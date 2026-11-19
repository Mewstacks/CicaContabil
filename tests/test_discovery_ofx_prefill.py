"""D-377: an OFX only prefills the bank identity of a discovered-account link review."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.hub.models import (
    CompanyAccessGrant,
    FinancialAccount,
    NormalizedMovement,
    ReconciliationLedgerMapping,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation import parse_ofx, read_ofx_account_identity, validate_ofx_account
from test_account_candidate_navigation import login
from test_account_discovery import discovered as discovered_fixture
from test_account_discovery import discovered_profile as discovered_profile_fixture
from test_account_discovery import sources as sources_fixture
from test_account_discovery_navigation import confirmed, detail_url
from test_account_discovery_navigation import web as web_fixture
from test_account_source_details import protected

sources = sources_fixture
discovered_profile = discovered_profile_fixture
discovered = discovered_fixture
web = web_fixture
pytestmark = pytest.mark.django_db


def synthetic_ofx(bank="748", branch="0101", account="00012345-6", rows=2) -> bytes:
    transactions = "".join(
        f"<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>2026090{day}<TRNAMT>-1{day}.50"
        f"<FITID>SYN-{day}<MEMO>Movimento sintetico {day}</STMTTRN>"
        for day in range(1, rows + 1)
    )
    branch_tag = f"<BRANCHID>{branch}" if branch else ""
    return (
        "OFXHEADER:100\nDATA:OFXSGML\n<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS>"
        f"<BANKACCTFROM><BANKID>{bank}{branch_tag}<ACCTID>{account}"
        f"<ACCTTYPE>CHECKING</BANKACCTFROM><BANKTRANLIST>{transactions}</BANKTRANLIST>"
        "</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
    ).encode()


def upload(content: bytes, name="extrato.ofx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/x-ofx")


def state():
    return (
        protected(),
        FinancialAccount.objects.count(),
        ReconciliationLedgerMapping.objects.count(),
        ReconciliationSourceFile.objects.count(),
        NormalizedMovement.objects.count(),
        AuditEvent.objects.count(),
    )


def test_identity_matches_exactly_what_the_import_requires():
    content = synthetic_ofx()
    identity = read_ofx_account_identity(content)
    assert (identity.bank_id, identity.branch_id, identity.account_id) == (
        "748",
        "0101",
        "00012345-6",
    )
    assert identity.account_reference == parse_ofx(content).account_reference
    assert identity.account_reference == "748:0101:00012345-6"
    assert identity.transaction_count == 2
    assert identity.first_date.isoformat() == "2026-09-01"
    assert identity.last_date.isoformat() == "2026-09-02"
    without_branch = read_ofx_account_identity(synthetic_ofx(branch=""))
    assert without_branch.branch_id == ""
    assert without_branch.account_reference == "748:00012345-6"


def test_prefill_fills_only_bank_identity_and_writes_nothing(web):
    url = detail_url(web["coverage"], web["chart"])
    before = state()
    response = web["client"].post(url, {"action": "prefill", "statement": upload(synthetic_ofx())})
    assert response.status_code == 200
    assert state() == before
    form = response.context["discovery_form"]
    assert not form.is_bound
    assert form["bank_code"].value() == "748"
    assert form["account_reference"].value() == "748:0101:00012345-6"
    assert form["bank_inflow_side"].value() in (None, "")
    for name in ("bank_association_confirmed", "account_active_and_postable"):
        assert not form[name].value()
    html = response.content.decode()
    assert "Dados lidos do extrato. Confira antes de confirmar." in html
    assert "01/09/2026 a 02/09/2026" in html
    assert "O arquivo não foi guardado." in html
    assert response["Cache-Control"] == "no-store, private"


def test_prefilled_confirmation_links_an_account_the_ofx_import_accepts(web, organization):
    coverage, chart = web["coverage"], web["chart"]
    content = synthetic_ofx()
    prefill = web["client"].post(
        detail_url(coverage, chart), {"action": "prefill", "statement": upload(content)}
    )
    form = prefill.context["discovery_form"]
    data = confirmed(coverage, chart)
    data.update(
        bank_code=form["bank_code"].value(),
        account_reference=form["account_reference"].value(),
    )
    response = web["client"].post(detail_url(coverage, chart), data)
    assert response.status_code == 302
    account = FinancialAccount.objects.get()
    assert account.account_reference == "748:0101:00012345-6"
    validate_ofx_account(
        parse_ofx(content),
        organization=organization,
        company=coverage.company,
        financial_account=account,
    )


def test_manual_reference_shape_is_what_prefill_prevents(web, organization):
    coverage, chart = web["coverage"], web["chart"]
    response = web["client"].post(detail_url(coverage, chart), confirmed(coverage, chart))
    assert response.status_code == 302
    account = FinancialAccount.objects.get()
    with pytest.raises(ValueError):
        validate_ofx_account(
            parse_ofx(synthetic_ofx()),
            organization=organization,
            company=coverage.company,
            financial_account=account,
        )


@pytest.mark.parametrize(
    ("content", "name"),
    [
        (b"not an ofx", "extrato.ofx"),
        (synthetic_ofx(), "extrato.csv"),
        (synthetic_ofx(bank=""), "extrato.ofx"),
        (synthetic_ofx(rows=0), "extrato.qfx"),
    ],
)
def test_invalid_files_prefill_nothing_and_explain(web, content, name):
    url = detail_url(web["coverage"], web["chart"])
    before = state()
    response = web["client"].post(url, {"action": "prefill", "statement": upload(content, name)})
    assert response.status_code == 400
    assert state() == before
    form = response.context["discovery_form"]
    assert not form.is_bound
    assert not form["bank_code"].value()
    assert not form["account_reference"].value()
    assert response.context["discovery_prefill"] is None
    assert response.context["discovery_prefill_error"]
    assert 'aria-invalid="true"' in response.content.decode()


def test_missing_or_duplicated_file_is_refused(web):
    url = detail_url(web["coverage"], web["chart"])
    before = state()
    assert web["client"].post(url, {"action": "prefill"}).status_code == 400
    response = web["client"].post(
        url,
        {"action": "prefill", "statement": [upload(synthetic_ofx()), upload(synthetic_ofx())]},
    )
    assert response.status_code == 400
    assert response.context["discovery_prefill"] is None
    assert state() == before


def test_oversized_file_is_refused_before_parsing(web, monkeypatch):
    monkeypatch.setattr("apps.hub.account_discovery_views.MAX_BYTES", 64)
    response = web["client"].post(
        detail_url(web["coverage"], web["chart"]),
        {"action": "prefill", "statement": upload(synthetic_ofx())},
    )
    assert response.status_code == 400
    assert "25 MB" in response.context["discovery_prefill_error"]


@pytest.mark.parametrize("role", ["auditor"])
def test_read_only_profile_cannot_prefill(organization, web, role):
    client, member = login(organization, role)
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=member,
        company=web["coverage"].company,
        modules=["reconciliation"],
    )
    assert client.get(detail_url(web["coverage"], web["chart"])).status_code == 200
    before = state()
    response = client.post(
        detail_url(web["coverage"], web["chart"]),
        {"action": "prefill", "statement": upload(synthetic_ofx())},
    )
    assert response.status_code == 403
    assert state() == before


def test_ready_link_does_not_offer_or_accept_prefill(web):
    coverage, chart = web["coverage"], web["chart"]
    assert (
        web["client"].post(detail_url(coverage, chart), confirmed(coverage, chart)).status_code
        == 302
    )
    page = web["client"].get(detail_url(coverage, chart))
    assert 'id="discovery-ofx-form"' not in page.content.decode()
    before = state()
    response = web["client"].post(
        detail_url(coverage, chart), {"action": "prefill", "statement": upload(synthetic_ofx())}
    )
    assert response.status_code == 400
    assert response.context["discovery_prefill"] is None
    assert state() == before


def test_page_offers_prefill_before_link_form(web):
    html = web["client"].get(detail_url(web["coverage"], web["chart"])).content.decode()
    assert html.index('id="discovery-ofx-form"') < html.index('id="discovery-link-form"')
    assert 'enctype="multipart/form-data"' in html
    assert 'accept=".ofx,.qfx"' in html
