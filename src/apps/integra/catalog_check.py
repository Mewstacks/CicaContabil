"""Compare the registry with the official Integra Contador catalog page.

Nothing here runs by itself: `fetch_catalog_html` is the only function that touches the network,
it is called only by the `integra_catalog_check` command when a person runs it without `--file`,
and no test reaches it. The parser is deliberately strict: a page that stops looking like the
catalog fails loudly instead of reporting "no difference".
"""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import urlparse

from apps.integra.catalog import SERVICES, ServiceSpec

DOCUMENTATION_HOST = "apicenter.estaleiro.serpro.gov.br"
CATALOG_URL = (
    f"https://{DOCUMENTATION_HOST}/documentacao/api-integra-contador/pt/catalogo_de_servicos/"
)
FETCH_TIMEOUT_SECONDS = 30
MAX_PAGE_BYTES = 3_000_000

_CELLS_PER_ROW = 7
_DATE = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
_ID = re.compile(r"[A-Z0-9][A-Z0-9-]*")
_SERVICE_PAGE = re.compile(
    r'href="(?:\.\./)*(solucoes/[a-z0-9_-]+/[a-z0-9_-]+/servicos/[a-z0-9_-]+)/?"'
)
# Pages that document the answer of a service whose request page is already in the registry.
_COMPANION_SUFFIXES = (("_entrada", "_saida"),)


class OfficialStatus(StrEnum):
    PRODUCTION = "producao"
    CONSTRUCTION = "construcao"
    PROSPECTING = "prospeccao"
    CANCELLED = "cancelado"


_STATUS_BY_IMAGE = {
    "em produção": OfficialStatus.PRODUCTION,
    "em construção": OfficialStatus.CONSTRUCTION,
    "em prospecção": OfficialStatus.PROSPECTING,
    "cancelado": OfficialStatus.CANCELLED,
}
_STATUS_LABEL = {
    OfficialStatus.PRODUCTION: "Em produção",
    OfficialStatus.CONSTRUCTION: "Em construção",
    OfficialStatus.PROSPECTING: "Em prospecção",
    OfficialStatus.CANCELLED: "Cancelado",
}


@dataclass(frozen=True)
class OfficialService:
    id_sistema: str
    id_servico: str
    status: OfficialStatus
    tipo: str
    implantacao: str
    descricao: str
    solucao: str

    @property
    def ids(self) -> tuple[str, str]:
        return self.id_sistema, self.id_servico

    @property
    def label(self) -> str:
        return f"{self.id_sistema}/{self.id_servico}"


@dataclass
class _Cell:
    parts: list[str] = field(default_factory=list)
    alt: str = ""

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.parts)).strip()


class _CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[OfficialService] = []
        self._solution = ""
        self._heading: list[str] | None = None
        self._cells: list[_Cell] | None = None
        self._cell: _Cell | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2":
            self._heading = []
        elif tag == "tr":
            self._cells = []
        elif tag == "td" and self._cells is not None:
            self._cell = _Cell()
        elif tag == "img" and self._cell is not None:
            self._cell.alt = dict(attrs).get("alt") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._heading is not None:
            self._solution = re.sub(r"\s+", " ", "".join(self._heading)).strip()
            self._heading = None
        elif tag == "td" and self._cell is not None and self._cells is not None:
            self._cells.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._cells is not None:
            if len(self._cells) == _CELLS_PER_ROW:
                self.rows.append(self._row(self._cells))
            self._cells = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.parts.append(data)
        elif self._heading is not None:
            self._heading.append(data)

    def _row(self, cells: list[_Cell]) -> OfficialService:
        id_sistema, id_servico = cells[2].text, cells[3].text
        if not _ID.fullmatch(id_sistema) or not _ID.fullmatch(id_servico):
            raise ValueError(f"Identificador inesperado no catálogo oficial: {id_sistema!r}.")
        image = cells[4].alt.strip()
        try:
            status = _STATUS_BY_IMAGE[image.casefold()]
        except KeyError as exc:
            raise ValueError(
                f"Situação desconhecida no catálogo oficial para {id_sistema}/{id_servico}: "
                f"{image!r}."
            ) from exc
        date = _DATE.search(cells[4].text)
        return OfficialService(
            id_sistema=id_sistema,
            id_servico=id_servico,
            status=status,
            tipo=cells[5].text,
            implantacao=date.group(0) if date else "",
            descricao=cells[6].text,
            solucao=self._solution,
        )


def parse_catalog_html(html: str) -> tuple[OfficialService, ...]:
    """Read every service row of the official catalog page."""

    parser = _CatalogParser()
    parser.feed(html)
    parser.close()
    if not parser.rows:
        raise ValueError("A página não traz as tabelas do catálogo de serviços; o layout mudou?")
    return tuple(parser.rows)


def parse_service_pages(html: str) -> frozenset[str]:
    """The service pages linked in the navigation of the documentation (relative paths)."""

    return frozenset(_SERVICE_PAGE.findall(html))


def fetch_catalog_html(url: str = CATALOG_URL) -> str:
    """Download the official page. Only the documentation host is reachable, over https."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != DOCUMENTATION_HOST:
        raise ValueError("A URL precisa ser do host da documentação do Serpro, por https.")
    request = urllib.request.Request(url, headers={"User-Agent": "cica-catalog-check/1.0"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        raw: bytes = response.read(MAX_PAGE_BYTES)
    return raw.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class CatalogDiff:
    official_total: int
    official_production: int
    registry_total: int
    new_in_production: tuple[OfficialService, ...]
    left_production: tuple[tuple[ServiceSpec, OfficialService | None], ...]
    verb_changed: tuple[tuple[ServiceSpec, OfficialService], ...]
    announced: tuple[OfficialService, ...]
    unclaimed_pages: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not (self.new_in_production or self.left_production or self.verb_changed)


def _claimed_pages(registry: Mapping[str, ServiceSpec]) -> frozenset[str]:
    claimed = {spec.doc_page for spec in registry.values()}
    for page in tuple(claimed):
        for request_suffix, answer_suffix in _COMPANION_SUFFIXES:
            if page.endswith(request_suffix):
                claimed.add(page[: -len(request_suffix)] + answer_suffix)
    return frozenset(claimed)


def compare_catalog(
    official: Iterable[OfficialService],
    registry: Mapping[str, ServiceSpec] | None = None,
    *,
    service_pages: Iterable[str] | None = None,
) -> CatalogDiff:
    rows = tuple(official)
    specs = SERVICES if registry is None else registry
    official_by_ids = {row.ids: row for row in rows}
    registry_by_ids = {(spec.id_sistema, spec.id_servico): spec for spec in specs.values()}
    production = [row for row in rows if row.status is OfficialStatus.PRODUCTION]

    left = []
    changed = []
    for ids, spec in registry_by_ids.items():
        row = official_by_ids.get(ids)
        if row is None or row.status is not OfficialStatus.PRODUCTION:
            left.append((spec, row))
        elif row.tipo != spec.verb.value:
            changed.append((spec, row))
    unclaimed = (
        sorted(frozenset(service_pages) - _claimed_pages(specs)) if service_pages else []
    )
    return CatalogDiff(
        official_total=len(rows),
        official_production=len(production),
        registry_total=len(specs),
        new_in_production=tuple(row for row in production if row.ids not in registry_by_ids),
        left_production=tuple(left),
        verb_changed=tuple(changed),
        announced=tuple(
            row
            for row in rows
            if row.status is not OfficialStatus.PRODUCTION and row.ids not in registry_by_ids
        ),
        unclaimed_pages=tuple(unclaimed),
    )


def render_report(diff: CatalogDiff) -> str:
    lines = [
        f"Catálogo oficial: {diff.official_total} serviços, {diff.official_production} em "
        f"produção; registro: {diff.registry_total}."
    ]
    for new in diff.new_in_production:
        when = f", desde {new.implantacao}" if new.implantacao else ""
        lines.append(f"- novo em produção: {new.label} ({new.tipo}{when}) {new.descricao}")
    for gone, last_seen in diff.left_production:
        state = _STATUS_LABEL[last_seen.status] if last_seen else "ausente da página"
        lines.append(
            f"- deixou a produção: {gone.id_sistema}/{gone.id_servico} [{gone.key}]: {state}"
        )
    for old, current in diff.verb_changed:
        lines.append(
            f"- tipo mudou: {current.label} [{old.key}]: registro {old.verb.value}, "
            f"página {current.tipo}"
        )
    if diff.clean:
        lines.append(
            f"Sem diferença: o registro cobre os {diff.official_production} serviços em produção."
        )
    for page in diff.unclaimed_pages:
        lines.append(f"- página de serviço sem registro (informativo): {page}")
    for future in diff.announced:
        lines.append(
            f"- fora de produção e fora do registro (informativo): {future.label} "
            f"({_STATUS_LABEL[future.status]})"
        )
    return "\n".join(lines)
