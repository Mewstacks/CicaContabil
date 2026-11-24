"""D-398: simpler screens for a direct-use office; other offices keep the current screens."""

from __future__ import annotations

import pytest
from django.urls import reverse
from tests.test_depara_ledger import BASE, _load, setup  # noqa: F401
from tests.test_direct_use import OCTOBER_BANK, OCTOBER_LEDGER, _october, enabled  # noqa: F401

from apps.hub.models import ClientCompany, NormalizedMovement

pytestmark = pytest.mark.django_db


def _html(client, name, *args, query=""):
    response = client.get(reverse(name, args=args) + query)
    assert response.status_code == 200, response.status_code
    return response.content.decode()


def test_overview_and_import_show_only_the_main_journey(enabled):  # noqa: F811
    html = _html(enabled["client"], "hub:reconciliation")
    assert "Conciliação bancária" in html
    assert "1. Importar extrato" in html and "3. Enviar ao Domínio" in html
    assert "Mais opções" in html and "Regras DE-PARA" in html
    assert 'name="purpose" value="general"' in html
    assert 'name="origin" value="bank_statement"' in html
    assert "Lote físico" not in html and "Como preparar o Razão" not in html
    assert "Prévia para conferência" not in html
    assert "Valores repetidos ou parecidos no Razão" in html


def test_other_offices_keep_the_current_screens(setup):  # noqa: F811
    html = _html(setup["client"], "hub:reconciliation")
    assert "Nova importação" in html and "Resumo da carteira" in html
    assert "Lote físico" in html and "1. Importar extrato" not in html


def test_result_page_separates_repeated_values_from_similar_ones(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
        source = _october(enabled, OCTOBER_BANK, OCTOBER_LEDGER)
    html = _html(enabled["client"], "hub:reconciliation-source-review", source.pk)
    assert "Resultado do extrato" in html
    # Two equal 5,55 lines in the bank and only one in the Razão: one may be missing.
    assert "Valor repetido · um pode faltar no Razão" in html
    assert "?state=confirmed" in html  # result cards filter the list
    assert ">Mais opções</summary>" in html


def test_portfolio_offers_import_for_companies_without_account(enabled):  # noqa: F811
    company = ClientCompany.objects.create(
        organization=enabled["org"], name="Sem extrato", dominio_code="77"
    )
    html = _html(enabled["client"], "hub:reconciliation-portfolio", query="?status=all")
    assert "Sem extrato importado" in html
    assert f"open_upload=1&amp;upload_company={company.pk}" in html
    assert "Importar extrato" in html
    opened = _html(
        enabled["client"],
        "hub:reconciliation",
        query=f"?open_upload=1&upload_company={company.pk}&upload_origin=bank_statement",
    )
    assert "data-modal-initial-open" in opened


def test_titles_open_the_only_account_directly(enabled):  # noqa: F811
    response = enabled["client"].get(reverse("hub:reconciliation-titles"))
    assert response.status_code == 302
    assert response["Location"].endswith(f"?account={enabled['account'].pk}")
    html = enabled["client"].get(response["Location"]).content.decode()
    assert "Ainda não há títulos lidos do Domínio" in html and "revisados" not in html


def test_home_points_to_the_bank_reconciliation(enabled):  # noqa: F811
    html = _html(enabled["client"], "hub:dashboard")
    assert "Conciliação bancária: importe o extrato e envie ao Domínio" in html
    assert reverse("hub:reconciliation") in html


def test_depara_page_speaks_of_rules(enabled):  # noqa: F811
    html = _html(enabled["client"], "hub:reconciliation-depara")
    assert "Regras DE-PARA" in html and "Revisar sugestões" not in html


def _october_source(enabled, django_capture_on_commit_callbacks):  # noqa: F811
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
        return _october(enabled, OCTOBER_BANK, OCTOBER_LEDGER)


def test_confirmed_rows_do_not_say_they_were_not_confirmed(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """D-399: a confirmed row never shows the "not confirmed" hint next to its badge."""
    source = _october_source(enabled, django_capture_on_commit_callbacks)
    confirmed = _html(
        enabled["client"], "hub:reconciliation-source-review", source.pk, query="?state=confirmed"
    )
    assert "Conferido com o Razão" in confirmed
    assert "Conferido: mesma data, valor e direção no Razão." in confirmed
    assert "não foi conferido sozinho" not in confirmed
    pending = _html(enabled["client"], "hub:reconciliation-source-review", source.pk)
    assert "fora do Razão" not in pending and "Fora do Razão" not in pending
    assert "não conferido" in pending and "Não conferidos" in pending


def test_movement_page_says_what_the_cica_did_instead_of_asking_accounts(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """D-399: a movement already in the Razão is not presented as missing debit/credit."""
    source = _october_source(enabled, django_capture_on_commit_callbacks)
    movement = NormalizedMovement.objects.filter(source_file=source, amount_cents=-555).first()
    html = _html(enabled["client"], "hub:reconciliation-movement", movement.pk)
    assert "Movimento do extrato" in html and "O QUE A CICA FEZ" in html
    assert "Valor repetido · um pode faltar no Razão" in html
    assert "Completar os dados obrigatórios" not in html
    free = NormalizedMovement.objects.get(source_file=source, amount_cents=9000)
    back = reverse("hub:reconciliation-source-review", args=[source.pk])
    html = _html(
        enabled["client"], "hub:reconciliation-movement", free.pk, query=f"?return_to={back}"
    )
    assert "Sem regra · não lançado" in html and "Classificar à mão" in html
    assert f"{reverse('hub:reconciliation-movement', args=[free.pk])}#movement-review-form" in html
    assert "Voltar ao resultado" in html


def test_ledger_page_lists_the_statement_as_imported(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    source = _october_source(enabled, django_capture_on_commit_callbacks)
    html = _html(
        enabled["client"],
        "hub:reconciliation-ledger-request",
        query=f"?company={source.company_id}&account={source.financial_account_id}&month=2026-10",
    )
    assert "Aguardando revisão" not in html
    assert "Importado" in html and "Ver resultado" in html


def test_other_offices_keep_the_review_movement_page(setup, django_capture_on_commit_callbacks):  # noqa: F811
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, BASE)
        source = _october(setup, OCTOBER_BANK, OCTOBER_LEDGER)
    movement = NormalizedMovement.objects.get(source_file=source, amount_cents=9000)
    html = _html(setup["client"], "hub:reconciliation-movement", movement.pk)
    assert "Revisar movimento" in html and "O QUE A CICA FEZ" not in html
