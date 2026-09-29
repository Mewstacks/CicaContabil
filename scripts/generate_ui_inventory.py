"""Generate the auditable CICA UI route matrix from Django's live URLconf."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402


def walk(
    patterns: list[URLPattern | URLResolver], prefix: str = "", namespace: str = ""
) -> Iterator[tuple[str, str]]:
    for item in patterns:
        route = f"{prefix}{item.pattern}"
        if isinstance(item, URLResolver):
            child_namespace = ":".join(filter(None, (namespace, item.namespace or item.app_name)))
            yield from walk(item.url_patterns, route, child_namespace)
        elif item.name:
            yield ":".join(filter(None, (namespace, item.name))), f"/{route}".replace("//", "/")


def route_type(name: str, path: str) -> str:
    lowered = f"{name} {path}".lower()
    download_tokens = (
        "download",
        ".pdf",
        ".xml",
        "baixar",
        "arquivo/",
        "relatorios/",
        "mfa-qr",
    )
    if any(token in lowered for token in download_tokens):
        return "download"
    if any(token in lowered for token in ("webhook", "callback", "status", "health")):
        return "estado"
    action_tokens = (
        "activity-add-evidence", "activity-block", "activity-complete", "-confirm-import",
        "confirm-reconciliation", "resolve-review", "-revoke", "-resend", "switch-office",
        "set-theme", "onboarding-complete", "issue-guide", "bulk-consult", "next-page",
        "decide-dte", "run-action", "upload", "bulk-action", "export-create",
        "imap-connect", "oauth-start", "app-save", "mailbox-configure", "disconnect",
        "destination-configure", "start-support", "end-support", "-sync", "-delete",
    )
    if any(token in lowered for token in action_tokens):
        return "ação"
    return "tela"


def module_for(name: str, path: str) -> str:
    value = f"{name} {path}"
    rules = (
        ("platform:", "Console Mewstack"), ("intelligence:", "Copiloto e aprendizado"),
        ("accounts:", "Autenticação e MFA"), ("/app/nfse", "NFS-e"),
        ("/app/guias", "Guias e DCTFWeb"), ("integra-contador", "Integra Contador"),
        ("conciliacao", "Conciliação"), ("triagem", "Triagem"), ("radar", "Radar"),
        ("atividades", "Atividades"), ("empresas", "Empresas"), ("equipe", "Equipe"),
        ("certificados", "Certificados"), ("configur", "Configurações"),
    )
    for token, label in rules:
        if token in value:
            return label
    return "Público e acesso" if not path.startswith("/app/") else "Central operacional"


def profile_for(name: str, path: str) -> str:
    if name.startswith("platform:"):
        return "admin da plataforma / suporte delegado"
    if name.startswith("intelligence:"):
        return "proprietário / administrador / operador autorizado"
    if path.startswith("/app/"):
        return "proprietário / administrador / operador / financeiro / auditor (conforme permissão)"
    if name.startswith("accounts:"):
        return "usuário autenticado"
    return "visitante / convidado"


def fixture_for(kind: str, module: str) -> str:
    if kind == "download":
        return "artefato sintético autorizado"
    if kind == "ação":
        return "registro sintético + confirmação/CSRF"
    if kind == "estado":
        return "execução sintética pendente/concluída/incerta"
    if module == "Público e acesso":
        return "sessão anônima, convite válido/expirado e formulário inválido"
    return "tenant sintético com estado vazio, carregado, filtrado, bloqueado e sem permissão"


def main() -> None:
    excluded = ("admin:", "api:")
    rows = []
    for name, path in walk(get_resolver().url_patterns):
        if name.startswith(excluded) or "webhooks/" in path or path.startswith("/admin/"):
            continue
        kind = route_type(name, path)
        module = module_for(name, path)
        rows.append((name, path, kind, module, profile_for(name, path), fixture_for(kind, module)))
    rows.sort(key=lambda row: (row[3], row[1], row[0]))
    counts = {
        kind: sum(row[2] == kind for row in rows)
        for kind in ("tela", "estado", "ação", "download")
    }
    print("# Matriz de rotas, telas, estados, ações e downloads — 28/09/2026")
    print()
    print("Gerada diretamente do URLconf atual por `python scripts/generate_ui_inventory.py`. ")
    print("Django Admin, APIs, webhooks e endpoints do agente não integram a auditoria visual.")
    print()
    print(
        f"Total: **{len(rows)} rotas** — {counts['tela']} telas, "
        f"{counts['estado']} estados, {counts['ação']} ações e "
        f"{counts['download']} downloads."
    )
    print()
    print("| Rota | Caminho | Tipo | Módulo | Perfis | Fixture/estado de QA |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        values = (f"`{value}`" if index < 3 else value for index, value in enumerate(row))
        print("| " + " | ".join(values) + " |")
    print()
    print(
        "A classificação é um inventário de cobertura, não autorização para executar "
        "integrações reais. Os estados sintéticos devem cobrir vazio, carregado, filtrado, "
        "erro recuperável, bloqueio, permissão negada, resultado incerto, texto longo e "
        "paginação quando aplicável."
    )


if __name__ == "__main__":
    main()
