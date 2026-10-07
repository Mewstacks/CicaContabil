"""Fiscal facts of a stored NFS-e, read from its immutable XML.

The list, its totals and the retention reports need the values of every note in SQL: service
and net amount, the retained taxes, the real competence and whether an event cancelled or
substituted the note. ``NfseDocument.normalized_data`` is immutable and ~99% of the stored
notes predate the retention keys, so these facts live in ``NfseDocumentSide`` and are
re-derived from the XML whenever ``FACTS_VERSION`` changes.

Retentions follow the national layout (``infNFSe/DPS/infDPS/valores/trib``):

* ISS is retained when ``tribMun/tpRetISSQN`` is 2 (tomador) or 3 (intermediário); the amount
  is ``vISSQN``.
* Since NT SE/CGNFS-e 007/2026 the retained PIS, COFINS and CSLL are summed in ``vRetCSLL`` and
  ``tpRetPisCofins`` (0, 3-9) says which of them entered the sum; 0 means nothing retained.
  The legacy code 1 meant PIS/COFINS retained with their amounts in ``vPis``/``vCofins`` and
  CSLL alone in ``vRetCSLL``; legacy code 2 meant PIS/COFINS not retained. The three are shown
  together as CRF, the way the Domínio and the DCTFWeb treat the code 5952.
* IRRF is ``vRetIRRF`` and the social security retention (INSS) is ``vRetCP``.

Events (``evento``) are not notes: codes 101101/101103 cancel and 105102 substitutes the note
whose key is in ``chNFSe``. A note carrying ``chSubstda`` substitutes the referenced one.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from defusedxml import DefusedXmlException, ElementTree  # type: ignore[import-untyped]
from django.db.models import Case, Exists, OuterRef, Q, Value, When
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

FACTS_VERSION = 1

ZERO = Decimal("0.00")
_CANCEL_EVENTS = {"e101101", "e101103"}
_SUBSTITUTION_EVENTS = {"e105102"}
_PROVIDER_GROUPS = {"emit", "emitente", "prest", "prestador", "prestadorservico", "infprestador"}
_RECIPIENT_GROUPS = {"toma", "tomador", "tomadorservico", "inftomador", "dest"}


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _index(root: Any) -> dict[str, str]:
    """First non-empty text of each local tag name, in document order."""

    values: dict[str, str] = {}
    for element in root.iter():
        name = _local(element.tag)
        if not name or name in values:
            continue
        text = (element.text or "").strip()
        if text:
            values[name] = text
    return values


def _first(values: dict[str, str], *names: str) -> str:
    for name in names:
        if values.get(name):
            return values[name]
    return ""


def _money(values: dict[str, str], *names: str) -> Decimal | None:
    raw = _first(values, *names)
    if not raw:
        return None
    try:
        amount = Decimal(raw.replace(",", ".") if raw.count(",") == 1 and "." not in raw else raw)
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return amount.quantize(Decimal("0.01"))


def _party_document(root: Any, groups: set[str]) -> str:
    for group in root.iter():
        if _local(group.tag).casefold() not in groups:
            continue
        for element in group.iter():
            if _local(element.tag).casefold() in {"cnpj", "cpf"}:
                digits = re.sub(r"\D", "", element.text or "")
                if len(digits) in {11, 14}:
                    return digits
    return ""


def _party_name(root: Any, groups: set[str]) -> str:
    for group in root.iter():
        if _local(group.tag).casefold() not in groups:
            continue
        for element in group.iter():
            if _local(element.tag).casefold() in {"xnome", "razaosocial", "nome"}:
                name = " ".join((element.text or "").split())
                if name:
                    return name[:160]
    return ""


def display_document(digits: str) -> str:
    """CNPJ in full (public registry); CPF masked, as the LGPD asks of a personal identifier."""

    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    if len(digits) == 11:
        return f"***.{digits[3:6]}.{digits[6:9]}-**"
    return ""


def _local_date(raw: str) -> date | None:
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is not None:
        if timezone.is_aware(parsed):
            parsed = timezone.localtime(parsed)
        return parsed.date()
    try:
        return parse_date(raw[:10])
    except ValueError:
        return None


def _event_facts(root: Any) -> dict[str, Any]:
    situation = ""
    for element in root.iter():
        name = _local(element.tag).casefold()
        if name in _SUBSTITUTION_EVENTS:
            situation = "substituted"
            break
        if name in _CANCEL_EVENTS:
            situation = "cancelled"
            break
    if not situation:
        # Without the event group, the code is in infEvento/@Id: EVT + key(50) + code(6) + seq(3).
        for element in root.iter():
            if _local(element.tag) == "infEvento":
                code = (element.get("Id") or "")[-9:-3]
                situation = (
                    "substituted"
                    if code == "105102"
                    else "cancelled"
                    if code in {"101101", "101103"}
                    else ""
                )
                break
    values = _index(root)
    return {
        "kind": "event",
        "access_key": _first(values, "chNFSe")[:60],
        "situation": situation or "active",
        "issued_on": _local_date(_first(values, "dhProc", "dhEvento")),
    }


def nfse_facts(
    xml: str, *, company_cnpj: str, fallback: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Facts of one stored document. Unreadable XML falls back to the stored normalization."""

    fallback = fallback if isinstance(fallback, dict) else {}
    try:
        root = ElementTree.fromstring(xml)
    except (ElementTree.ParseError, DefusedXmlException, ValueError, TypeError):
        root = None
    is_event = str(fallback.get("document_type") or "").upper().startswith("EVENTO")
    if root is not None and (is_event or _local(root.tag).casefold() == "evento"):
        return _event_facts(root)
    if is_event:
        return {"kind": "event", "access_key": "", "situation": "active", "issued_on": None}
    values = _index(root) if root is not None else {}

    access_key = ""
    if root is not None:
        for element in root.iter():
            if _local(element.tag) == "infNFSe":
                identifier = element.get("Id") or ""
                access_key = identifier[3:] if identifier.startswith("NFS") else identifier
                break
    access_key = (access_key or _first(values, "chNFSe") or str(fallback.get("access_key") or ""))[
        :60
    ]

    company = re.sub(r"\D", "", company_cnpj or "")
    provider = _party_document(root, _PROVIDER_GROUPS) if root is not None else ""
    recipient = _party_document(root, _RECIPIENT_GROUPS) if root is not None else ""
    counterparty = ""
    counterparty_name = ""
    if company and provider and (provider == company or provider[:8] == company[:8]):
        if recipient != provider:
            counterparty = recipient
            counterparty_name = _party_name(root, _RECIPIENT_GROUPS)
    elif company and recipient and (recipient == company or recipient[:8] == company[:8]):
        counterparty = provider
        counterparty_name = _party_name(root, _PROVIDER_GROUPS)

    issued_on = _local_date(_first(values, "dhProc", "dhEmi")) or _local_date(
        str(fallback.get("issued_at") or "")
    )
    competence = _local_date(_first(values, "dCompet")) or _local_date(
        str(fallback.get("competence") or "")
    )

    service_amount = _money(values, "vServ", "vServPrest", "ValorServicos")
    net_amount = _money(values, "vLiq", "ValorLiquidoNfse")
    if service_amount is None and net_amount is None:
        service_amount = _money({"amount": str(fallback.get("amount") or "")}, "amount")

    iss_retained = ZERO
    if _first(values, "tpRetISSQN") in {"2", "3"}:
        iss_retained = _money(values, "vISSQN") or ZERO
    iss_retained = iss_retained or _money(values, "vISSQNRetido", "vISSRet", "vRetISS") or ZERO

    pis_cofins_kind = _first(values, "tpRetPisCofins", "tpRetPISCofins")
    if pis_cofins_kind == "0":
        crf_retained = ZERO
    elif pis_cofins_kind == "1":
        crf_retained = sum(
            (_money(values, name) or ZERO for name in ("vPis", "vCofins", "vRetCSLL")), ZERO
        )
    else:
        crf_retained = _money(values, "vRetCSLL") or ZERO
        if pis_cofins_kind not in {"3", "4", "5", "6", "7", "8", "9"}:
            # Layouts that still send the retained contributions one by one.
            crf_retained += sum(
                (_money(values, name) or ZERO for name in ("vRetPIS", "vRetCOFINS")), ZERO
            )
    irrf_retained = _money(values, "vRetIRRF") or ZERO
    inss_retained = _money(values, "vRetCP", "vRetINSS") or ZERO
    stored = fallback.get("retentions")
    if not (iss_retained or crf_retained or irrf_retained or inss_retained) and isinstance(
        stored, dict
    ):
        # Layouts the reader does not know keep the retentions normalized at capture.
        def stored_amount(*keys: str) -> Decimal:
            return sum(
                (_money({key: str(stored.get(key) or "")}, key) or ZERO for key in keys), ZERO
            )

        iss_retained = stored_amount("iss")
        crf_retained = stored_amount("pis", "cofins", "csll")
        irrf_retained = stored_amount("irrf")
        inss_retained = stored_amount("inss")

    return {
        "kind": "note",
        "access_key": access_key,
        "replaces_key": _first(values, "chSubstda")[:60],
        "number": (_first(values, "nNFSe") or str(fallback.get("number") or ""))[:40],
        "issued_on": issued_on,
        "competence": competence or issued_on,
        "counterparty_document": display_document(counterparty),
        "counterparty_name": counterparty_name,
        "service_amount": service_amount,
        "net_amount": net_amount,
        "iss_retained": iss_retained,
        "crf_retained": crf_retained,
        "irrf_retained": irrf_retained,
        "inss_retained": inss_retained,
        "retained_total": iss_retained + crf_retained + irrf_retained + inss_retained,
    }


FACT_FIELDS = (
    "kind",
    "access_key",
    "replaces_key",
    "number",
    "issued_on",
    "competence",
    "counterparty_document",
    "service_amount",
    "net_amount",
    "iss_retained",
    "crf_retained",
    "irrf_retained",
    "inss_retained",
    "retained_total",
)


def apply_facts(side: Any, facts: dict[str, Any]) -> None:
    """Copy facts onto a side; the counterparty name is kept when the XML has none."""

    for field in FACT_FIELDS:
        if field in facts:
            setattr(side, field, facts[field])
    if facts.get("counterparty_name") and not side.counterparty_name:
        side.counterparty_name = facts["counterparty_name"]
    if facts.get("kind") == "event":
        side.event_situation = facts.get("situation", "")
    side.facts_version = FACTS_VERSION


def refresh_situations(organization_id: Any, keys: set[str] | None = None) -> int:
    """Mark notes cancelled or substituted by events and later notes of the same office."""

    from apps.hub.models import NfseDocumentSide

    sides = NfseDocumentSide.objects.filter(organization_id=organization_id, kind="note")
    if keys is not None:
        keys = {key for key in keys if key}
        if not keys:
            return 0
        sides = sides.filter(access_key__in=keys)
    events = NfseDocumentSide.objects.filter(
        organization_id=organization_id, kind="event", access_key=OuterRef("access_key")
    )
    replacing = NfseDocumentSide.objects.filter(
        organization_id=organization_id, kind="note", replaces_key=OuterRef("access_key")
    )
    return sides.exclude(access_key="").update(
        situation=Case(
            When(Exists(events.filter(event_situation="cancelled")), then=Value("cancelled")),
            When(
                Q(Exists(events.filter(event_situation="substituted"))) | Q(Exists(replacing)),
                then=Value("substituted"),
            ),
            default=Value("active"),
        )
    )
