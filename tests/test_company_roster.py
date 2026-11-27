"""Carteira por planilha (D-304, E2): leitura, prévia linha a linha, gravação e telas."""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from openpyxl import Workbook

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub import company_roster
from apps.hub.company_roster import (
    CREATE,
    PROBLEM,
    SAME,
    UPDATE,
    analyse_roster,
    apply_roster,
    create_roster_batch,
    error_report_csv,
    template_csv,
)
from apps.hub.imports import ImportValidationError
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    DataSource,
    ImportBatch,
    NfseDocument,
    NfseProcuracaoRequest,
    NfseSync,
    OfficeProfile,
)
from apps.hub.procuracao_onboarding import procuracao_setup_steps
from apps.organizations.models import Membership, Organization
from test_nfse_procuracao import ALNUM_CLIENT_CNPJ, cnpj_from
from test_nfse_procuracao_views import World, login

NEW_A = cnpj_from("334445550001")
NEW_B = cnpj_from("556667770001")
NEW_C = cnpj_from("778889990001")
CSV_HEADER = "nome;cnpj;email;codigo\r\n"


def csv_file(
    text: str, *, name: str = "carteira.csv", encoding: str = "utf-8"
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, text.encode(encoding), content_type="text/csv")


def rows(*items: dict[str, str]) -> list[dict[str, str]]:
    return list(items)


def office() -> Organization:
    organization = Organization.objects.create(name="Escritório Carteira", slug="carteira")
    OfficeProfile.objects.create(
        organization=organization,
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    )
    return organization


def by_number(preview: Any) -> dict[int, Any]:
    return {line.number: line for line in preview.lines}


# ---------------------------------------------------------------- prévia (sem gravar)


@pytest.mark.django_db
def test_a_valid_row_is_a_new_company_with_a_clean_cnpj_and_email() -> None:
    organization = office()

    preview = analyse_roster(
        organization=organization,
        rows=rows(
            {
                "nome": "  Padaria   Central ",
                "cnpj": "33.444.555/0001-" + NEW_A[-2:],
                "email": " Dono@Padaria.Example ",
                "codigo": "101",
            }
        ),
    )

    [line] = preview.lines
    assert (line.action, line.number) == (CREATE, 2)
    assert line.name == "Padaria Central"
    assert line.cnpj == NEW_A
    assert line.email == "dono@padaria.example"
    assert line.code == "101"
    assert (preview.create, preview.importable, preview.problems) == (1, 1, 0)
    assert ClientCompany.objects.count() == 0


@pytest.mark.django_db
def test_an_alphanumeric_cnpj_is_accepted() -> None:
    preview = analyse_roster(
        organization=office(), rows=rows({"nome": "Nova Era", "cnpj": ALNUM_CLIENT_CNPJ})
    )

    assert preview.lines[0].action == CREATE and preview.lines[0].cnpj == ALNUM_CLIENT_CNPJ


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ({"nome": "", "cnpj": NEW_A}, "Informe o nome"),
        ({"nome": "Sem CNPJ", "cnpj": ""}, "Informe o CNPJ"),
        (
            {"nome": "Dígito errado", "cnpj": NEW_A[:-1] + ("0" if NEW_A[-1] != "0" else "1")},
            "Dígitos do CNPJ não conferem",
        ),
        ({"nome": "Formato errado", "cnpj": "123"}, "CNPJ inválido"),
        ({"nome": "x" * 181, "cnpj": NEW_A}, "Nome acima de 180 caracteres"),
    ],
)
def test_a_row_without_name_or_a_valid_cnpj_is_a_problem(row: dict[str, str], reason: str) -> None:
    preview = analyse_roster(organization=office(), rows=rows(row))

    [line] = preview.lines
    assert line.action == PROBLEM
    assert reason in line.problems
    assert preview.importable == 0


@pytest.mark.django_db
def test_a_repeated_cnpj_or_code_inside_the_file_points_at_the_first_line() -> None:
    preview = analyse_roster(
        organization=office(),
        rows=rows(
            {"nome": "Primeira", "cnpj": NEW_A, "codigo": "7"},
            {"nome": "Repetida", "cnpj": NEW_A},
            {"nome": "Outro código", "cnpj": NEW_B, "codigo": "7"},
        ),
    )

    lines = by_number(preview)
    assert lines[2].action == CREATE
    assert lines[3].problems == ("CNPJ repetido na linha 2",)
    assert lines[4].problems == ("Código repetido na linha 2",)


@pytest.mark.django_db
def test_an_invalid_email_is_dropped_but_the_company_still_comes_in() -> None:
    preview = analyse_roster(
        organization=office(),
        rows=rows({"nome": "Padaria", "cnpj": NEW_A, "email": "isto-nao-e-email"}),
    )

    [line] = preview.lines
    assert line.action == CREATE and line.email == ""
    assert "E-mail inválido, ignorado" in line.notes
    assert "Sem e-mail" in line.notes
    assert preview.without_email == 1


@pytest.mark.django_db
def test_an_existing_company_is_matched_by_cnpj_whatever_the_mask() -> None:
    organization = office()
    ClientCompany.objects.create(
        organization=organization,
        name="Nome do Domínio",
        cnpj_masked=f"{NEW_A[:2]}.{NEW_A[2:5]}.{NEW_A[5:8]}/{NEW_A[8:12]}-{NEW_A[12:]}",
        contact_email="velho@example.test",
    )

    preview = analyse_roster(
        organization=organization,
        rows=rows(
            {"nome": "Outro nome", "cnpj": NEW_A, "email": "novo@example.test"},
            {"nome": "Igual", "cnpj": NEW_A.lower(), "email": "velho@example.test"},
        ),
    )

    first, second = preview.lines
    assert (first.action, first.email) == (UPDATE, "novo@example.test")
    assert first.name == "Nome do Domínio"  # identidade vinda do Domínio nunca é sobrescrita
    assert second.action == PROBLEM  # mesmo CNPJ duas vezes na planilha
    assert preview.update == 1


@pytest.mark.django_db
def test_an_existing_company_without_email_in_the_file_is_left_alone() -> None:
    organization = office()
    ClientCompany.objects.create(
        organization=organization,
        name="Já tem",
        cnpj_masked=NEW_A,
        contact_email="tem@example.test",
    )
    ClientCompany.objects.create(organization=organization, name="Sem", cnpj_masked=NEW_B)
    ClientCompany.objects.create(
        organization=organization, name="Parada", cnpj_masked=NEW_C, active=False
    )

    preview = analyse_roster(
        organization=organization,
        rows=rows(
            {"nome": "x", "cnpj": NEW_A},
            {"nome": "x", "cnpj": NEW_B},
            {"nome": "x", "cnpj": NEW_C, "email": "volta@example.test"},
        ),
    )

    a, b, c = preview.lines
    assert (a.action, a.notes) == (SAME, ())
    assert (b.action, b.notes) == (SAME, ("Sem e-mail",))
    assert c.action == SAME and "Empresa inativa" in c.notes  # inativa não muda


@pytest.mark.django_db
def test_companies_of_another_office_are_invisible_to_the_roster() -> None:
    organization = office()
    stranger = Organization.objects.create(name="Outro", slug="outro-carteira")
    ClientCompany.objects.create(organization=stranger, name="De outro", cnpj_masked=NEW_A)

    preview = analyse_roster(organization=organization, rows=rows({"nome": "Meu", "cnpj": NEW_A}))

    assert preview.lines[0].action == CREATE


@pytest.mark.django_db
def test_a_code_already_used_by_another_company_of_the_source_is_a_problem() -> None:
    organization = office()
    source = company_roster.ensure_roster_source(organization)
    ClientCompany.objects.create(
        organization=organization,
        data_source=source,
        external_key="9",
        name="Dona do 9",
        cnpj_masked=NEW_A,
    )

    preview = analyse_roster(
        organization=organization,
        data_source=source,
        rows=rows({"nome": "Quer o 9", "cnpj": NEW_B, "codigo": "9"}),
    )

    assert preview.lines[0].problems == ("Código já usado por outra empresa",)


@pytest.mark.django_db
def test_the_plan_limit_turns_the_overflow_into_problems() -> None:
    preview = analyse_roster(
        organization=office(),
        max_new=1,
        rows=rows(
            {"nome": "Cabe", "cnpj": NEW_A},
            {"nome": "Não cabe", "cnpj": NEW_B},
        ),
    )

    assert [line.action for line in preview.lines] == [CREATE, PROBLEM]
    assert preview.lines[1].problems == ("Limite de empresas do plano",)


# ---------------------------------------------------------------- leitura do arquivo


@pytest.mark.django_db
def test_a_semicolon_csv_with_accents_becomes_a_batch() -> None:
    organization = office()
    actor = World().owner
    upload = csv_file(CSV_HEADER + f"Padaria Pão Quente;{NEW_A};dono@pao.example;1\r\n")

    batch, created = create_roster_batch(organization=organization, upload=upload, actor=actor)

    assert created and batch.row_count == 1
    assert company_roster.batch_rows(batch)[0]["nome"] == "Padaria Pão Quente"
    assert company_roster.is_roster_batch(batch)


@pytest.mark.django_db
def test_an_excel_csv_in_windows_1252_is_read_not_rejected() -> None:
    organization = office()
    actor = World().owner
    upload = csv_file(
        CSV_HEADER + f"Açougue São José;{NEW_A};;\r\n", name="excel.csv", encoding="cp1252"
    )

    batch, _ = create_roster_batch(organization=organization, upload=upload, actor=actor)

    assert company_roster.batch_rows(batch)[0]["nome"] == "Açougue São José"


@pytest.mark.django_db
def test_portuguese_headers_with_accents_are_understood() -> None:
    organization = office()
    actor = World().owner
    upload = csv_file(f"Razão Social;CNPJ;E-mail;Código\r\nPadaria;{NEW_A};a@b.example;5\r\n")

    batch, _ = create_roster_batch(organization=organization, upload=upload, actor=actor)
    [line] = analyse_roster(organization=organization, rows=company_roster.batch_rows(batch)).lines

    assert (line.name, line.email, line.code, line.action) == (
        "Padaria",
        "a@b.example",
        "5",
        CREATE,
    )


@pytest.mark.django_db
def test_an_xlsx_sheet_is_read_too() -> None:
    organization = office()
    actor = World().owner
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["nome", "cnpj", "email"])
    sheet.append(["Oficina Norte", NEW_A, "oficina@example.test"])
    buffer = io.BytesIO()
    book.save(buffer)
    upload = SimpleUploadedFile("carteira.xlsx", buffer.getvalue())

    batch, _ = create_roster_batch(organization=organization, upload=upload, actor=actor)

    assert company_roster.batch_rows(batch)[0]["email"] == "oficina@example.test"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("carteira.pdf", b"%PDF", "Envie um arquivo .csv ou .xlsx."),
        ("vazio.csv", b"", "O arquivo está vazio."),
        ("so-cabecalho.csv", b"nome;cnpj\r\n", "O arquivo não possui linhas para importar."),
        ("sem-cnpj.csv", b"nome;email\r\nA;a@b.example\r\n", "Faltam as colunas nome e cnpj"),
    ],
)
def test_unusable_files_are_refused_with_a_reason(name: str, content: bytes, message: str) -> None:
    organization = office()
    actor = World().owner

    with pytest.raises(ImportValidationError) as raised:
        create_roster_batch(
            organization=organization, upload=SimpleUploadedFile(name, content), actor=actor
        )

    assert message in str(raised.value)


@pytest.mark.django_db
def test_the_payload_is_encrypted_at_rest_and_the_same_file_returns_the_same_batch() -> None:
    organization = office()
    actor = World().owner
    text = CSV_HEADER + f"Padaria Sigilosa;{NEW_A};segredo@example.test;1\r\n"

    first, created = create_roster_batch(
        organization=organization, upload=csv_file(text), actor=actor
    )
    again, created_again = create_roster_batch(
        organization=organization, upload=csv_file(text), actor=actor
    )

    assert created and not created_again and first.pk == again.pk
    assert first.content_hash == hashlib.sha256(text.encode()).hexdigest()
    with connection.cursor() as cursor:
        cursor.execute(
            "select encrypted_payload from hub_importbatch where id = %s",
            [first.pk.hex if connection.vendor == "sqlite" else str(first.pk)],
        )
        raw = cursor.fetchone()[0]
    assert "Padaria Sigilosa" not in raw and "segredo@example.test" not in raw


def test_the_template_is_only_a_header_so_nothing_is_imported_by_accident() -> None:
    content = template_csv()

    assert content.startswith(b"\xef\xbb\xbf")
    assert content.decode("utf-8-sig") == "nome;cnpj;email;codigo\r\n"


def test_the_error_report_neutralises_spreadsheet_formulas() -> None:
    line = company_roster.RosterLine(
        number=3,
        name="=1+1",
        cnpj="123",
        email="+a@b.example",
        code="",
        action=PROBLEM,
        problems=("CNPJ inválido",),
    )

    text = error_report_csv([line]).decode("utf-8-sig")

    header, body = text.strip().split("\r\n")
    assert header == "linha;nome;cnpj;email;codigo;situacao;motivo"
    assert body.startswith("3;'=1+1;123;")
    assert ";'+a@b.example;" in body and body.endswith("Com problema;CNPJ inválido")


# ---------------------------------------------------------------- gravação


def batch_for(organization: Organization, actor: Any, text: str) -> ImportBatch:
    batch, _ = create_roster_batch(organization=organization, upload=csv_file(text), actor=actor)
    return batch


@pytest.mark.django_db
def test_confirming_creates_the_companies_and_keeps_only_the_report() -> None:
    organization = office()
    actor = World().owner
    batch = batch_for(
        organization,
        actor,
        CSV_HEADER
        + f"Padaria Central;{NEW_A};dono@padaria.example;101\r\n"
        + f"Oficina Norte;{NEW_B};;\r\n"
        + "Sem CNPJ;;;\r\n",
    )

    result = apply_roster(batch=batch, actor=actor)

    assert result is not None
    assert (result.created, result.updated, result.problems) == (2, 0, 1)
    padaria = ClientCompany.objects.get(organization=organization, name="Padaria Central")
    assert padaria.cnpj_masked == NEW_A and padaria.contact_email == "dono@padaria.example"
    assert padaria.external_key == "101" and padaria.active
    assert padaria.commercial_root_cnpj == NEW_A[:8]
    source = DataSource.objects.get(organization=organization, kind=DataSource.Kind.OTHER_MANUAL)
    assert padaria.data_source_id == source.pk
    assert source.status == DataSource.Status.READY and "companies" in source.capabilities
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.COMPLETED
    assert (batch.created_count, batch.updated_count) == (2, 0)
    assert batch.errors == [{"row": 4, "message": "Informe o CNPJ"}]
    stored = company_roster.batch_rows(batch)
    assert {item["nome"] for item in stored} == {
        "Oficina Norte",
        "Sem CNPJ",
    }  # só quem tem ocorrência


@pytest.mark.django_db
def test_confirming_twice_changes_nothing_the_second_time() -> None:
    organization = office()
    actor = World().owner
    batch = batch_for(organization, actor, CSV_HEADER + f"Padaria;{NEW_A};;\r\n")

    assert apply_roster(batch=batch, actor=actor) is not None
    assert apply_roster(batch=batch, actor=actor) is None
    assert ClientCompany.objects.filter(organization=organization).count() == 1


@pytest.mark.django_db
def test_an_existing_company_only_gets_its_email_updated() -> None:
    organization = office()
    actor = World().owner
    other_source = DataSource.objects.create(
        organization=organization, kind=DataSource.Kind.DOMINIO_WEB_BACKUP, label="Domínio"
    )
    existing = ClientCompany.objects.create(
        organization=organization,
        name="Nome do Domínio",
        cnpj_masked=NEW_A,
        data_source=other_source,
        dominio_code="55",
        contact_email="",
    )
    batch = batch_for(
        organization, actor, CSV_HEADER + f"Nome da planilha;{NEW_A};novo@example.test;9\r\n"
    )

    result = apply_roster(batch=batch, actor=actor)

    assert result is not None and (result.created, result.updated) == (0, 1)
    existing.refresh_from_db()
    assert existing.contact_email == "novo@example.test"
    assert (existing.name, existing.dominio_code, existing.data_source_id) == (
        "Nome do Domínio",
        "55",
        other_source.pk,
    )
    assert ClientCompany.objects.filter(organization=organization).count() == 1


@pytest.mark.django_db
def test_the_plan_limit_is_enforced_at_confirmation_not_only_in_the_preview() -> None:
    organization = office()
    actor = World().owner
    batch = batch_for(
        organization, actor, CSV_HEADER + f"Um;{NEW_A};;\r\nDois;{NEW_B};;\r\nTrês;{NEW_C};;\r\n"
    )

    result = apply_roster(batch=batch, actor=actor, max_new=2)

    assert result is not None and (result.created, result.problems) == (2, 1)
    assert ClientCompany.objects.filter(organization=organization).count() == 2


@pytest.mark.django_db
def test_a_member_with_company_grants_gets_the_new_companies_in_their_portfolio() -> None:
    world = World()
    restricted = Membership.objects.get(user=world.owner, organization=world.office)
    CompanyAccessGrant.objects.create(
        organization=world.office,
        membership=restricted,
        company=world.padaria,
        modules=["nfse"],
        capabilities=["*"],
    )
    batch = batch_for(world.office, world.owner, CSV_HEADER + f"Nova;{NEW_A};;\r\n")

    apply_roster(batch=batch, actor=world.owner, membership=restricted)

    created = ClientCompany.objects.get(organization=world.office, name="Nova")
    assert CompanyAccessGrant.objects.filter(membership=restricted, company=created).exists()


@pytest.mark.django_db
def test_the_audit_trail_records_counts_never_names_or_addresses() -> None:
    organization = office()
    actor = World().owner
    batch = batch_for(
        organization, actor, CSV_HEADER + f"Padaria Sigilosa;{NEW_A};x@example.test;\r\n"
    )

    apply_roster(batch=batch, actor=actor)

    event = AuditEvent.objects.get(action="hub.roster.imported")
    assert event.metadata["created"] == 1
    assert "sigilosa" not in str(event.metadata).lower() and "example.test" not in str(
        event.metadata
    )


# ---------------------------------------------------------------- telas


def upload_file(client: Any, text: str, name: str = "carteira.csv") -> Any:
    return client.post(reverse("hub:roster"), {"planilha": csv_file(text, name=name)})


@pytest.mark.django_db
def test_the_upload_page_lists_nothing_at_first_and_offers_the_template() -> None:
    world = World()

    response = login(world.owner, world.office).get(reverse("hub:roster"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Nenhuma planilha enviada" in html and reverse("hub:roster-template") in html
    assert response.context["page_title"] == "Carteira"


@pytest.mark.django_db
def test_an_upload_lands_on_the_preview_and_confirming_imports_and_seeds_the_collection() -> None:
    world = World()
    client = login(world.owner, world.office)

    sent = upload_file(
        client, CSV_HEADER + f"Nova Empresa;{NEW_A};nova@example.test;\r\n" + "Sem CNPJ;;;\r\n"
    )
    assert sent.status_code == 302
    preview = client.get(sent["Location"])
    html = preview.content.decode()
    assert "Prévia" in html and "Importar 1" in html and "1 com problema" in html
    assert "Informe o CNPJ" in html

    done = client.post(sent["Location"], {"action": "confirm"}, follow=True)

    assert any("1 empresa importada" in str(m) for m in done.context["messages"])
    assert "Resultado" in done.content.decode() and "Pedir procurações" in done.content.decode()
    company = ClientCompany.objects.get(organization=world.office, name="Nova Empresa")
    assert NfseSync.objects.filter(
        company=company, credential_mode=NfseSync.CredentialMode.PROCURACAO
    ).exists()


@pytest.mark.django_db
def test_the_error_report_downloads_for_a_preview_and_after_the_import() -> None:
    world = World()
    client = login(world.owner, world.office)
    sent = upload_file(client, CSV_HEADER + f"Boa;{NEW_A};;\r\nRuim;123;;\r\n")
    errors_url = sent["Location"] + "erros.csv"

    before = client.get(errors_url)
    client.post(sent["Location"], {"action": "confirm"})
    after = client.get(errors_url)

    for response in (before, after):
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        assert response["Cache-Control"] == "no-store"
        text = response.content.decode("utf-8-sig")
        assert "CNPJ inválido" in text and "Ruim" in text
    assert "attachment" in after["Content-Disposition"]


@pytest.mark.django_db
def test_discarding_a_preview_deletes_the_batch() -> None:
    world = World()
    client = login(world.owner, world.office)
    sent = upload_file(client, CSV_HEADER + f"Boa;{NEW_A};;\r\n")

    response = client.post(sent["Location"], {"action": "discard"})

    assert response["Location"] == reverse("hub:roster")
    assert not ImportBatch.objects.filter(organization=world.office).exists()
    assert AuditEvent.objects.filter(action="hub.roster.discarded").exists()


@pytest.mark.django_db
def test_re_sending_a_finished_file_says_it_was_already_imported() -> None:
    world = World()
    client = login(world.owner, world.office)
    text = CSV_HEADER + f"Boa;{NEW_A};;\r\n"
    first = upload_file(client, text)
    client.post(first["Location"], {"action": "confirm"})

    second = client.post(reverse("hub:roster"), {"planilha": csv_file(text)}, follow=True)

    assert second.redirect_chain[-1][0] == first["Location"]
    assert any("já foi importada" in str(m) for m in second.context["messages"])


@pytest.mark.django_db
def test_a_bad_file_goes_back_with_the_reason() -> None:
    world = World()
    client = login(world.owner, world.office)

    response = client.post(
        reverse("hub:roster"), {"planilha": SimpleUploadedFile("x.pdf", b"%PDF")}, follow=True
    )

    assert any("Envie um arquivo .csv ou .xlsx" in str(m) for m in response.context["messages"])
    assert not ImportBatch.objects.exists()


@pytest.mark.django_db
def test_a_legacy_office_never_reaches_the_roster() -> None:
    world = World(mode=OfficeProfile.NfseCollectionMode.CERTIFICATE)
    client = login(world.owner, world.office)

    for name in ("hub:roster", "hub:roster-template"):
        assert client.get(reverse(name))["Location"] == reverse("hub:companies")
    assert client.post(reverse("hub:roster"), {"planilha": csv_file(CSV_HEADER)}).status_code == 302
    assert not ImportBatch.objects.exists()


@pytest.mark.django_db
def test_only_who_manages_the_portfolio_imports() -> None:
    world = World()
    client = login(world.operator, world.office)

    page = client.get(reverse("hub:roster"))
    sent = client.post(
        reverse("hub:roster"), {"planilha": csv_file(CSV_HEADER + f"A;{NEW_A};;\r\n")}
    )

    assert page.status_code == 200 and "Seu perfil não altera a carteira." in page.content.decode()
    assert sent.status_code == 403 and not ImportBatch.objects.exists()


@pytest.mark.django_db
def test_another_offices_batch_is_a_404() -> None:
    world = World()
    other = Organization.objects.create(name="Vizinho", slug="vizinho")
    OfficeProfile.objects.create(
        organization=other, nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO
    )
    actor = world.owner
    foreign = batch_for(other, actor, CSV_HEADER + f"Alheia;{NEW_A};;\r\n")
    client = login(world.owner, world.office)

    assert client.get(reverse("hub:roster-batch", args=[foreign.pk])).status_code == 404
    assert client.get(reverse("hub:roster-errors", args=[foreign.pk])).status_code == 404
    confirm = client.post(reverse("hub:roster-batch", args=[foreign.pk]), {"action": "confirm"})
    assert confirm.status_code == 404


@pytest.mark.django_db
def test_a_legacy_import_batch_is_not_served_as_a_roster() -> None:
    world = World()
    source = DataSource.objects.create(
        organization=world.office, kind=DataSource.Kind.OTHER_MANUAL, label="Manual"
    )
    legacy = ImportBatch.objects.create(
        organization=world.office,
        data_source=source,
        kind=ImportBatch.Kind.COMPANIES,
        original_filename="antigo.csv",
        content_hash="a" * 64,
        mapping={"company_id": ""},
    )

    response = login(world.owner, world.office).get(reverse("hub:roster-batch", args=[legacy.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_the_procuracoes_page_offers_the_import_as_the_way_out_of_an_empty_portfolio() -> None:
    world = World()
    ClientCompany.objects.filter(organization=world.office).delete()

    html = login(world.owner, world.office).get(reverse("hub:procuracoes")).content.decode()

    assert reverse("hub:roster") in html and "Importar carteira" in html


# ---------------------------------------------------------------- passos do assistente


def steps(world: World) -> dict[str, dict[str, Any]]:
    profile = OfficeProfile.objects.get(organization=world.office)
    return {
        step["label"]: step
        for step in procuracao_setup_steps(office=world.office, profile=profile, mfa_complete=False)
    }


@pytest.mark.django_db
def test_every_step_is_pending_for_an_office_that_did_nothing() -> None:
    world = World()
    ClientCompany.objects.filter(organization=world.office).delete()
    Membership.objects.filter(organization=world.office).exclude(user=world.owner).delete()

    state = steps(world)

    assert [item["done"] for item in state.values()] == [False] * len(state)
    assert list(state)[:5] == [
        "Confirmar escritório",
        "Enviar e-CNPJ",
        "Importar carteira",
        "Pedir procurações",
        "Receber a primeira NFS-e",
    ]


@pytest.mark.django_db
def test_each_step_turns_done_only_with_its_own_fact() -> None:
    world = World()
    ClientCompany.objects.filter(organization=world.office).delete()
    world.operator.delete()
    world.auditor.delete()
    OfficeProfile.objects.filter(organization=world.office).update(cnpj_hash="x" * 64)
    assert steps(world)["Confirmar escritório"]["done"] is True
    assert steps(world)["Importar carteira"]["done"] is False

    company = world.company("Padaria", NEW_A, "p@example.test")
    after_import = steps(world)
    assert after_import["Importar carteira"]["done"] is True
    assert after_import["Importar carteira"]["note"] == "1 empresa"
    assert after_import["Pedir procurações"]["done"] is False
    assert after_import["Enviar e-CNPJ"]["done"] is False

    NfseProcuracaoRequest.objects.create(
        organization=world.office,
        company=company,
        status=NfseProcuracaoRequest.Status.SENT,
        recipient_masked="p***@example.test",
    )
    assert steps(world)["Pedir procurações"]["done"] is True
    assert steps(world)["Receber a primeira NFS-e"]["done"] is False

    xml = "<NFSe/>"
    NfseDocument.objects.create(
        organization=world.office,
        company=company,
        source_nsu="1",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        issued_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    assert steps(world)["Receber a primeira NFS-e"]["done"] is True


@pytest.mark.django_db
def test_the_certificate_step_needs_a_valid_ecnpj_not_a_revoked_one() -> None:
    world = World()
    client = login(world.owner, world.office)
    assert steps(world)["Enviar e-CNPJ"]["done"] is False

    world.upload(client)
    assert steps(world)["Enviar e-CNPJ"]["done"] is True

    client.post(reverse("hub:settings"), {"action": "revoke-certificate"})
    assert steps(world)["Enviar e-CNPJ"]["done"] is False


@pytest.mark.django_db
def test_waiting_procuracoes_are_counted_in_the_note() -> None:
    world = World()
    client = login(world.owner, world.office)
    world.upload(client)  # semeia as linhas de coleta
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING
    )
    NfseSync.objects.filter(company=world.mercado).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK
    )

    state = steps(world)

    assert state["Pedir procurações"]["note"] == "1 aguardando procuração"
    assert state["Pedir procurações"]["done"] is True  # há procuração em dia
    assert state["Receber a primeira NFS-e"]["note"] == "1 empresa em dia"


@pytest.mark.django_db
def test_the_setup_page_shows_the_new_steps_for_a_procuracao_office() -> None:
    world = World()

    html = login(world.owner, world.office).get(reverse("hub:setup")).content.decode()

    assert "Enviar e-CNPJ" in html and "Receber a primeira NFS-e" in html
    assert "Escolher fonte de dados" not in html


@pytest.mark.django_db
def test_the_setup_page_of_a_legacy_office_keeps_the_old_steps() -> None:
    world = World(mode=OfficeProfile.NfseCollectionMode.CERTIFICATE)

    html = login(world.owner, world.office).get(reverse("hub:setup")).content.decode()

    assert "Escolher fonte de dados" in html and "Receber a primeira NFS-e" not in html


@pytest.mark.django_db
def test_an_empty_companies_page_points_a_procuracao_office_to_the_import() -> None:
    world = World()
    ClientCompany.objects.filter(organization=world.office).delete()

    html = login(world.owner, world.office).get(reverse("hub:companies")).content.decode()

    assert reverse("hub:roster") in html


@pytest.mark.django_db
def test_an_empty_companies_page_of_a_legacy_office_is_unchanged() -> None:
    world = World(mode=OfficeProfile.NfseCollectionMode.CERTIFICATE)
    ClientCompany.objects.filter(organization=world.office).delete()

    html = login(world.owner, world.office).get(reverse("hub:companies")).content.decode()

    assert reverse("hub:roster") not in html and "Adicionar empresa" in html


# ---------------------------------------------------- carteira parcial (revisão de segurança)


def partial_portfolio(world: World) -> Membership:
    """Um gestor que só alcança a padaria (acesso por empresa)."""

    manager = world.member(Membership.Role.MANAGER, "gestor@example.test")
    membership = Membership.objects.get(user=manager, organization=world.office)
    CompanyAccessGrant.objects.create(
        organization=world.office,
        membership=membership,
        company=world.padaria,
        modules=["nfse"],
        capabilities=["*"],
    )
    return membership


@pytest.mark.django_db
def test_owner_and_admin_reach_the_whole_office_even_with_leftover_grants() -> None:
    world = World()
    owner_membership = Membership.objects.get(user=world.owner, organization=world.office)
    CompanyAccessGrant.objects.create(
        organization=world.office,
        membership=owner_membership,
        company=world.padaria,
        modules=["nfse"],
        capabilities=["*"],
    )
    client = login(world.owner, world.office)
    text = CSV_HEADER + f"x;{world.oficina.cnpj_masked};novo@oficina.example;\r\n"
    sent = client.post(reverse("hub:roster"), {"planilha": csv_file(text)})

    client.post(sent["Location"], {"action": "confirm"})

    world.oficina.refresh_from_db()
    assert (
        world.oficina.contact_email == "novo@oficina.example"
    )  # como o produto já define o escopo


@pytest.mark.django_db
def test_the_visible_companies_follow_the_product_scope_rule() -> None:
    from apps.hub.controlplane import company_queryset_for_membership
    from apps.hub.views_roster import visible_company_ids

    world = World()
    manager = partial_portfolio(world)
    owner_membership = Membership.objects.get(user=world.owner, organization=world.office)

    def context_for(membership: Membership) -> dict[str, object]:
        return {
            "membership": membership,
            "support_session": None,
            "companies": company_queryset_for_membership(membership),
        }

    assert visible_company_ids(context_for(owner_membership)) is None
    assert visible_company_ids(context_for(manager)) == frozenset({str(world.padaria.pk)})


@pytest.mark.django_db
def test_a_member_with_a_partial_portfolio_cannot_import_at_all() -> None:
    """O portão que torna o cinto de segurança inalcançável hoje: só quem vê tudo importa."""

    world = World()
    partial_portfolio(world)
    client = login(User.objects.get(email="gestor@example.test"), world.office)

    page = client.get(reverse("hub:roster"))
    sent = client.post(
        reverse("hub:roster"), {"planilha": csv_file(CSV_HEADER + f"A;{NEW_A};;\r\n")}
    )

    assert "Seu perfil não altera a carteira." in page.content.decode()
    assert (
        sent.status_code == 403
        and not ImportBatch.objects.filter(organization=world.office).exists()
    )


@pytest.mark.django_db
def test_the_analysis_with_an_empty_scope_flags_every_known_cnpj_and_still_creates_new_ones() -> (
    None
):
    world = World()

    preview = analyse_roster(
        organization=world.office,
        visible_ids=frozenset(),
        rows=rows(
            {"nome": "digitado", "cnpj": world.padaria.cnpj_masked},
            {"nome": "Nova", "cnpj": NEW_A},
        ),
    )

    known, new = preview.lines
    assert known.action == PROBLEM and known.problems == ("Empresa fora da sua carteira",)
    assert known.name == "digitado" and known.company_id == ""  # nada da empresa existente
    assert new.action == CREATE


@pytest.mark.django_db
def test_the_report_of_an_outside_company_never_carries_its_name_or_status() -> None:
    world = World()
    world.oficina.active = False
    world.oficina.save(update_fields=["active"])
    preview = analyse_roster(
        organization=world.office,
        visible_ids=frozenset({str(world.padaria.pk)}),
        rows=rows({"nome": "digitado", "cnpj": world.oficina.cnpj_masked}),
    )

    report = error_report_csv(preview.reportable()).decode("utf-8-sig")

    assert "Empresa fora da sua carteira" in report
    assert "Oficina Norte" not in report and "inativa" not in report.lower()


@pytest.mark.django_db
def test_the_write_path_never_updates_a_company_outside_the_scope() -> None:
    world = World()
    batch = batch_for(
        world.office,
        world.owner,
        CSV_HEADER + f"x;{world.padaria.cnpj_masked};outro@padaria.example;\r\n",
    )

    result = apply_roster(batch=batch, actor=world.owner, visible_ids=frozenset())

    assert result is not None and (result.updated, result.problems) == (0, 1)
    world.padaria.refresh_from_db()
    assert world.padaria.contact_email == "dono@padaria.example"
