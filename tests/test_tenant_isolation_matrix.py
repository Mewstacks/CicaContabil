"""Matriz de isolamento: um escritório (A) não enxerga nem altera o que é de outro (B).

Prova em tempo de execução, sobre o resolver de URLs inteiro, e não por leitura do código:

1. Dois escritórios com todos os módulos ligados. B recebe uma linha de CADA modelo de tenant
   (povoador genérico por `_meta`, mais receitas para o que só abre num estado exato) com o texto
   "ZZ-B-SEGREDO-n" em todo campo livre.
2. Para cada rota com id: o dono de B pede a própria linha (controle positivo) e o mesmo pedido com
   um id que não existe em lugar nenhum (fantasma). Só vale o par em que as duas respostas
   diferem; senão a rota nem enxerga a linha de B e o teste não provaria nada.
3. O dono de A pede a linha de B pelo mesmo caminho (GET e POST, com cada `action` que a view
   compara; PATCH/PUT/DELETE na API). Tem de receber o que um id inexistente recebe (403/404), o
   corpo nunca traz o texto nem um id de B, e nenhuma linha muda (B) nem nasce (A). Em rotas com
   dois ids, um de cada escritório também; e com a sessão e o cabeçalho da API forjados para B.
4. Controle simétrico: no mesmo pedido, a linha equivalente de A é achada. Sem isso um 404 de A
   poderia ser A bloqueado, e não o filtro de escritório.
5. Id de B no corpo ou na consulta (`BODY_SPECS`: troca de escritório, ação em lote, filtro por
   empresa, lote do agente): o mesmo controle positivo e o mesmo veredito.
6. Rotas sem id (listas, busca, notificações, JSON): GET como dono, operador e auditor de A, com
   consulta envenenada (busca pelo texto de B, filtros com o id da empresa e do escritório de B)
   e com a sessão forjada para B. O agente Windows de A pede trabalho com a assinatura dele.
7. Diferencial: as páginas estáveis de A saem iguais quando um terceiro escritório ganha dados,
   o que pega contagem e total sem filtro, que texto nenhum denuncia.

O detector é testado também: com o dono e o agente de B no lugar dos de A, a mesma matriz tem de
acusar leitura, escrita, corpo e lista. `-s` imprime o relatório de cobertura. Rota nova no
resolver, modelo novo sem construtor ou exclusão sem motivo derrubam o teste: obrigam a decidir.
Vazamento real não se conserta aqui: entra em `KNOWN_LEAKS` e vira xfail estrito.
"""

from __future__ import annotations

import logging
import socket
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from django.db import transaction
from django.test import override_settings
from pytest_django.plugin import DjangoDbBlocker

from tenant_matrix_support import (
    BODY_SPECS,
    MARK_B,
    WORLD_SETTINGS,
    WORLD_SKIP_MODELS,
    MatrixResult,
    Observed,
    Runner,
    bound_models,
    build_world,
    collect_routes,
    judge,
    leaks_in,
    pairing_gap,
    report_lines,
    run_matrix,
)

# Sem o marcador o pytest-django agenda estes testes depois dos transacionais, e
# `test_nfse_export_migration` deixa o hub na migração 0067: a matriz não acharia as colunas das
# migrações novas. Rodando sozinhos, sem o marcador, o banco de teste nem seria criado.
# Não é `transaction=True`: o mundo de teste é desfeito pelo próprio fixture `matrix`.
pytestmark = pytest.mark.django_db

ROUTES = collect_routes()
BY_KEY = {route.key: route for route in ROUTES}

# --------------------------------------------------------------------------------------------
# Decisões congeladas
# --------------------------------------------------------------------------------------------

# Modelos de tenant que o povoador genérico não conseguiu montar (chave = modelo ou receita).
UNBUILDABLE: frozenset[str] = frozenset()

# Modelos ligados a escritório que o mundo de teste não cria, e por quê (ver o suporte).
SKIPPED_MODELS = frozenset(
    {
        "hub.ControlPlaneBinding",
        "platform.TenantLifecycle",
        "platform.PlatformAccess",
        "platform.SupportSession",
        "platform.PlatformConfiguration",
    }
)

_PLATFORM = (
    "console da plataforma (staff) ou sessão de suporte: fora da matriz de escritório; "
    "o isolamento dele é de test_platform_isolation.py"
)
_PUBLIC = (
    "página pública ou fluxo de autenticação: não serve linha de escritório "
    "(a credencial é o token de uso único; ver test_invitation_takeover.py)"
)
_GLOBAL = "dado global por desenho (referência pública), não há linha de B para pedir"
_DEMO = "atende só o escritório demo (is_demo); escritório real recebe 404 por desenho"
_MACHINE = "rota de máquina com credencial própria (token do MCP ou código de cadastro do agente)"

EXCLUDED_ROUTES: dict[str, str] = {
    "platform:configuration": _PLATFORM,
    "platform:fiscal-calendar": _PLATFORM,
    "platform:dashboard": _PLATFORM,
    "platform:tenants": _PLATFORM,
    "platform:tenant-detail": _PLATFORM,
    "platform:start-support": _PLATFORM,
    "platform:end-support": _PLATFORM,
    "platform:asaas-webhook": "webhook de pagamento autenticado por token do Asaas, sem sessão",
    "hub:home": _PUBLIC,
    "hub:demo-entry": _PUBLIC,
    "hub:proposal": _PUBLIC,
    "hub:proposal-cnpj": _PUBLIC,
    "hub:signup": _PUBLIC,
    "hub:signup-verify": _PUBLIC,
    "hub:activate": _PUBLIC,
    "hub:login": _PUBLIC,
    "hub:logout": _PUBLIC,
    "hub:password-reset": _PUBLIC,
    "hub:password-reset-done": _PUBLIC,
    "hub:password-reset-confirm": _PUBLIC,
    "hub:password-reset-complete": _PUBLIC,
    "hub:legal": _PUBLIC,
    "hub:reform-analysis": "o alerta do Radar é global (fontes oficiais), não é de escritório",
    "privacy-purpose-detail": _GLOBAL,
    "privacy-purpose-detail~fmt": _GLOBAL,
    "hub:demo-guide-pdf": _DEMO,
    "hub:demo-parcelamento-das-pdf": _DEMO,
    "intelligence-mcp": _MACHINE,
    "intelligence-agent-enroll": _MACHINE,
    "intelligence-agent-sync": _MACHINE,
    "agent-v2-enroll": _MACHINE,
}

# Rotas com id no caminho sem controle positivo e o motivo provável. Vazio é o ideal.
ACCEPTED_UNPAIRED: dict[str, str] = {}

# O mesmo para ids no corpo ou na consulta: o campo só é lido depois de uma validação que o
# POST mínimo da matriz não atravessa (a rota em si já tem prova pelo id do caminho).
_DEEP_FORM = "o formulário recusa (400) antes de ler o campo; exige action e campos próprios"
_SECOND_ID = "o campo é um segundo id, lido só com o movimento em estado de candidato"
_IGNORED = "o filtro não muda a página (corpo igual ao do id inexistente): nada a distinguir"
ACCEPTED_UNPAIRED_BODY: dict[str, str] = {
    "hub:nfse-center#company_id@GET": _IGNORED,
    "hub:setup#batch_id@GET": _IGNORED,
    "hub:setup#source_id@GET": _IGNORED,
    "hub:reconciliation-configuration#period_id@POST": _DEEP_FORM,
    "hub:reconciliation-configuration#rule_id@POST": _DEEP_FORM,
    "hub:confirm-reconciliation#source_entry@POST": _SECOND_ID,
    "hub:reconciliation-movement#entry_id@POST": _SECOND_ID,
    "hub:reconciliation-movement#reconciliation_id@POST": _SECOND_ID,
}

ACCEPTED_UNCOVERED = frozenset(EXCLUDED_ROUTES) | frozenset(ACCEPTED_UNPAIRED)

# Vazamentos reais achados pela matriz: rota -> "LEAK-n: o que vaza". Cada um vira xfail estrito.
KNOWN_LEAKS: dict[str, str] = {}

# Páginas que têm de mostrar linhas de B ao próprio dono de B; sem isso a varredura não prova nada.
MUST_SHOW_ROWS = frozenset(
    {
        "hub:dashboard",
        "hub:activities",
        "hub:companies",
        "hub:notifications",
        "hub:reconciliation",
        "hub:team",
        "hub:triage",
        "company-list",
        "privacy-request-list",
    }
)

BODY_KEYS = sorted(spec.key for spec in BODY_SPECS if spec.route not in EXCLUDED_ROUTES)
PARAM_KEYS = sorted(r.key for r in ROUTES if r.uuid_params and r.key not in EXCLUDED_ROUTES)
SWEEP_KEYS = sorted(r.key for r in ROUTES if not r.uuid_params and r.key not in EXCLUDED_ROUTES)


def _marked(keys: list[str]) -> list[object]:
    return [
        pytest.param(key, marks=pytest.mark.xfail(strict=True, reason=KNOWN_LEAKS[key]))
        if key in KNOWN_LEAKS
        else key
        for key in keys
    ]


# --------------------------------------------------------------------------------------------
# A matriz inteira, calculada uma vez
# --------------------------------------------------------------------------------------------


@contextmanager
def sandbox(media: Path) -> Iterator[None]:
    """Arquivos num diretório descartável, sem rede, sem ruído de log e com as chaves ligadas."""

    no_network = OSError("rede desligada na matriz de isolamento")
    logging.disable(logging.CRITICAL)
    try:
        with (
            override_settings(MEDIA_ROOT=str(media), **WORLD_SETTINGS),
            mock.patch.object(socket.socket, "connect", side_effect=no_network),
            mock.patch.object(socket, "getaddrinfo", side_effect=socket.gaierror("sem rede")),
        ):
            yield
    finally:
        logging.disable(logging.NOTSET)


@pytest.fixture(scope="module")
def matrix(
    django_db_setup: None,
    django_db_blocker: DjangoDbBlocker,
    tmp_path_factory: pytest.TempPathFactory,
) -> MatrixResult:
    """Roda tudo dentro de uma transação desfeita no fim: nada fica no banco."""

    with (
        django_db_blocker.unblock(),
        sandbox(tmp_path_factory.mktemp("media")),
        transaction.atomic(),
    ):
        result = run_matrix(build_world(), ROUTES, EXCLUDED_ROUTES)
        transaction.set_rollback(True)
    return result


# --------------------------------------------------------------------------------------------
# O mundo e a cobertura
# --------------------------------------------------------------------------------------------


def test_the_world_of_b_has_a_row_for_every_tenant_model(matrix: MatrixResult) -> None:
    world = matrix.world
    assert WORLD_SKIP_MODELS == SKIPPED_MODELS
    assert set(world.b.failures) == set(UNBUILDABLE), world.b.failures
    wanted = {m._meta.label for m in bound_models()} - SKIPPED_MODELS
    assert wanted - set(world.b.rows) == set()
    assert wanted - set(world.a.rows) == set()


def _printable(text: str) -> str:
    """O console do Windows (cp1252) não aceita tudo; o relatório nunca derruba o teste."""

    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    return text.encode(encoding, errors="replace").decode(encoding)


def test_coverage_report(matrix: MatrixResult) -> None:
    """Imprime o relatório (visível com `-s`) antes de qualquer asserção sobre ele."""

    lines = report_lines(matrix, ROUTES, EXCLUDED_ROUTES, ACCEPTED_UNPAIRED, ACCEPTED_UNPAIRED_BODY)
    print(_printable("\n".join(lines)))
    assert matrix.requests > 5_000


def test_every_route_has_exactly_one_decision(matrix: MatrixResult) -> None:
    keys = {route.key for route in ROUTES}
    proved = {k for k, r in matrix.param.items() if r.proved}
    unpaired = {k for k, r in matrix.param.items() if not r.proved}
    swept = set(matrix.sweep)
    excluded = set(EXCLUDED_ROUTES)

    groups = [proved, unpaired, swept, excluded]
    assert sum(len(group) for group in groups) == len(set().union(*groups)), "rota em dois grupos"
    assert set().union(*groups) == keys, f"rota sem decisão: {sorted(keys - set().union(*groups))}"
    assert excluded <= keys
    assert (excluded | unpaired) == ACCEPTED_UNCOVERED, (
        f"fora de ACCEPTED_UNCOVERED: {sorted((excluded | unpaired) - ACCEPTED_UNCOVERED)}; "
        f"sobrando nele: {sorted(ACCEPTED_UNCOVERED - (excluded | unpaired))}"
    )


def test_both_nfse_collection_modes_were_exercised(matrix: MatrixResult) -> None:
    """A carteira por planilha só existe em modo procuração; a página de A1, só no certificado."""

    assert matrix.param["hub:roster-batch"].proved
    assert matrix.param["hub:roster-errors"].proved
    assert "hub:certificates" in matrix.sweep


def test_the_run_stays_inside_its_request_budget(matrix: MatrixResult) -> None:
    """Orçamento em requisições, não em segundos: não depende da máquina estar ocupada."""

    assert matrix.requests < 15_000, f"{matrix.requests} requisições"


# --------------------------------------------------------------------------------------------
# A prova, rota a rota
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", _marked(PARAM_KEYS))
def test_a_foreign_id_is_refused_and_nothing_changes(matrix: MatrixResult, key: str) -> None:
    result = matrix.param[key]
    if key in ACCEPTED_UNPAIRED:
        assert not result.proved, f"{key} ganhou controle positivo: tire-o de ACCEPTED_UNPAIRED"
        return
    assert result.proved, f"{key} sem controle positivo: {dict(result.unpaired)}"
    assert not result.problems, "\n".join(result.problems[:8])


@pytest.mark.parametrize("key", _marked(SWEEP_KEYS))
def test_a_route_without_id_never_shows_or_touches_b(matrix: MatrixResult, key: str) -> None:
    result = matrix.sweep[key]
    assert result.requests, key
    assert not result.problems, "\n".join(result.problems[:8])


def test_body_specs_point_at_real_routes() -> None:
    assert {spec.route for spec in BODY_SPECS} <= set(BY_KEY)
    assert len({spec.key for spec in BODY_SPECS}) == len(BODY_SPECS)
    assert set(ACCEPTED_UNPAIRED_BODY) <= {spec.key for spec in BODY_SPECS}


@pytest.mark.parametrize("key", _marked(BODY_KEYS))
def test_a_foreign_id_in_the_body_or_query_is_refused(matrix: MatrixResult, key: str) -> None:
    result = matrix.body[key]
    if key in ACCEPTED_UNPAIRED_BODY:
        assert not result.proved, (
            f"{key} ganhou controle positivo: tire-o de ACCEPTED_UNPAIRED_BODY"
        )
        return
    assert result.proved, f"{key} sem controle positivo: {dict(result.unpaired)}"
    assert not result.problems, "\n".join(result.problems[:8])


def test_a_page_of_a_does_not_change_when_another_office_appears(matrix: MatrixResult) -> None:
    """Diferencial: pega contagem e total calculados sem filtro, que o marcador não vê."""

    assert matrix.differential_checked >= 30, matrix.differential_checked
    assert not matrix.differential, matrix.differential


def test_the_sweep_is_not_vacuous(matrix: MatrixResult) -> None:
    shown = {key for key, result in matrix.sweep.items() if result.informative}
    assert shown >= MUST_SHOW_ROWS, (
        f"o dono de B não vê as próprias linhas em {MUST_SHOW_ROWS - shown}"
    )


# --------------------------------------------------------------------------------------------
# O detector também tem de ser testado
# --------------------------------------------------------------------------------------------


B_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def _world_stub() -> SimpleNamespace:
    return SimpleNamespace(b=SimpleNamespace(marker=MARK_B.lower(), mark=MARK_B), b_ids={B_ID})


def _observed(status: int, body: str = "", location: str = "") -> Observed:
    return Observed(status, location, "text/html", body, (), 1, 0.0)


def test_the_judge_accepts_what_a_missing_id_gets_and_flags_everything_else() -> None:
    world = _world_stub()
    ghost = _observed(404)
    control = _observed(302, location="/app/atividades/pk/")

    assert judge(world, _observed(404), ghost, control, ["pk"]) == []
    assert judge(world, _observed(403), ghost, control, ["pk"]) == []
    assert judge(world, _observed(302, location="/app/atividades/"), ghost, control, ["pk"]) == []
    assert judge(world, _observed(404, "Nada aqui"), ghost, control, ["pk"]) == []

    assert judge(world, _observed(404, f"x {MARK_B}-1 y"), ghost, control, ["pk"])
    assert judge(world, _observed(404, f"x {B_ID}"), ghost, control, ["pk"])
    assert judge(world, _observed(200, "ok"), ghost, control, ["pk"])
    assert judge(world, _observed(302, location="/app/atividades/pk/"), ghost, control, ["pk"])
    assert judge(world, _observed(500), ghost, control, ["pk"])


def test_pairing_requires_the_control_to_differ_from_a_missing_id() -> None:
    marker = MARK_B.lower()
    list_page = _observed(302, location="/app/empresas/")

    assert pairing_gap(marker, list_page, list_page).startswith("igual ao inexistente")
    assert pairing_gap(marker, _observed(404), _observed(404))
    assert pairing_gap(marker, _observed(200), _observed(404)) == ""
    assert pairing_gap(marker, _observed(400), _observed(404)) == ""
    assert pairing_gap(marker, _observed(200, f"{MARK_B}-1"), _observed(200, "vazio")) == ""


def test_leaks_in_only_reports_what_belongs_to_b() -> None:
    world = _world_stub()

    assert leaks_in(world, "nada de mais") == []
    assert leaks_in(world, "ZZ-A-PROPRIO-1 e a empresa de A") == []
    assert leaks_in(world, f"{MARK_B}-9")
    assert leaks_in(world, B_ID)
    assert leaks_in(world, B_ID, exclude=[B_ID]) == []


def test_the_matrix_catches_a_cross_tenant_read_and_write(tmp_path: Path) -> None:
    """Põe o dono e o agente de B no lugar dos de A: o mesmo código tem de acusar tudo."""

    with sandbox(tmp_path):
        runner = Runner(build_world(), impostor=True)
        read = runner.run_route(BY_KEY["hub:activity-detail"])
        write = runner.run_route(BY_KEY["hub:activity-complete"])
        agent = runner.run_route(BY_KEY["agent-v2-crosscheck-batch"])
        listing = runner.run_sweep(BY_KEY["hub:activities"])
        switch = next(spec for spec in BODY_SPECS if spec.route == "hub:switch-office")
        body = runner.run_body(switch, BY_KEY[switch.route])

    assert any(pair.problems for pair in read.pairs), "leitura de B por A passou sem alarme"
    assert any("gravou" in problem for problem in write.problems), "escrita em B passou sem alarme"
    assert agent.problems, "agente de A mexendo no trabalho de B passou sem alarme"
    assert listing.problems, "lista de B vista por A passou sem alarme"
    assert body.problems, "id de B no corpo aceito para A passou sem alarme"
