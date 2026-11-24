"""CNPJ alfanumérico (Receita Federal, emitido desde jul/2026).

Raiz e ordem aceitam letras; os dois dígitos verificadores seguem numéricos. O que já era
numérico precisa dar exatamente o resultado de antes: o legado não muda (L3/L4).
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.serialization import pkcs12
from django.core.exceptions import ValidationError

from apps.common.cnpj import cnpj_candidates, normalize_cnpj, strip_document
from apps.hub.forms import OfficeIdentityForm
from apps.hub.imports import _company_for_row
from apps.hub.models import ClientCompany, DataSource
from apps.hub.nfse_facts import nfse_facts
from apps.hub.nfse_sync import _counterparty, _party_identifier, _validate_certificate_company
from apps.hub.search import search_workspace
from apps.hub.services import certificate_cnpjs
from apps.intelligence.connectors import _format_cnpj
from apps.organizations.models import Organization
from apps.platform.forms import SelfServiceSignupForm
from apps.platform.models import PlatformConfiguration
from pki_support import make_pfx

ALNUM = "12ABC34501DE35"  # exemplo oficial da Receita: 12.ABC.345/01DE-35
ALNUM_MASKED = "12.ABC.345/01DE-35"
NUMERIC = "11222333000181"
RECIPIENT = "99888777000166"
KEY = "43149022211222333000181000000000012326091234567890"


def _note_xml(provider: str, recipient: str) -> str:
    return (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.00">'
        f'<infNFSe Id="NFS{KEY}"><nNFSe>123</nNFSe>'
        "<dhProc>2026-09-15T10:00:00-03:00</dhProc>"
        f"<emit><CNPJ>{provider}</CNPJ><xNome>Prestadora Ltda</xNome></emit>"
        "<valores><vLiq>888.50</vLiq></valores>"
        "<DPS><infDPS><dhEmi>2026-09-14T09:00:00-03:00</dhEmi><dCompet>2026-08-31</dCompet>"
        f"<prest><CNPJ>{provider}</CNPJ></prest>"
        f"<toma><CNPJ>{recipient}</CNPJ><xNome>Tomadora SA</xNome></toma>"
        "<valores><vServPrest><vServ>1000.00</vServ></vServPrest></valores>"
        "</infDPS></DPS></infNFSe></NFSe>"
    )


def test_the_official_example_passes_the_check_digits() -> None:
    assert normalize_cnpj(ALNUM_MASKED) == ALNUM
    with pytest.raises(ValidationError):
        normalize_cnpj("12.ABC.345/01DE-00")


@pytest.mark.parametrize(
    "raw",
    [
        "",
        None,
        "12.345.678/0001-95",
        "12345678000195",
        " 11222333000181 ",
        "CNPJ: 12.345.678/0001-95",
        "123.456.789-09",
        "abc",
        "12.345.678/0001",
        "00.000.000/0000-00",
    ],
)
def test_numeric_input_keeps_exactly_the_legacy_digits(raw: object) -> None:
    assert strip_document(raw) == re.sub(r"\D", "", str(raw or ""))


def test_alphanumeric_document_keeps_its_letters_uppercased() -> None:
    assert strip_document(ALNUM_MASKED) == ALNUM
    assert strip_document("12.abc.345/01de-35") == ALNUM
    assert strip_document(f"CNPJ: {ALNUM_MASKED}") == ALNUM


def test_candidates_in_free_text_keep_the_legacy_match_and_add_valid_alphanumerics() -> None:
    assert cnpj_candidates(f"ESCRITORIO TESTE:{ALNUM}") == {ALNUM}
    assert cnpj_candidates(f"EMPRESA:{NUMERIC} FILIAL") == {NUMERIC}
    assert cnpj_candidates("EMPRESA:12ABC34501DE00") == set()  # dígitos verificadores errados
    assert cnpj_candidates("SEM DOCUMENTO 123") == set()


def test_nfse_facts_reads_an_alphanumeric_provider_and_recipient() -> None:
    as_provider = nfse_facts(_note_xml(ALNUM, RECIPIENT), company_cnpj=ALNUM)
    assert as_provider["counterparty_document"] == "99.888.777/0001-66"

    as_recipient = nfse_facts(_note_xml(ALNUM, RECIPIENT), company_cnpj=RECIPIENT)
    assert as_recipient["counterparty_document"] == ALNUM_MASKED

    same_root_branch = nfse_facts(_note_xml(ALNUM, RECIPIENT), company_cnpj="12ABC34502DE02")
    assert same_root_branch["counterparty_document"] == "99.888.777/0001-66"


def test_nfse_sync_reads_alphanumeric_parties() -> None:
    from defusedxml import ElementTree

    root = ElementTree.fromstring(_note_xml(ALNUM, RECIPIENT))
    assert _party_identifier(root, {"emit", "prest"}) == ALNUM
    assert _counterparty({"CNPJ": [ALNUM_MASKED]}) != ""
    assert _counterparty({"CNPJ": [ALNUM_MASKED]}) == _counterparty({"CNPJ": [ALNUM]})
    assert _counterparty({"CNPJ": [NUMERIC]}) != _counterparty({"CNPJ": [ALNUM]})


def test_certificate_with_an_alphanumeric_cnpj_is_recognised() -> None:
    blob = make_pfx(password="segredo-123", cnpj=ALNUM)
    _, parsed, _ = pkcs12.load_key_and_certificates(blob, b"segredo-123")
    assert parsed is not None
    assert certificate_cnpjs(parsed) == {ALNUM}

    stored = SimpleNamespace(company=SimpleNamespace(cnpj_masked=ALNUM_MASKED))
    _validate_certificate_company(parsed, stored)  # type: ignore[arg-type]


def test_certificate_of_another_root_is_still_refused() -> None:
    blob = make_pfx(password="segredo-123", cnpj=ALNUM)
    _, parsed, _ = pkcs12.load_key_and_certificates(blob, b"segredo-123")
    assert parsed is not None
    other = SimpleNamespace(company=SimpleNamespace(cnpj_masked="19.131.243/0001-97"))
    with pytest.raises(ValidationError):
        _validate_certificate_company(parsed, other)  # type: ignore[arg-type]


def test_connector_and_platform_format_an_alphanumeric_cnpj() -> None:
    assert _format_cnpj(ALNUM) == ALNUM_MASKED
    assert _format_cnpj(ALNUM_MASKED) == ALNUM_MASKED
    assert _format_cnpj(NUMERIC) == "11.222.333/0001-81"
    assert _format_cnpj("123") == ""
    assert PlatformConfiguration(provider_cnpj=ALNUM).provider_cnpj_display == ALNUM_MASKED
    numeric = PlatformConfiguration(provider_cnpj=NUMERIC)
    assert numeric.provider_cnpj_display == "11.222.333/0001-81"


def test_cnpj_inputs_accept_letters_on_a_phone_keyboard() -> None:
    office = OfficeIdentityForm().fields["cnpj"].widget.attrs
    signup = SelfServiceSignupForm().fields["cnpj"].widget.attrs
    for attrs in (office, signup):
        assert attrs.get("inputmode") != "numeric"
        assert attrs.get("autocapitalize") == "characters"


@pytest.mark.django_db
def test_spreadsheet_import_matches_an_existing_alphanumeric_company() -> None:
    organization = Organization.objects.create(name="Acme", slug="acme-alnum")
    source = DataSource.objects.create(
        organization=organization, kind=DataSource.Kind.OTHER_MANUAL, label="Planilha"
    )
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa Nova",
        cnpj_masked=ALNUM_MASKED,
        dominio_code="900",
        data_source=source,
    )
    found = _company_for_row(organization, source, {"cnpj": ALNUM_MASKED, "nome": "Empresa Nova"})
    assert found is not None and found.pk == company.pk

    numeric = ClientCompany.objects.create(
        organization=organization,
        name="Empresa Antiga",
        cnpj_masked="11.222.333/0001-81",
        dominio_code="901",
        data_source=source,
    )
    old = _company_for_row(organization, source, {"cnpj": "11.222.333/0001-81"})
    assert old is not None and old.pk == numeric.pk


@pytest.mark.django_db
def test_workspace_search_finds_an_alphanumeric_company() -> None:
    from apps.hub.models import OperationalActivity

    organization = Organization.objects.create(name="Acme", slug="acme-busca")
    ClientCompany.objects.create(
        organization=organization,
        name="Empresa Letras",
        cnpj_masked=ALNUM_MASKED,
        dominio_code="902",
    )
    ClientCompany.objects.create(
        organization=organization,
        name="Empresa Numeros",
        cnpj_masked="11.222.333/0001-81",
        dominio_code="903",
    )
    groups = search_workspace(
        query="12ABC345",
        companies=ClientCompany.objects.filter(organization=organization),
        activities=OperationalActivity.objects.none(),
        documents=None,
    )
    titles = [result.title for group in groups for result in group.results]
    assert titles == ["Empresa Letras"]

    numeric_groups = search_workspace(
        query="222333",
        companies=ClientCompany.objects.filter(organization=organization),
        activities=OperationalActivity.objects.none(),
        documents=None,
    )
    numeric_titles = [result.title for group in numeric_groups for result in group.results]
    assert numeric_titles == ["Empresa Numeros"]
