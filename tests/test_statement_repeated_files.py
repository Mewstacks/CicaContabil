"""D-416 (C-05): the same account statement imported in two files never yields movements twice."""

from __future__ import annotations

from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas
from tests.test_depara_ledger import setup  # noqa: F401  (fixture reuse)

from apps.hub.direct_use_ui import movement_outcomes
from apps.hub.models import NormalizedMovement
from apps.hub.reconciliation_service import create_source_file, process_run

pytestmark = pytest.mark.django_db


def ofx(rows, prefix):
    """rows: (yyyymmdd, text, cents)."""
    body = "".join(
        f"<STMTTRN><DTPOSTED>{day}<TRNAMT>{cents / 100:.2f}"
        f"<FITID>{prefix}-{i}<MEMO>{text}</STMTTRN>"
        for i, (day, text, cents) in enumerate(rows)
    )
    return f"OFXHEADER:100\n<OFX><BANKID>748<ACCTID>123<BANKTRANLIST>{body}</BANKTRANLIST></OFX>"


def money(cents):
    text = f"{abs(cents) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if cents < 0 else "") + text


def sicredi_pdf(rows):
    """rows: (dd/mm/yyyy, text, cents) in the Sicredi statement layout."""
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(612, 792))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(40, 760, "Cooperativa: 9999")
    canvas.drawString(40, 745, "Conta: 00001-0")
    canvas.drawString(40, 725, "Extrato (Período de 01/10/2026 a 31/10/2026)")
    for x, title in ((40, "Data"), (120, "Descrição"), (350, "Documento")):
        canvas.drawString(x, 700, title)
    canvas.drawString(450, 700, "Valor (R$)")
    canvas.drawString(520, 700, "Saldo (R$)")
    canvas.drawString(120, 680, "SALDO ANTERIOR")
    balance = 1_000_000
    canvas.drawRightString(590, 680, money(balance))
    for i, (day, text, cents) in enumerate(rows):
        balance += cents
        y = 660 - i * 20
        canvas.drawString(40, y, day)
        canvas.drawString(120, y, text)
        canvas.drawRightString(500, y, money(cents))
        canvas.drawRightString(590, y, money(balance))
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def load(setup, name, content):  # noqa: F811
    source, run, _ = create_source_file(
        organization=setup["org"],
        company=setup["company"],
        financial_account=setup["account"],
        filename=name,
        content=content,
        origin="bank_statement",
    )
    process_run(str(run.pk))
    run.refresh_from_db()
    return source, run


def movements(source):
    return list(NormalizedMovement.objects.filter(source_file=source).order_by("occurred_on", "id"))


def test_pdf_after_ofx_ignores_only_the_repeated_movements(setup):  # noqa: F811
    first, _ = load(
        setup,
        "extrato.ofx",
        ofx(
            [
                ("20261005", "LIQUIDACAO BOLETO 777", -4321),
                ("20261005", "TARIFA", -555),
                ("20261005", "TARIFA", -555),
            ],
            "a",
        ).encode(),
    )
    second, run = load(
        setup,
        "extrato.pdf",
        sicredi_pdf(
            [
                ("05/10/2026", "LIQUIDACAO BOLETO SICREDI 777", -4321),  # same, other wording
                ("05/10/2026", "TARIFA SERV", -555),  # one of the two tariffs
                ("06/10/2026", "LIQUIDACAO BOLETO 777", -4321),  # other day: new
                ("07/10/2026", "PIX RECEBIDO", 10000),
            ]
        ),
    )
    states = [(m.occurred_on.day, m.amount_cents, m.review_state) for m in movements(second)]
    ignored = NormalizedMovement.ReviewState.IGNORED
    assert sorted(s[:2] for s in states if s[2] == ignored) == [(5, -4321), (5, -555)]
    assert len([s for s in states if s[2] != ignored]) == 2
    assert run.ignored_count == 2 and run.created_count == 4
    repeated = next(
        m for m in movements(second) if m.review_state == ignored and m.amount_cents == -4321
    )
    original = next(m for m in movements(first) if m.amount_cents == -4321)
    assert repeated.confidence_details["repeated_movement"] == str(original.pk)
    assert repeated.confidence_details["repeated_file"] == "extrato.ofx"
    outcome = movement_outcomes([repeated])[str(repeated.pk)]
    assert outcome["label"] == "Repetido de outro extrato · não lançado"
    assert "extrato.ofx" in outcome["help"]
    # The first file is untouched.
    assert all(m.review_state != ignored for m in movements(first))


def test_two_ofx_exports_with_other_ids_do_not_double_and_reprocessing_is_stable(setup):  # noqa: F811
    load(setup, "a.ofx", ofx([("20261010", "PIX", -9900)], "a").encode())
    second, run = load(
        setup,
        "b.ofx",
        ofx([("20261010", "PIX", -9900), ("20261010", "PIX", -9900)], "b").encode(),
    )
    states = [m.review_state for m in movements(second)]
    assert states.count(NormalizedMovement.ReviewState.IGNORED) == 1  # min(2, 1)
    process_run(str(run.pk))  # running again creates nothing and changes nothing
    assert [m.review_state for m in movements(second)] == states


def test_other_account_or_ignored_original_is_not_a_repetition(setup):  # noqa: F811
    first, _ = load(setup, "a.ofx", ofx([("20261012", "TED", -50000)], "a").encode())
    NormalizedMovement.objects.filter(source_file=first).update(
        review_state=NormalizedMovement.ReviewState.IGNORED
    )
    second, _ = load(setup, "b.ofx", ofx([("20261012", "TED", -50000)], "b").encode())
    assert movements(second)[0].review_state != NormalizedMovement.ReviewState.IGNORED


@pytest.mark.parametrize("direct_use", [False, True])
def test_movement_page_explains_the_repetition(setup, settings, direct_use):  # noqa: F811
    from django.urls import reverse

    if direct_use:
        settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(setup["org"].pk)]

    load(setup, "a.ofx", ofx([("20261014", "PIX", -1234)], "a").encode())
    second, _ = load(setup, "b.ofx", ofx([("20261014", "PIX", -1234)], "b").encode())
    repeated = movements(second)[0]
    page = setup["client"].get(reverse("hub:reconciliation-movement", args=[repeated.pk]))
    assert page.status_code == 200
    content = page.content.decode()
    assert "Repetido de outro extrato" in content and "a.ofx" in content
