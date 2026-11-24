"""Overlay curado, versionado no git: arquivos YAML em `data/overlay/` (D-318).

So nomes tecnicos e frases proprias; nada copiado do dicionario da Thomson Reuters. O hash do
conjunto dos arquivos entra na versao composta do pack: mudar qualquer arquivo invalida o pack.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml


class OverlayError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Overlay:
    files: dict[str, str]
    sha: str

    def data(self, name: str) -> Any:
        """Conteudo YAML ja lido de `name` (ex.: `glossary.yaml`); vazio se o arquivo nao existe."""
        text = self.files.get(name)
        if text is None:
            return {}
        try:
            return yaml.safe_load(text) or {}
        except yaml.YAMLError:
            raise OverlayError(f"YAML invalido em {name}") from None


def overlay_from_files(files: dict[str, str]) -> Overlay:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(files[name].encode("utf-8"))
        digest.update(b"\x00")
    return Overlay(dict(files), digest.hexdigest())


def load_overlay() -> Overlay:
    folder = resources.files("dominio_mcp").joinpath("data/overlay")
    files = {
        entry.name: entry.read_text(encoding="utf-8")
        for entry in folder.iterdir()
        if entry.name.endswith(".yaml")
    }
    return overlay_from_files(files)


def approved_views(overlay: Overlay) -> dict[str, str]:
    """`views_aprovadas.yaml`: nome da view -> sha256 da definicao aprovada (D-318).

    View so e consultavel em L2 com nome E hash da definicao iguais ao aprovado: definicao que
    mudou volta a bloqueada.
    """
    data = overlay.data("views_aprovadas.yaml")
    entries = data.get("views", []) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise OverlayError("views_aprovadas.yaml: 'views' deve ser uma lista")
    approved: dict[str, str] = {}
    for item in entries:
        name = item.get("name") if isinstance(item, dict) else None
        sha = item.get("sha256") if isinstance(item, dict) else None
        if not isinstance(name, str) or not isinstance(sha, str) or len(sha) != 64:
            raise OverlayError("views_aprovadas.yaml: cada item precisa de name e sha256 (64 hex)")
        try:
            int(sha, 16)
        except ValueError:
            raise OverlayError("views_aprovadas.yaml: sha256 invalido") from None
        approved[name.lower()] = sha.lower()
    return approved
