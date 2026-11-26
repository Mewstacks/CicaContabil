"""Prévia das baixas do multifontes e conta pelo código do título (D-421). Dados fictícios."""

from __future__ import annotations

from tests.test_multisource_matching import D1, RECEIVABLES, collection, inst, item, position
from tests.test_multisource_suggested_accounts import ROWS, row

from apps.hub.multisource.matching import BankLine, simulate
from apps.hub.multisource.planned_entries import (
    ALREADY,
    AMBIGUOUS,
    READY,
    plan_settlements,
    planned_summary,
    render_planned_csv,
)
from apps.hub.multisource.suggested_accounts import Chart, suggest_accounts
from apps.hub.multisource.title_position import RECEIVABLE


def chart(extra=()):
    return Chart([r for r in [*ROWS, *extra] if r["chart_company_code"] == 900])


def collected():
    bank = [BankLine(1, D1, 140000 + 1120 + 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    return simulate(
        bank,
        collection=collection(
            item("CLIENTE ALFA LTDA", 140000, interest=1120),
            item("CLIENTE BETA SA", 445667, our="26/000002-2"),
        ),
        receivables=RECEIVABLES,
    )


def test_settlements_are_planned_with_passage_and_customer_accounts():
    result = collected()
    planned = plan_settlements(result, suggest_accounts(result, chart()))
    assert [(e.debit, e.credit, e.amount_cents, e.situation) for e in planned] == [
        ("9 COBRANÇA", "500 CLIENTE ALFA LTDA - 9", 140000, READY),
        ("9 COBRANÇA", "132 JUROS ATIVOS", 1120, READY),
        ("9 COBRANÇA", "501 CLIENTE BETA SA - 2", 445667, READY),
    ]
    assert planned[0].history.startswith("Baixa NF 100 parc. 1/1 — CLIENTE ALFA LTDA - 9")
    csv_text = render_planned_csv(planned)
    assert "Juros/multa recebidos — francesinha" in csv_text
    assert "- Prontos quando as contas forem confirmadas: 3 · 5.867,87" in planned_summary(planned)


def test_titles_already_settled_in_the_domínio_are_not_planned_again():
    result = collected()
    # Posição do mês: a parcela do cliente A sumiu (quitada); a do cliente B segue com saldo.
    reference = position(
        RECEIVABLE,
        *[i for i in RECEIVABLES.installments if i.party_code != "1"],
    )
    planned = plan_settlements(
        result, suggest_accounts(result, chart()), {"receivables": reference}
    )
    # A (e seus juros) já baixado no Domínio; B continua com saldo na posição do mês.
    assert [e.situation for e in planned] == [ALREADY, ALREADY, READY]
    # Sem a posição do mês, a mesma simulação fica pronta.
    assert {e.situation for e in plan_settlements(result, suggest_accounts(result, chart()))} == {
        READY
    }


def test_party_code_is_the_account_code_and_beats_repeated_names():
    repeated = (
        row(600, "11020010014", "CLIENTE ALFA LTDA"),
        row(601, "11020010015", "CLIENTE ALFA LTDA - 812"),
    )
    plan = chart(repeated)
    assert [a.code for a in plan.party("receivable", "CLIENTE ALFA LTDA", "601")] == [601]
    assert [a.code for a in plan.party("receivable", "CLIENTE ALFA LTDA", "7")] == [500, 600, 601]
    positions = position(RECEIVABLE, inst(RECEIVABLE, "7", "CLIENTE ALFA LTDA", "100", D1, 140000))
    bank = [BankLine(1, D1, 140000, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank, collection=collection(item("CLIENTE ALFA LTDA", 140000)), receivables=positions
    )
    planned = plan_settlements(result, suggest_accounts(result, plan))
    assert planned[0].situation == AMBIGUOUS  # código 7 não é conta: três contas com o mesmo nome
