"""Collection of public tax-reform updates from official government pages."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone

from apps.hub.models import ReformAlert, ReformSourceStatus

_MAX_ITEMS_PER_SOURCE = 40
_MAX_RESPONSE_BYTES = 1_000_000
_SOURCES: dict[str, str] = {
    ReformAlert.Source.RFB: "https://www.gov.br/receitafederal/pt-br/assuntos/noticias",
    ReformAlert.Source.FAZENDA: "https://www.gov.br/fazenda/pt-br/canais_atendimento/imprensa",
    ReformAlert.Source.PLANALTO: "https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/noticias",
}
_REFORM_TERMS = (
    "reforma tribut",
    "ibs",
    "cbs",
    "imposto sobre bens",
    "tributação do consumo",
    "tributacao do consumo",
)
_FISCAL_TERMS = (
    "tribut",
    "imposto",
    "benefícios fiscais",
    "beneficios fiscais",
    "crédito fiscal",
    "credito fiscal",
    "simples nacional",
)
_FISCAL_ACRONYMS = re.compile(r"\b(?:pis|cofins|irrf|itr|dctf|sped)\b", re.IGNORECASE)


@dataclass(frozen=True)
class CollectedAlert:
    title: str
    source_url: str


class _NewsLinkParser(HTMLParser):
    """Extract title links only from heading content; ignore navigation links."""

    def __init__(self, *, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self._heading_depth = 0
        self._href = ""
        self._text: list[str] = []
        self.items: list[CollectedAlert] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3"}:
            self._heading_depth += 1
        if tag == "a" and self._heading_depth:
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            title = " ".join("".join(self._text).split())
            url = urljoin(self.page_url, self._href)
            parsed = urlparse(url)
            if title and parsed.scheme == "https" and parsed.netloc == "www.gov.br":
                self.items.append(CollectedAlert(title=title[:360], source_url=url[:1_500]))
            self._href = ""
            self._text = []
        if tag in {"h2", "h3"} and self._heading_depth:
            self._heading_depth -= 1


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _relevance(title: str) -> str:
    normalized = title.casefold()
    if any(term in normalized for term in _REFORM_TERMS):
        return ReformAlert.Relevance.REFORM
    if any(term in normalized for term in _FISCAL_TERMS) or _FISCAL_ACRONYMS.search(normalized):
        return ReformAlert.Relevance.FISCAL
    return ReformAlert.Relevance.GENERAL


def _fetch_source(source: str, page_url: str) -> list[CollectedAlert]:
    request = Request(  # noqa: S310 - fixed official source registry
        page_url, headers={"User-Agent": "CICA-Radar/1.0"}
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed official source registry
        payload = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(payload) > _MAX_RESPONSE_BYTES:
        raise ValueError("Resposta maior que o limite do Radar.")
    parser = _NewsLinkParser(page_url=page_url)
    parser.feed(payload.decode("utf-8", errors="replace"))
    seen: set[str] = set()
    collected: list[CollectedAlert] = []
    for item in parser.items:
        canonical = item.source_url.split("#", maxsplit=1)[0]
        if canonical in seen:
            continue
        seen.add(canonical)
        collected.append(CollectedAlert(title=_clean_title(item.title), source_url=canonical))
        if len(collected) == _MAX_ITEMS_PER_SOURCE:
            break
    return collected


def refresh_reform_source(source: str) -> tuple[int, int]:
    """Refresh one fixed official page. Repeated collections are idempotent."""

    page_url = _SOURCES.get(source)
    if page_url is None:
        raise ValueError("Fonte do Radar não permitida.")
    status, _ = ReformSourceStatus.objects.get_or_create(source=source)
    now = timezone.now()
    try:
        items = _fetch_source(source, page_url)
    except (HTTPError, URLError, TimeoutError, UnicodeError, ValueError) as exc:
        status.last_collected_at = now
        status.last_error = str(exc)[:240]
        status.save(update_fields=["last_collected_at", "last_error", "updated_at"])
        return 0, 0

    created = updated = 0
    with transaction.atomic():
        relevant_items = 0
        for item in items:
            key = hashlib.sha256(item.source_url.encode()).hexdigest()
            relevance = _relevance(item.title)
            if relevance == ReformAlert.Relevance.GENERAL:
                # An older broad rule may have marked this same official link as
                # fiscal. Preserve its evidence, but withdraw it from the radar.
                if (
                    ReformAlert.objects.filter(source=source, external_key=key)
                    .exclude(relevance=ReformAlert.Relevance.GENERAL)
                    .update(relevance=ReformAlert.Relevance.GENERAL)
                ):
                    updated += 1
                continue
            relevant_items += 1
            content_hash = hashlib.sha256(item.title.encode()).hexdigest()
            alert, was_created = ReformAlert.objects.get_or_create(
                source=source,
                external_key=key,
                defaults={
                    "title": item.title,
                    "source_url": item.source_url,
                    "relevance": relevance,
                    "content_hash": content_hash,
                },
            )
            if was_created:
                created += 1
            elif alert.content_hash != content_hash or alert.relevance != relevance:
                alert.title = item.title
                alert.relevance = relevance
                alert.content_hash = content_hash
                alert.save(update_fields=["title", "relevance", "content_hash", "updated_at"])
                updated += 1
        status.last_collected_at = now
        status.last_success_at = now
        status.last_error = ""
        status.items_seen = relevant_items
        status.save(
            update_fields=[
                "last_collected_at",
                "last_success_at",
                "last_error",
                "items_seen",
                "updated_at",
            ]
        )
    return created, updated


def refresh_reform_sources() -> tuple[int, int, int]:
    """Refresh every source, isolating failures to the respective source status."""

    created = updated = failed = 0
    for source in _SOURCES:
        source_created, source_updated = refresh_reform_source(source)
        created += source_created
        updated += source_updated
        after_error = (
            ReformSourceStatus.objects.filter(source=source)
            .values_list("last_error", flat=True)
            .first()
        )
        if after_error:
            failed += 1
    return created, updated, failed
