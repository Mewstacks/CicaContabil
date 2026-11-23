"""Plain text out of an e-mail, never markup: the body excerpt and a forwarded original author.

Nothing here fetches, renders or executes content: HTML is reduced to its visible text with
the standard-library parser, scripts and styles dropped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from email.message import Message
from email.utils import getaddresses
from html.parser import HTMLParser

BODY_LIMIT = 6000
_SKIP_TAGS = frozenset({"script", "style", "head", "noscript", "template"})
_FROM_LINE = re.compile(r"(?im)^[ \t>]*(?:de|from)[ \t]*:[ \t]*(.+)$")


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in {"br", "p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _Text()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:  # broken markup is only a missing hint
        return ""
    return "".join(parser.parts)


def clean_body(text: str) -> str:
    """Bounded text with collapsed blanks and no NUL byte."""

    text = text.replace("\x00", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()[:BODY_LIMIT]


def body_from_message(message: Message) -> str:
    """The readable body of a parsed e-mail (plain preferred, HTML reduced)."""

    try:
        part = message.get_body(preferencelist=("plain", "html"))  # type: ignore[attr-defined]
    except (KeyError, ValueError, AttributeError):
        return ""
    if part is None:
        return ""
    try:
        content = part.get_content()
    except Exception:  # a broken charset only loses a hint
        return ""
    if not isinstance(content, str):
        return ""
    if part.get_content_type() == "text/html":
        content = html_to_text(content)
    return clean_body(content)


def _external(line: str, internal_domains: Iterable[str]) -> list[str]:
    internal = {domain.casefold() for domain in internal_domains}
    found: list[str] = []
    for _name, address in getaddresses([line]):
        address = address.strip().casefold()
        if "@" not in address:
            continue
        if address.rsplit("@", 1)[1] in internal or address in found:
            continue
        found.append(address)
    return found


def original_sender(
    body: str, internal_domains: Iterable[str], *, attached: Message | None = None
) -> str:
    """The one outside author of a forwarded message, or "" when it is not clear.

    Looks at the attached message (``message/rfc822``) first, then the first ``De:``/``From:``
    block of the body. Two outside addresses, or only the office's own, give "".
    """

    if attached is not None:
        found = _external(str(attached.get("From", "")), internal_domains)
        return found[0] if len(found) == 1 else ""
    first = _FROM_LINE.search(body or "")
    if first:
        found = _external(first.group(1), internal_domains)
        return found[0] if len(found) == 1 else ""
    return ""


def attached_message(message: Message) -> Message | None:
    for part in message.walk():
        if part.get_content_type() == "message/rfc822":
            inner = part.get_payload()
            if isinstance(inner, list) and inner and isinstance(inner[0], Message):
                return inner[0]
            return None
    return None


def mailbox_domain(address: str) -> str:
    return address.rsplit("@", 1)[1].casefold() if "@" in address else ""
