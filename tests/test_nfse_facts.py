from __future__ import annotations

from datetime import date
from decimal import Decimal

from apps.hub.nfse_facts import display_document, nfse_facts

PROVIDER = "11222333000181"
RECIPIENT = "99888777000166"
KEY = "43149022211222333000181000000000012326091234567890"


def national_xml(
    *,
    tp_ret_iss: str = "2",
    tp_ret_pis_cofins: str = "3",
    ret_csll: str = "46.50",
    irrf: str = "15.00",
    cp: str = "0.00",
    extra_dps: str = "",
) -> str:
    return (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.00">'
        f'<infNFSe Id="NFS{KEY}"><nNFSe>123</nNFSe>'
        "<dhProc>2026-09-15T10:00:00-03:00</dhProc>"
        f"<emit><CNPJ>{PROVIDER}</CNPJ><xNome>Prestadora Ltda</xNome></emit>"
        "<valores><vBC>1000.00</vBC><vISSQN>50.00</vISSQN><vLiq>888.50</vLiq></valores>"
        "<DPS><infDPS><dhEmi>2026-09-14T09:00:00-03:00</dhEmi><dCompet>2026-08-31</dCompet>"
        f"{extra_dps}"
        f"<prest><CNPJ>{PROVIDER}</CNPJ></prest>"
        f"<toma><CNPJ>{RECIPIENT}</CNPJ><xNome>Tomadora SA</xNome></toma>"
        "<valores><vServPrest><vServ>1000.00</vServ></vServPrest><trib>"
        f"<tribMun><tribISSQN>1</tribISSQN><tpRetISSQN>{tp_ret_iss}</tpRetISSQN></tribMun>"
        "<tribFed><piscofins><vPis>6.50</vPis><vCofins>30.00</vCofins>"
        f"<tpRetPisCofins>{tp_ret_pis_cofins}</tpRetPisCofins></piscofins>"
        f"<vRetCP>{cp}</vRetCP><vRetIRRF>{irrf}</vRetIRRF><vRetCSLL>{ret_csll}</vRetCSLL>"
        "</tribFed></trib></valores></infDPS></DPS></infNFSe></NFSe>"
    )


def test_national_note_reads_values_retentions_and_competence() -> None:
    facts = nfse_facts(national_xml(), company_cnpj=PROVIDER)

    assert facts["kind"] == "note"
    assert facts["access_key"] == KEY
    assert facts["number"] == "123"
    assert facts["issued_on"] == date(2026, 9, 15)
    assert facts["competence"] == date(2026, 8, 31)
    assert facts["counterparty_document"] == "99.888.777/0001-66"
    assert facts["counterparty_name"] == "Tomadora SA"
    assert facts["service_amount"] == Decimal("1000.00")
    assert facts["net_amount"] == Decimal("888.50")
    assert facts["iss_retained"] == Decimal("50.00")
    # NT 007: PIS, COFINS and CSLL retained are summed in vRetCSLL; vPis/vCofins are owed.
    assert facts["crf_retained"] == Decimal("46.50")
    assert facts["irrf_retained"] == Decimal("15.00")
    assert facts["inss_retained"] == Decimal("0.00")
    assert facts["retained_total"] == Decimal("111.50")


def test_taken_note_shows_the_provider_as_counterparty() -> None:
    facts = nfse_facts(national_xml(), company_cnpj=RECIPIENT)

    assert facts["counterparty_document"] == "11.222.333/0001-81"
    assert facts["counterparty_name"] == "Prestadora Ltda"


def test_iss_not_retained_and_code_zero_mean_no_retention() -> None:
    facts = nfse_facts(
        national_xml(tp_ret_iss="1", tp_ret_pis_cofins="0", irrf="0"), company_cnpj=PROVIDER
    )

    assert facts["iss_retained"] == Decimal("0.00")
    assert facts["crf_retained"] == Decimal("0.00")
    assert facts["retained_total"] == Decimal("0.00")


def test_legacy_code_one_keeps_pis_and_cofins_in_their_own_tags() -> None:
    facts = nfse_facts(national_xml(tp_ret_pis_cofins="1", ret_csll="10.00"), company_cnpj=PROVIDER)

    assert facts["crf_retained"] == Decimal("46.50")


def test_substituting_note_points_to_the_replaced_key() -> None:
    facts = nfse_facts(
        national_xml(extra_dps="<subst><chSubstda>OLDKEY</chSubstda></subst>"),
        company_cnpj=PROVIDER,
    )

    assert facts["replaces_key"] == "OLDKEY"


def test_cancellation_event_is_not_a_note() -> None:
    event = (
        '<evento xmlns="http://www.sped.fazenda.gov.br/nfse"><infEvento Id="EVT">'
        "<dhProc>2026-09-20T10:00:00-03:00</dhProc><pedRegEvento><infPedReg>"
        f"<chNFSe>{KEY}</chNFSe><e101101><xDesc>Cancelamento</xDesc></e101101>"
        "</infPedReg></pedRegEvento></infEvento></evento>"
    )
    facts = nfse_facts(event, company_cnpj=PROVIDER)

    assert facts == {
        "kind": "event",
        "access_key": KEY,
        "situation": "cancelled",
        "issued_on": date(2026, 9, 20),
    }


def test_unreadable_xml_falls_back_to_the_stored_normalization() -> None:
    facts = nfse_facts(
        "<NFSe>",
        company_cnpj=PROVIDER,
        fallback={"amount": "12.30", "number": "77", "issued_at": "2026-07-02"},
    )

    assert facts["service_amount"] == Decimal("12.30")
    assert facts["number"] == "77"
    assert facts["competence"] == date(2026, 7, 2)


def test_cpf_is_masked_and_cnpj_is_shown_in_full() -> None:
    assert display_document("12345678901") == "***.456.789-**"
    assert display_document(PROVIDER) == "11.222.333/0001-81"
    assert display_document("") == ""


def test_unknown_layout_keeps_the_retentions_normalized_at_capture() -> None:
    facts = nfse_facts(
        "<nfse><valor>100</valor></nfse>",
        company_cnpj=PROVIDER,
        fallback={"amount": "100", "retentions": {"iss": "5.00", "pis": "0.65", "csll": "1"}},
    )

    assert facts["iss_retained"] == Decimal("5.00")
    assert facts["crf_retained"] == Decimal("1.65")
    assert facts["retained_total"] == Decimal("6.65")
