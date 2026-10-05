from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    AccumulatorCatalogEntry,
    AccumulatorObservation,
    AccumulatorRule,
    ClientCompany,
    DataSource,
    ImportBatch,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)
from apps.hub.services import (
    _xml_with_dominio_accumulator,
    create_document_and_artifact,
    create_nfse_export,
    normalize_service_code,
    record_human_observation,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

TAKEN = AccumulatorObservation.Direction.TAKEN
PROVIDED = AccumulatorObservation.Direction.PROVIDED


def _company(slug: str) -> ClientCompany:
    office = Organization.objects.create(name=slug, slug=slug)
    return ClientCompany.objects.create(organization=office, name=f"Cliente {slug}")


def _catalog(company: ClientCompany, codes: dict[str, bool], *, hours_ago: int = 1) -> None:
    source, _ = DataSource.objects.get_or_create(
        organization=company.organization,
        kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
        defaults={"label": "Backup Domínio Web"},
    )
    snapshot_at = timezone.now() - timedelta(hours=hours_ago)
    batch = ImportBatch.objects.create(
        organization=company.organization,
        data_source=source,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.COMPLETED,
        original_filename="backup.zip",
        content_hash=hashlib.sha256(f"{company.pk}{hours_ago}".encode()).hexdigest(),
        source_snapshot_at=snapshot_at,
        completed_at=snapshot_at,
    )
    for code, active in codes.items():
        AccumulatorCatalogEntry.objects.create(
            organization=company.organization,
            company=company,
            data_source=source,
            source_batch=batch,
            accumulator_code=code,
            active=active,
            source_snapshot_at=snapshot_at,
        )


def _observe(company: ClientCompany, code: str, *, direction: str = "", **match: str) -> None:
    AccumulatorObservation.objects.create(
        organization=company.organization,
        company=company,
        accumulator_code=code,
        direction=direction,
        frequency=20,
        last_used_at=timezone.now(),
        **match,
    )


def _capture(company: ClientCompany, data: dict[str, str], name: str = "nota"):
    return create_document_and_artifact(
        company=company, original_xml=f"<nfse id='{name}'/>", normalized_data=data
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("17.01", "1701"),
        ("1.05", "0105"),
        ("170101", "1701"),
        ("010501", "0105"),
        ("1701", "1701"),
        (" 17.01.01 ", "1701"),
        ("", ""),
        ("ABC-1", "ABC-1"),
    ],
)
def test_service_code_reduces_ctribnac_and_lc116_item_to_the_same_key(
    raw: str, expected: str
) -> None:
    assert normalize_service_code(raw) == expected


def test_ctribnac_note_matches_dominio_lc116_item() -> None:
    company = _company("lc116")
    _observe(company, "301", direction=TAKEN, service_code="17.01")

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "direction": "taken"}
    )

    assert review is None
    assert artifact is not None and artifact.accumulator_code == "301"


def test_taken_note_never_receives_a_provided_service_accumulator() -> None:
    company = _company("direcao")
    _observe(company, "SAIDA", direction=PROVIDED, service_code="17.01")
    _observe(company, "ENTRADA", direction=TAKEN, service_code="17.01")

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "direction": "taken"}
    )

    assert review is None
    assert artifact is not None and artifact.accumulator_code == "ENTRADA"


def test_taken_note_with_only_provided_history_goes_to_review() -> None:
    company = _company("so-saida")
    _observe(company, "SAIDA", direction=PROVIDED, service_code="17.01")

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "direction": "taken"}
    )

    assert artifact is None
    assert review is not None and review.suggested_accumulator == ""


def test_unknown_direction_is_not_decided_once_history_has_direction() -> None:
    company = _company("sem-direcao")
    _observe(company, "ENTRADA", direction=TAKEN, service_code="17.01")

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "direction": "unknown"}
    )

    assert artifact is None
    assert review is not None


def test_inactive_or_missing_catalog_accumulator_is_never_chosen() -> None:
    company = _company("catalogo")
    _catalog(company, {"OLD": True}, hours_ago=48)
    # Latest snapshot: OLD was deactivated and GHOST never existed in Domínio.
    _catalog(company, {"OLD": False, "GOOD": True})
    _observe(company, "OLD", direction=TAKEN, counterparty_ref="forn")
    _observe(company, "GHOST", direction=TAKEN, counterparty_ref="forn")
    AccumulatorRule.objects.create(
        organization=company.organization,
        company=company,
        name="Regra desativada",
        match={"service_code": "170101"},
        accumulator_code="GHOST",
        active=False,
    )

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "counterparty_ref": "forn", "direction": "taken"}
    )
    assert artifact is None
    assert review is not None

    _observe(company, "GOOD", direction=TAKEN, counterparty_ref="forn")
    _document, artifact, review = _capture(
        company,
        {"service_code": "170101", "counterparty_ref": "forn", "direction": "taken"},
        name="segunda",
    )
    assert review is None
    assert artifact is not None and artifact.accumulator_code == "GOOD"


def _exportable(company: ClientCompany, code: str) -> NfseDocument:
    xml = "<NFSe><infNFSe><valores><vLiq>1.00</vLiq></valores></infNFSe></NFSe>"
    document = NfseDocument.objects.create(
        organization=company.organization,
        company=company,
        source_nsu=f"nsu-{code}",
        document_hash=hashlib.sha256(f"{xml}{code}".encode()).hexdigest(),
        original_xml=xml,
        normalized_data={"number": f"N-{code}"},
        issued_at=timezone.now(),
    )
    IntegrationArtifact.objects.create(
        organization=company.organization, document=document, accumulator_code=code
    )
    return document


def test_export_refuses_accumulator_outside_the_active_catalog() -> None:
    company = _company("export-catalogo")
    _catalog(company, {"GOOD": True, "OFF": False})
    actor = User.objects.create_user("export-catalogo@example.test", "safe-password-123")
    good = _exportable(company, "GOOD")
    off = _exportable(company, "OFF")

    with pytest.raises(ValueError, match="N-OFF"):
        create_nfse_export(organization=company.organization, documents=[good, off], actor=actor)
    assert (
        create_nfse_export(
            organization=company.organization, documents=[good], actor=actor
        ).document_count
        == 1
    )


def test_human_decision_learns_under_the_note_key_even_with_many_backup_rows() -> None:
    company = _company("humano")
    _observe(company, "77", direction=TAKEN, service_code="01.01")
    _observe(company, "77", direction=TAKEN, counterparty_ref="outro")
    document, _artifact, _review = _capture(
        company, {"service_code": "170101", "counterparty_ref": "forn", "direction": "taken"}
    )

    first = record_human_observation(
        document=document, accumulator_code="77", observed_at=timezone.now()
    )
    again = record_human_observation(
        document=document, accumulator_code="77", observed_at=timezone.now()
    )

    assert first.pk == again.pk
    first.refresh_from_db()
    assert (first.service_code, first.counterparty_ref, first.direction) == (
        "170101",
        "forn",
        TAKEN,
    )
    assert first.frequency == 2
    assert AccumulatorObservation.objects.filter(company=company).count() == 3


def test_export_xml_keeps_prefixes_signature_and_declaration() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<n:NFSe xmlns:n="http://www.sped.fazenda.gov.br/nfse" versao="1.00">'
        '<n:infNFSe Id="NFS1"><n:emit><n:enderNac><n:cMun>4314902</n:cMun>'
        "</n:enderNac></n:emit><n:valores><n:vLiq>10.00</n:vLiq></n:valores>"
        "<n:DPS><n:infDPS><n:valores><n:vServPrest><n:vServ>10.00</n:vServ>"
        "</n:vServPrest></n:valores></n:infDPS></n:DPS></n:infNFSe>"
        '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignatureValue>abc'
        "</SignatureValue></Signature></n:NFSe>"
    )

    rendered = _xml_with_dominio_accumulator(xml, "12&3")

    assert rendered == xml.replace(
        "<n:vLiq>10.00</n:vLiq></n:valores>",
        "<n:vLiq>10.00</n:vLiq><n:acum>12&amp;3</n:acum></n:valores>",
        1,
    )


def test_export_xml_replaces_existing_acum_and_opens_empty_values() -> None:
    replaced = _xml_with_dominio_accumulator(
        "<NFSe><infNFSe><valores><acum>OLD</acum><vLiq>1</vLiq></valores></infNFSe></NFSe>",
        "NEW",
    )
    assert replaced == (
        "<NFSe><infNFSe><valores><acum>NEW</acum><vLiq>1</vLiq></valores></infNFSe></NFSe>"
    )

    opened = _xml_with_dominio_accumulator("<NFSe><infNFSe><valores /></infNFSe></NFSe>", "9")
    assert opened == "<NFSe><infNFSe><valores><acum>9</acum></valores></infNFSe></NFSe>"

    created = _xml_with_dominio_accumulator("<NFSe><infNFSe><nNFSe>1</nNFSe></infNFSe></NFSe>", "9")
    assert created == (
        "<NFSe><infNFSe><nNFSe>1</nNFSe><valores><acum>9</acum></valores></infNFSe></NFSe>"
    )


def test_supplier_always_booked_in_one_accumulator_classifies_even_if_rare_and_old() -> None:
    company = _company("unanime")
    AccumulatorObservation.objects.create(
        organization=company.organization,
        company=company,
        accumulator_code="410",
        counterparty_ref="forn",
        direction=TAKEN,
        frequency=1,
        last_used_at=timezone.now() - timedelta(days=400),
    )

    _document, artifact, review = _capture(
        company, {"counterparty_ref": "forn", "direction": "taken"}
    )

    assert review is None
    assert artifact is not None and artifact.accumulator_code == "410"
    assert artifact.confidence == 80


def test_service_winner_against_supplier_history_goes_to_review() -> None:
    company = _company("conflito")
    _observe(company, "SERVICO", direction=TAKEN, service_code="17.01")
    AccumulatorObservation.objects.create(
        organization=company.organization,
        company=company,
        accumulator_code="FORNECEDOR",
        counterparty_ref="forn",
        direction=TAKEN,
        frequency=1,
        last_used_at=timezone.now() - timedelta(days=700),
    )

    _document, artifact, review = _capture(
        company, {"service_code": "170101", "counterparty_ref": "forn", "direction": "taken"}
    )

    assert artifact is None
    assert review is not None and review.suggested_accumulator == "SERVICO"


def test_accumulator_registered_by_hand_is_valid_for_export() -> None:
    company = _company("export-manual")
    _catalog(company, {"GOOD": True})
    AccumulatorRule.objects.create(
        organization=company.organization,
        company=company,
        name="Criado no Domínio depois do backup",
        accumulator_code="NOVO",
    )
    actor = User.objects.create_user("export-manual@example.test", "safe-password-123")

    export = create_nfse_export(
        organization=company.organization, documents=[_exportable(company, "NOVO")], actor=actor
    )

    assert export.document_count == 1


def test_human_decision_with_direction_keeps_legacy_backup_history_usable() -> None:
    company = _company("legado")
    _observe(company, "LEGADO", counterparty_ref="forn")
    first, _artifact, _review = _capture(
        company, {"service_code": "990101", "counterparty_ref": "outro", "direction": "taken"}
    )
    record_human_observation(document=first, accumulator_code="HUMANO", observed_at=timezone.now())

    _document, artifact, review = _capture(
        company, {"counterparty_ref": "forn", "direction": "taken"}, name="seguinte"
    )

    assert review is None
    assert artifact is not None and artifact.accumulator_code == "LEGADO"


def test_directional_backup_row_replaces_the_legacy_row_with_the_same_key() -> None:
    from apps.hub.backup_bridge import apply_backup_page
    from apps.intelligence.models import EdgeAgent

    company = _company("ponte")
    _catalog(company, {"501": True})
    _observe(company, "501", service_code="17.01")
    source = DataSource.objects.get(organization=company.organization)
    company.data_source = source
    company.external_key = "7"
    company.save(update_fields=["data_source", "external_key", "updated_at"])
    batch = ImportBatch.objects.filter(organization=company.organization).first()
    assert batch is not None

    result = apply_backup_page(
        batch=batch,
        capability="accumulator_observations",
        rows=[
            {
                "company_key": "7",
                "accumulator_code": "501",
                "service_code": "17.01",
                "direction": "taken",
                "frequency": 3,
                "last_used_at": "2026-09-23T20:00:00-03:00",
            },
            {
                "company_key": "7",
                "accumulator_code": "501",
                "service_code": "17.02",
                "direction": "sideways",
                "frequency": 3,
                "last_used_at": "2026-09-23T20:00:00-03:00",
            },
        ],
        agent=EdgeAgent(),
    )

    assert result == {"created": 1, "updated": 0, "ignored": 1}
    assert list(
        AccumulatorObservation.objects.filter(company=company).values_list(
            "service_code", "direction"
        )
    ) == [("17.01", TAKEN)]


def _legacy_note(company: ClientCompany, *, provider: str, recipient: str) -> NfseDocument:
    xml = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse"><infNFSe>'
        f"<emit><CNPJ>{provider}</CNPJ></emit><valores><vLiq>1.00</vLiq></valores>"
        f"<DPS><infDPS><prest><CNPJ>{provider}</CNPJ></prest>"
        f"<toma><CNPJ>{recipient}</CNPJ></toma></infDPS></DPS></infNFSe></NFSe>"
    )
    legacy_first_cnpj = hashlib.sha256(provider.encode()).hexdigest()[:24]
    return NfseDocument.objects.create(
        organization=company.organization,
        company=company,
        source_nsu=f"{provider}-{recipient}",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        # Normalization from before the direction existed: no side, first CNPJ as counterparty.
        normalized_data={"service_code": "170101", "counterparty_ref": legacy_first_cnpj},
        issued_at=timezone.now(),
    )


def test_legacy_note_gets_side_and_real_counterparty_from_its_xml() -> None:
    from apps.hub.nfse_sync import nfse_match_data

    company = _company("legado-xml")
    company.cnpj_masked = "11.222.333/0001-81"
    company.save(update_fields=["cnpj_masked", "updated_at"])
    client, supplier = "07469188000160", "33000167000101"

    issued = nfse_match_data(_legacy_note(company, provider="11222333000181", recipient=client))
    taken = nfse_match_data(_legacy_note(company, provider=supplier, recipient="11222333000181"))
    foreign = nfse_match_data(_legacy_note(company, provider=supplier, recipient=client))

    assert issued["direction"] == "provided"
    assert issued["counterparty_ref"] == hashlib.sha256(client.encode()).hexdigest()[:24]
    assert taken["direction"] == "taken"
    assert taken["counterparty_ref"] == hashlib.sha256(supplier.encode()).hexdigest()[:24]
    assert foreign["direction"] == "unknown"
    assert foreign["counterparty_ref"] == ""


def test_branch_note_takes_its_side_from_the_cnpj_root() -> None:
    from apps.hub.nfse_sync import nfse_match_data

    company = _company("filial")
    company.cnpj_masked = "11.222.333/0001-81"
    company.save(update_fields=["cnpj_masked", "updated_at"])
    supplier = "33000167000101"

    taken = nfse_match_data(_legacy_note(company, provider=supplier, recipient="11222333000262"))

    assert taken["direction"] == "taken"
    assert taken["counterparty_ref"] == hashlib.sha256(supplier.encode()).hexdigest()[:24]


def test_export_xml_puts_acum_right_after_vliq() -> None:
    xml = (
        "<NFSe><infNFSe><valores><pAliqAplic>0.00</pAliqAplic><vTotalRet>0.00</vTotalRet>"
        "<vLiq>38400.00</vLiq><xOutInf>obs</xOutInf></valores></infNFSe></NFSe>"
    )

    rendered = _xml_with_dominio_accumulator(xml, "31")

    assert rendered == xml.replace("<vLiq>38400.00</vLiq>", "<vLiq>38400.00</vLiq><acum>31</acum>")


def test_export_separates_issued_and_taken_notes_for_the_right_dominio_importer() -> None:
    import csv
    import io
    import zipfile

    company = _company("export-lados")
    company.cnpj_masked = "11.222.333/0001-81"
    company.dominio_code = "109"
    company.save(update_fields=["cnpj_masked", "dominio_code", "updated_at"])
    actor = User.objects.create_user("export-lados@example.test", "safe-password-123")
    issued = _legacy_note(company, provider="11222333000181", recipient="05527009000179")
    taken = _legacy_note(company, provider="33000167000101", recipient="11222333000181")
    for document, code in ((issued, "1"), (taken, "14")):
        IntegrationArtifact.objects.create(
            organization=company.organization, document=document, accumulator_code=code
        )

    export = create_nfse_export(
        organization=company.organization, documents=[issued, taken], actor=actor
    )

    paths = {row["document_id"]: row["path"] for row in export.snapshot["documents"]}
    assert paths[str(issued.id)].startswith("NFS-e/Emitidas/109-/")
    assert paths[str(taken.id)].startswith("NFS-e/Tomadas/109-/")
    with zipfile.ZipFile(io.BytesIO(export.content.read())) as bundle:
        manifest = bundle.read("manifesto-classificacao.csv").decode("utf-8-sig")
    rows = {row["Acumulador"]: row for row in csv.DictReader(io.StringIO(manifest), delimiter=";")}
    assert rows["1"]["Importador Dominio"] == "Serviços"
    assert rows["14"]["Importador Dominio"] == "Entradas"


def test_legacy_notes_get_a_persisted_side_that_the_direction_filter_finds() -> None:
    from django.core.management import call_command

    from apps.hub.models import NfseDocumentSide
    from apps.hub.views import _filter_nfse_side

    company = _company("lado-filtro")
    company.cnpj_masked = "11.222.333/0001-81"
    company.save(update_fields=["cnpj_masked", "updated_at"])
    issued = _legacy_note(company, provider="11222333000181", recipient="05527009000179")
    taken = _legacy_note(company, provider="33000167000101", recipient="11222333000181")
    captured, _artifact, _review = _capture(
        company, {"direction": "taken", "counterparty_name": "Fornecedor Novo"}, name="nova"
    )
    assert NfseDocumentSide.objects.get(document=captured).direction == "taken"

    call_command("backfill_nfse_sides", organization=company.organization.slug)

    side = NfseDocumentSide.objects.get(document=issued)
    assert (side.direction, side.counterparty_ref) == (
        "provided",
        hashlib.sha256(b"05527009000179").hexdigest()[:24],
    )
    documents = NfseDocument.objects.filter(company=company)
    assert set(_filter_nfse_side(documents, "provided")) == {issued}
    assert set(_filter_nfse_side(documents, "taken")) == {taken, captured}
    assert not _filter_nfse_side(documents, "unknown").exists()


def test_review_offers_dominio_xml_only_once_the_note_has_an_accumulator() -> None:
    from django.test import Client

    from apps.organizations.models import Membership

    company = _company("ficha-dominio")
    _catalog(company, {"13": True, "99": False})
    owner = User.objects.create_user("ficha-dominio@example.test", "safe-password-123")
    Membership.objects.create(
        organization=company.organization, user=owner, role=Membership.Role.OWNER
    )
    xml = "<NFSe><infNFSe><valores><vLiq>440.00</vLiq></valores></infNFSe></NFSe>"
    document = NfseDocument.objects.create(
        organization=company.organization,
        company=company,
        source_nsu="724",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        normalized_data={"number": "724"},
        issued_at=timezone.now(),
    )
    review = ReviewCase.objects.create(
        organization=company.organization, document=document, reason="Sem histórico"
    )
    client = Client()
    client.force_login(owner)
    session = client.session
    session["hub_organization_id"] = str(company.organization.pk)
    session.save()

    page = client.get(f"/app/revisoes/{review.id}/")
    assert b"dominio.xml" not in page.content
    assert b'<option value="13">' in page.content and b'value="99"' not in page.content
    assert client.get(f"/app/revisoes/{review.id}/dominio.xml").status_code != 200

    client.post(f"/app/revisoes/{review.id}/resolver/", {"accumulator_code": "13"})
    page = client.get(f"/app/revisoes/{review.id}/")
    assert b"dominio.xml" in page.content
    response = client.get(f"/app/revisoes/{review.id}/dominio.xml")
    assert response.status_code == 200
    assert response.content.decode() == xml.replace(
        "<vLiq>440.00</vLiq>", "<vLiq>440.00</vLiq><acum>13</acum>"
    )
