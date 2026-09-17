"""Interpret Caixa Postal responses using the Serpro field names and date format."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime


class DtePayloadError(ValueError):
    """A successful HTTP response did not contain usable Caixa Postal data."""


def data_object(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("dados")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DtePayloadError("O Serpro devolveu dados ilegíveis da Caixa Postal.") from exc
    if not isinstance(raw, dict):
        raise DtePayloadError("O Serpro não devolveu dados da Caixa Postal.")
    code = raw.get("codigo")
    if code is not None and str(code).zfill(2) != "00":
        raise DtePayloadError(f"A Caixa Postal recusou a consulta (código {code}).")
    return raw


def list_page(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, str]:
    data = data_object(payload)
    contents = data.get("conteudo")
    if isinstance(contents, list):
        pages = [page for page in contents if isinstance(page, dict)]
        if not pages:
            return [], False, ""
    else:
        pages = [data]
    rows: list[dict[str, Any]] = []
    more_available = False
    next_pointer = ""
    for page in pages:
        values: object = None
        for key in ("listaMensagens", "mensagens", "itens"):
            if key in page:
                values = page[key]
                break
        if not isinstance(values, list):
            raise DtePayloadError("A Caixa Postal não devolveu uma lista de mensagens.")
        rows.extend(value for value in values if isinstance(value, dict))
        more_available = more_available or (
            str(page.get("indicadorUltimaPagina", "S")).upper() == "N"
        )
        if str(page.get("indicadorUltimaPagina", "S")).upper() == "N":
            next_pointer = str(page.get("ponteiroProximaPagina", "")).strip()
            if not re.fullmatch(r"\d{1,24}", next_pointer):
                next_pointer = ""
    return rows, more_available, next_pointer


def list_rows(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows, more_available, _next_pointer = list_page(payload)
    return rows, more_available


def detail_row(payload: dict[str, Any], *, expected_isn: str) -> dict[str, Any]:
    data = data_object(payload)
    values = data.get("conteudo")
    if not isinstance(values, list):
        raise DtePayloadError("O Serpro não devolveu o teor da mensagem.")
    for row in values:
        if isinstance(row, dict) and str(row.get("isn", "")).zfill(10) == expected_isn.zfill(10):
            return row
    raise DtePayloadError("O Serpro devolveu detalhes de outra mensagem.")


def source_date(value: object, clock: object = "") -> datetime | None:
    date_value = str(value or "").strip()
    if not date_value:
        return None
    if re.fullmatch(r"\d{8}", date_value):
        time_value = str(clock or "").strip().zfill(6)
        if not re.fullmatch(r"\d{6}", time_value):
            time_value = "000000"
        try:
            naive = datetime.strptime(date_value + time_value, "%Y%m%d%H%M%S")
        except ValueError:
            return None
        return timezone.make_aware(naive, timezone.get_default_timezone())
    return parse_datetime(date_value)


def value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        field = row.get(key)
        if field is not None:
            return str(field)
    return ""


def subject(row: dict[str, Any]) -> str:
    text = value(row, "assuntoModelo", "assunto", "subject")
    parameter = value(row, "valorParametroAssunto")
    return text.replace("++VARIAVEL++", parameter) if parameter else text


def body(row: dict[str, Any]) -> str:
    """Substitute provider variables before the web layer turns HTML into safe text."""

    template = value(row, "corpoModelo")
    variables: Iterable[object] = row.get("variaveis", [])
    if not isinstance(variables, list):
        return template
    for index, replacement in enumerate(variables[:40], start=1):
        template = template.replace(f"++{index}++", str(replacement))
    return template


class _TextOnlyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth += 1
        if tag in {"p", "br", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def body_text(row: dict[str, Any]) -> str:
    parser = _TextOnlyParser()
    parser.feed(body(row))
    return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
