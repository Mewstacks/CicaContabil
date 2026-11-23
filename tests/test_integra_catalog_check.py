"""T10.1: the script that compares the registry with the official catalog page.

The network is only reachable when a human runs the command; no test may touch it.
"""

from __future__ import annotations

import urllib.request
from collections import Counter
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.integra import catalog_check
from apps.integra.catalog import SERVICES
from apps.integra.catalog_check import (
    CATALOG_URL,
    OfficialService,
    OfficialStatus,
    compare_catalog,
    fetch_catalog_html,
    parse_catalog_html,
    parse_service_pages,
    render_report,
)

OFFICIAL_PAGE = (
    Path(__file__).parent / "fixtures" / "integra" / "catalogo_de_servicos_2026-10-15.html"
)
COMMAND = "apps.integra.management.commands.integra_catalog_check"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the catalog check must never reach the network in a test")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)


def _official() -> tuple[OfficialService, ...]:
    return parse_catalog_html(OFFICIAL_PAGE.read_text(encoding="utf-8"))


def _row(
    id_sistema: str,
    id_servico: str,
    *,
    status: OfficialStatus = OfficialStatus.PRODUCTION,
    tipo: str = "Consultar",
    implantacao: str = "31/10/2026",
) -> OfficialService:
    return OfficialService(
        id_sistema=id_sistema,
        id_servico=id_servico,
        status=status,
        tipo=tipo,
        implantacao=implantacao,
        descricao="Linha de teste",
        solucao="Integra-Teste",
    )


def _html_row(id_sistema: str, id_servico: str, alt: str, tipo: str, date: str) -> str:
    return (
        "<tr><td>900</td><td>9.9</td>"
        f'<td style="text-align: center;"><code>{id_sistema}</code></td>'
        f'<td style="text-align: center;"><code>{id_servico}</code></td>'
        '<td style="text-align: center;"><a class="glightbox" href="../imgs/concluido.png">'
        f'<img alt="{alt}" src="../imgs/concluido.png" title="{alt}"></a> <br>{date}</td>'
        f'<td style="text-align: center;"><code>{tipo}</code></td><td>Serviço novo</td></tr>'
    )


def _with_extra_row(html: str, row: str) -> str:
    marker = "</tbody>"
    index = html.index(marker)
    return html[:index] + row + html[index:]


def test_the_official_page_lists_119_services_in_four_states() -> None:
    rows = _official()

    assert len(rows) == 119
    assert Counter(row.status for row in rows) == {
        OfficialStatus.PRODUCTION: 99,
        OfficialStatus.CONSTRUCTION: 6,
        OfficialStatus.PROSPECTING: 13,
        OfficialStatus.CANCELLED: 1,
    }
    assert Counter(row.tipo for row in rows if row.status is OfficialStatus.PRODUCTION) == {
        "Consultar": 61, "Emitir": 23, "Declarar": 6, "Monitorar": 5, "Apoiar": 4,
    }
    assert len({(row.id_sistema, row.id_servico) for row in rows}) == 119


def test_a_row_carries_system_service_status_date_type_and_solution() -> None:
    by_ids = {(row.id_sistema, row.id_servico): row for row in _official()}

    declare = by_ids[("PGDASD", "TRANSDECLARACAO11")]
    assert declare.status is OfficialStatus.PRODUCTION
    assert (declare.tipo, declare.implantacao, declare.solucao) == (
        "Declarar", "23/09/2022", "Integra-SN"
    )
    assert "Entregar declaração mensal" in declare.descricao
    assert by_ids[("DASNSIMEI", "TRANSDECLARACAO151")].status is OfficialStatus.CONSTRUCTION
    assert by_ids[("DASNSIMEI", "TRANSDECLARACAO151")].implantacao == ""
    assert by_ids[("PARC-PAEX", "OBTEREXTRATOPDF171")].status is OfficialStatus.PROSPECTING
    assert by_ids[("AUTENTICAPROCURADOR", "EXPIRARAUTORIZACAO82")].status is (
        OfficialStatus.CANCELLED
    )
    assert by_ids[("SICALC", "CONSOLIDAR54")].implantacao == "15/10/2026"


def test_the_registry_matches_the_official_page() -> None:
    diff = compare_catalog(_official())

    assert diff.clean
    assert diff.new_in_production == ()
    assert diff.left_production == ()
    assert diff.verb_changed == ()
    assert len(diff.announced) == 20
    assert "Sem diferença" in render_report(diff)


def test_a_new_production_service_is_reported_by_name() -> None:
    quantity = _row("CAIXAPOSTAL", "QTQMSG64")
    diff = compare_catalog((*_official(), quantity))

    assert not diff.clean
    assert diff.new_in_production == (quantity,)
    report = render_report(diff)
    assert "CAIXAPOSTAL/QTQMSG64" in report
    assert "novo em produção" in report


def test_a_registry_service_that_leaves_production_is_reported() -> None:
    cancelled = [
        _row(row.id_sistema, row.id_servico, status=OfficialStatus.CANCELLED, tipo=row.tipo)
        if (row.id_sistema, row.id_servico) == ("SITFIS", "RELATORIOSITFIS92")
        else row
        for row in _official()
        if (row.id_sistema, row.id_servico) != ("PGMEI", "DIVIDAATIVA24")
    ]

    diff = compare_catalog(cancelled)

    gone = {(spec.id_sistema, spec.id_servico): official for spec, official in diff.left_production}
    assert set(gone) == {("SITFIS", "RELATORIOSITFIS92"), ("PGMEI", "DIVIDAATIVA24")}
    assert gone[("SITFIS", "RELATORIOSITFIS92")] is not None
    assert gone[("PGMEI", "DIVIDAATIVA24")] is None
    assert not diff.clean
    assert "deixou a produção" in render_report(diff)


def test_a_changed_type_is_reported() -> None:
    rows = [
        _row(row.id_sistema, row.id_servico, tipo="Emitir")
        if (row.id_sistema, row.id_servico) == ("PGMEI", "DIVIDAATIVA24")
        else row
        for row in _official()
    ]

    diff = compare_catalog(rows)

    assert [spec.key for spec, _ in diff.verb_changed] == ["pgmei.divida"]
    assert not diff.clean
    assert "tipo mudou" in render_report(diff)


def test_services_that_are_not_in_production_are_informational() -> None:
    announced = _row("NOVO", "FUTURO999", status=OfficialStatus.PROSPECTING)

    diff = compare_catalog((*_official(), announced))

    assert diff.clean
    assert announced in diff.announced
    assert "NOVO/FUTURO999" in render_report(diff)


def test_a_page_without_the_catalog_tables_fails_instead_of_looking_clean() -> None:
    with pytest.raises(ValueError, match="tabelas do catálogo"):
        parse_catalog_html("<html><body><p>Manutenção</p></body></html>")


def test_an_unknown_status_image_fails_instead_of_being_guessed() -> None:
    page = _with_extra_row(
        OFFICIAL_PAGE.read_text(encoding="utf-8"),
        _html_row("NOVO", "ESTADO1", "Em homologação", "Consultar", "01/11/2026"),
    )

    with pytest.raises(ValueError, match="Em homologação"):
        parse_catalog_html(page)


def test_service_pages_in_the_menu_that_no_registry_entry_claims_are_listed() -> None:
    nav = (
        '<a href="../solucoes/integra-sn/pgdasd/servicos/consultar_declaracao_por_ano_pa/">x</a>'
        '<a href="../solucoes/integra-sn/pgdasd/servicos/entregar_declaracao_mensal_saida/">x</a>'
        '<a href="../solucoes/integra-caixapostal/caixapostal/servicos/'
        'obter_quantidade_de_mensagens/">x</a>'
        '<a href="../solucoes/integra-sn/pgdasd/changelog/">x</a>'
    )

    pages = parse_service_pages(nav)
    diff = compare_catalog(_official(), service_pages=pages)

    assert pages == frozenset({
        "solucoes/integra-sn/pgdasd/servicos/consultar_declaracao_por_ano_pa",
        "solucoes/integra-sn/pgdasd/servicos/entregar_declaracao_mensal_saida",
        "solucoes/integra-caixapostal/caixapostal/servicos/obter_quantidade_de_mensagens",
    })
    assert diff.unclaimed_pages == (
        "solucoes/integra-caixapostal/caixapostal/servicos/obter_quantidade_de_mensagens",
    )
    assert diff.clean
    assert "obter_quantidade_de_mensagens" in render_report(diff)


def test_the_command_reads_a_saved_page_and_reports_no_difference() -> None:
    output = StringIO()

    call_command("integra_catalog_check", "--file", str(OFFICIAL_PAGE), stdout=output)

    text = output.getvalue()
    assert "99 em produção" in text
    assert f"registro: {len(SERVICES)}" in text
    assert "Sem diferença" in text


def test_strict_mode_fails_when_the_registry_is_behind(tmp_path: Path) -> None:
    page = tmp_path / "catalogo.html"
    page.write_text(
        _with_extra_row(
            OFFICIAL_PAGE.read_text(encoding="utf-8"),
            _html_row("CAIXAPOSTAL", "QTQMSG64", "Em produção", "Consultar", "31/10/2026"),
        ),
        encoding="utf-8",
    )
    output = StringIO()

    call_command("integra_catalog_check", "--file", str(page), stdout=output)
    assert "CAIXAPOSTAL/QTQMSG64" in output.getvalue()

    with pytest.raises(CommandError, match="QTQMSG64"):
        call_command("integra_catalog_check", "--file", str(page), "--strict", stdout=StringIO())


def test_without_a_file_the_command_goes_through_the_single_fetch_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_fetch(url: str = CATALOG_URL) -> str:
        calls.append(url)
        return OFFICIAL_PAGE.read_text(encoding="utf-8")

    monkeypatch.setattr(f"{COMMAND}.fetch_catalog_html", fake_fetch)
    output = StringIO()

    call_command("integra_catalog_check", stdout=output)

    assert calls == [CATALOG_URL]
    assert "Sem diferença" in output.getvalue()


def test_fetch_only_talks_to_the_documentation_host_over_https() -> None:
    for url in (
        "http://apicenter.estaleiro.serpro.gov.br/documentacao/x/",
        "https://example.com/documentacao/x/",
        "file:///etc/passwd",
    ):
        with pytest.raises(ValueError, match="host da documentação"):
            fetch_catalog_html(url)


def test_fetch_is_bounded_and_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            seen["limit"] = limit
            return "<html>Catálogo</html>".encode()

    def fake_urlopen(request: Any, timeout: float) -> Response:
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert fetch_catalog_html() == "<html>Catálogo</html>"
    assert seen["url"] == CATALOG_URL
    assert 0 < seen["timeout"] <= 60
    assert 0 < seen["limit"] <= 5_000_000
    assert catalog_check.CATALOG_URL.startswith("https://apicenter.estaleiro.serpro.gov.br/")
