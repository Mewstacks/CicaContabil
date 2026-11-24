"""Leitura de XML fiscal (NF-e, NFC-e, CT-e e eventos) com parser endurecido.

O arquivo é dado de terceiros: recusa DOCTYPE e ENTITY (bomba de entidades, XXE), byte nulo
e documento acima do teto, e valida a chave de acesso com o dígito verificador. A navegação
ignora o namespace e compara só o nome local das tags, porque XML de NF-e circula com e sem
`xmlns` (o legado tinha três caminhos de busca para isso).

Valores saem em centavos e alíquotas com quatro casas, como no resto do motor. O XML nunca
fica inteiro em memória depois de lido: o chamador guarda só o resumo que a comparação usa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from defusedxml import DefusedXmlException, ElementTree  # type: ignore[import-untyped]

from .keys import is_valid_key, is_well_formed
from .money import MoneyError, xml_cents, xml_rate

MAX_XML_BYTES = 2 * 1024 * 1024

_FORBIDDEN = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)", re.IGNORECASE)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

#: cStat de protocolo: autorizada, autorizada fora do prazo / denegada / cancelamento.
AUTHORIZED_STATUS = frozenset({"100", "150"})
DENIED_STATUS = frozenset({"110", "301", "302", "303"})
CANCELLED_STATUS = frozenset({"101", "151"})
#: cStat de evento registrado (135 e 136) ou cancelamento fora do prazo (155).
EVENT_REGISTERED = frozenset({"135", "136", "155"})
CANCEL_EVENT = "110111"

_NFE_TOTALS = {
    "vBC": "vbc",
    "vICMS": "vicms",
    "vICMSDeson": "vicms_deson",
    "vFCP": "vfcp",
    "vBCST": "vbcst",
    "vST": "vst",
    "vFCPST": "vfcpst",
    "vProd": "vprod",
    "vFrete": "vfrete",
    "vSeg": "vseg",
    "vDesc": "vdesc",
    "vII": "vii",
    "vIPI": "vipi",
    "vIPIDevol": "vipi_devol",
    "vPIS": "vpis",
    "vCOFINS": "vcofins",
    "vOutro": "voutro",
    "vNF": "vnf",
}


class FiscalXmlError(ValueError):
    """XML recusado; `code` identifica o motivo e `message` é seguro para a tela."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class Icms51Item:
    item: int
    cfop: str
    v_bc: int | None
    p_icms: int | None
    v_icms_op: int | None
    p_dif: int | None
    v_icms_dif: int | None
    v_icms: int | None

    @property
    def arithmetic_ok(self) -> bool:
        """vICMSOp - vICMSDif = vICMS (regra de validação da SEFAZ, rejeição 353)."""

        if self.v_icms_op is None and self.v_icms_dif is None:
            return True
        return (self.v_icms_op or 0) - (self.v_icms_dif or 0) == (self.v_icms or 0)


@dataclass(frozen=True, slots=True)
class ParsedNfe:
    key: str
    model: str
    series: str
    number: str
    issued: str
    tp_nf: str
    fin_nfe: str
    emit_doc: str
    emit_uf: str
    emit_name: str
    dest_doc: str
    dest_uf: str
    dest_name: str
    #: cStat do protocolo ("" quando o XML veio sem `protNFe`).
    c_stat: str
    totals: dict[str, int | None]
    #: Soma de vCredICMSSN dos itens (crédito do Simples Nacional).
    cred_sn: int
    #: ICMS dos itens agrupado pelo CFOP do item (CFOP do emitente).
    icms_by_cfop: dict[str, int]
    icms51: tuple[Icms51Item, ...]
    item_count: int
    kind: Literal["nfe"] = "nfe"


@dataclass(frozen=True, slots=True)
class ParsedCte:
    key: str
    model: str
    series: str
    number: str
    issued: str
    emit_doc: str
    emit_uf: str
    emit_name: str
    #: Documentos (CNPJ/CPF) das demais partes: remetente, expedidor, recebedor,
    #: destinatário e tomador.
    party_docs: tuple[str, ...]
    c_stat: str
    v_tprest: int | None
    v_rec: int | None
    v_bc: int | None
    v_icms: int | None
    kind: Literal["cte"] = "cte"


@dataclass(frozen=True, slots=True)
class ParsedEvent:
    key: str
    tp_evento: str
    c_stat: str
    cancels: bool
    kind: Literal["event"] = "event"


@dataclass(frozen=True, slots=True)
class Ignored:
    reason: str
    detail: str = ""
    kind: Literal["ignored"] = "ignored"


ParsedXml = ParsedNfe | ParsedCte | ParsedEvent | Ignored


# -- navegação sem namespace -------------------------------------------------------------
def _local(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _child(node: Any, name: str) -> Any | None:
    if node is None:
        return None
    for child in node:
        if _local(child.tag) == name:
            return child
    return None


def _children(node: Any, name: str) -> list[Any]:
    if node is None:
        return []
    return [child for child in node if _local(child.tag) == name]


def _find(node: Any, *path: str) -> Any | None:
    for name in path:
        node = _child(node, name)
        if node is None:
            return None
    return node


def _text(node: Any, *path: str) -> str:
    found = _find(node, *path)
    return (found.text or "").strip() if found is not None else ""


def _cents(node: Any, *path: str) -> int | None:
    try:
        return xml_cents(_text(node, *path))
    except MoneyError as exc:
        raise FiscalXmlError("valor_invalido", f"Valor inválido em {'/'.join(path)}.") from exc


def _rate(node: Any, *path: str) -> int | None:
    try:
        return xml_rate(_text(node, *path))
    except MoneyError as exc:
        raise FiscalXmlError("valor_invalido", f"Alíquota inválida em {'/'.join(path)}.") from exc


def _party_doc(node: Any) -> str:
    return (_text(node, "CNPJ") or _text(node, "CPF") or _text(node, "idEstrangeiro")).upper()


def _issued(node: Any) -> str:
    raw = _text(node, "dhEmi") or _text(node, "dEmi")
    return raw[:10] if _ISO_DATE.fullmatch(raw[:10]) else ""


def parse_root(content: bytes) -> Any:
    """Lê o XML recusando DTD, entidade, byte nulo e tamanho acima do teto."""

    if len(content) > MAX_XML_BYTES:
        raise FiscalXmlError("grande_demais", "O XML passa do tamanho máximo aceito.")
    if b"\x00" in content:
        raise FiscalXmlError("nul", "O XML contém byte nulo.")
    if _FORBIDDEN.search(content):
        raise FiscalXmlError("dtd_proibido", "O XML declara DTD ou entidade, o que não é aceito.")
    try:
        return ElementTree.fromstring(content, forbid_dtd=True, forbid_entities=True)
    except (ElementTree.ParseError, DefusedXmlException, ValueError, TypeError) as exc:
        raise FiscalXmlError("xml_invalido", "O arquivo não é um XML válido.") from exc


def _access_key(inf: Any, prefix: str) -> str:
    raw = (inf.attrib.get("Id") or "").strip().upper()
    key = raw.removeprefix(prefix.upper())
    if not is_well_formed(key):
        raise FiscalXmlError("chave_invalida", "A chave de acesso do XML não tem 44 posições.")
    if not is_valid_key(key):
        raise FiscalXmlError("chave_dv_invalida", "O dígito verificador da chave está errado.")
    return key


# -- NF-e / NFC-e ------------------------------------------------------------------------
def _parse_nfe(root: Any) -> ParsedNfe | Ignored:
    nfe = root if _local(root.tag) == "NFe" else _child(root, "NFe")
    inf = _child(nfe, "infNFe")
    if inf is None:
        raise FiscalXmlError("sem_infnfe", "O XML não tem o grupo infNFe.")
    ide = _child(inf, "ide")
    if _text(ide, "tpAmb") == "2":
        return Ignored("homologacao", "NF-e emitida em ambiente de homologação")
    key = _access_key(inf, "NFe")

    totals_node = _find(inf, "total", "ICMSTot")
    if totals_node is None:
        raise FiscalXmlError("sem_icmstot", "A NF-e não tem o grupo de totais ICMSTot.")
    totals: dict[str, int | None] = {
        target: _cents(totals_node, source) for source, target in _NFE_TOTALS.items()
    }

    cred_sn = 0
    by_cfop: dict[str, int] = {}
    icms51: list[Icms51Item] = []
    details = _children(inf, "det")
    for position, det in enumerate(details, start=1):
        cfop = _text(det, "prod", "CFOP")
        icms = _find(det, "imposto", "ICMS")
        group = next(iter(icms), None) if icms is not None else None
        if group is None:
            continue
        cred_sn += _cents(group, "vCredICMSSN") or 0
        by_cfop[cfop] = by_cfop.get(cfop, 0) + (_cents(group, "vICMS") or 0)
        if _local(group.tag) == "ICMS51":
            try:
                item_number = int(det.attrib.get("nItem") or position)
            except ValueError:
                item_number = position
            icms51.append(
                Icms51Item(
                    item=item_number,
                    cfop=cfop,
                    v_bc=_cents(group, "vBC"),
                    p_icms=_rate(group, "pICMS"),
                    v_icms_op=_cents(group, "vICMSOp"),
                    p_dif=_rate(group, "pDif"),
                    v_icms_dif=_cents(group, "vICMSDif"),
                    v_icms=_cents(group, "vICMS"),
                )
            )

    protocol = _find(root, "protNFe", "infProt") if _local(root.tag) != "NFe" else None
    emit = _child(inf, "emit")
    dest = _child(inf, "dest")
    return ParsedNfe(
        key=key,
        model=_text(ide, "mod"),
        series=_text(ide, "serie"),
        number=_text(ide, "nNF"),
        issued=_issued(ide),
        tp_nf=_text(ide, "tpNF"),
        fin_nfe=_text(ide, "finNFe"),
        emit_doc=_party_doc(emit),
        emit_uf=_text(emit, "enderEmit", "UF").upper(),
        emit_name=_text(emit, "xNome"),
        dest_doc=_party_doc(dest),
        dest_uf=_text(dest, "enderDest", "UF").upper(),
        dest_name=_text(dest, "xNome"),
        c_stat=_text(protocol, "cStat"),
        totals=totals,
        cred_sn=cred_sn,
        icms_by_cfop=by_cfop,
        icms51=tuple(icms51),
        item_count=len(details),
    )


# -- CT-e / CT-e OS ----------------------------------------------------------------------
def _parse_cte(root: Any) -> ParsedCte | Ignored:
    cte = root
    if _local(root.tag) not in {"CTe", "CTeOS"}:
        # `or` entre elementos erraria: um Element sem filhos conta como falso.
        cte = _child(root, "CTe")
        if cte is None:
            cte = _child(root, "CTeOS")
    inf = _child(cte, "infCte")
    if inf is None:
        raise FiscalXmlError("sem_infcte", "O XML não tem o grupo infCte.")
    ide = _child(inf, "ide")
    if _text(ide, "tpAmb") == "2":
        return Ignored("homologacao", "CT-e emitido em ambiente de homologação")
    key = _access_key(inf, "CTe")

    parties: list[str] = []
    for name in ("rem", "exped", "receb", "dest", "toma"):
        doc = _party_doc(_child(inf, name))
        if doc:
            parties.append(doc)
    toma4 = _party_doc(_find(ide, "toma4"))
    if toma4:
        parties.append(toma4)
    toma3 = _text(ide, "toma3", "toma")
    referenced = {"0": "rem", "1": "exped", "2": "receb", "3": "dest"}.get(toma3)
    if referenced:
        doc = _party_doc(_child(inf, referenced))
        if doc:
            parties.append(doc)

    icms = _find(inf, "imp", "ICMS")
    group = next(iter(icms), None) if icms is not None else None
    protocol = (
        _find(root, "protCTe", "infProt") if _local(root.tag) not in {"CTe", "CTeOS"} else None
    )
    emit = _child(inf, "emit")
    return ParsedCte(
        key=key,
        model=_text(ide, "mod"),
        series=_text(ide, "serie"),
        number=_text(ide, "nCT"),
        issued=_issued(ide),
        emit_doc=_party_doc(emit),
        emit_uf=_text(emit, "enderEmit", "UF").upper(),
        emit_name=_text(emit, "xNome"),
        party_docs=tuple(dict.fromkeys(parties)),
        c_stat=_text(protocol, "cStat"),
        v_tprest=_cents(inf, "vPrest", "vTPrest"),
        v_rec=_cents(inf, "vPrest", "vRec"),
        v_bc=_cents(group, "vBC") if group is not None else None,
        v_icms=_cents(group, "vICMS") if group is not None else None,
    )


# -- eventos -----------------------------------------------------------------------------
def _parse_event(root: Any) -> ParsedEvent:
    if _local(root.tag) in {"procCancNFe"}:
        key = _text(root, "cancNFe", "infCanc", "chNFe") or _text(
            root, "retCancNFe", "infCanc", "chNFe"
        )
        c_stat = _text(root, "retCancNFe", "infCanc", "cStat")
        tp_evento = CANCEL_EVENT
        cancelled = c_stat in CANCELLED_STATUS | EVENT_REGISTERED
    else:
        event = _child(root, "evento")
        info = _child(event if event is not None else root, "infEvento")
        key = _text(info, "chNFe") or _text(info, "chCTe")
        tp_evento = _text(info, "tpEvento")
        c_stat = _text(root, "retEvento", "infEvento", "cStat")
        cancelled = tp_evento == CANCEL_EVENT and c_stat in EVENT_REGISTERED
    key = key.upper()
    if not is_well_formed(key):
        raise FiscalXmlError("chave_invalida", "A chave do evento não tem 44 posições.")
    return ParsedEvent(key=key, tp_evento=tp_evento, c_stat=c_stat, cancels=cancelled)


_NFE_ROOTS = {"nfeProc", "NFe"}
_CTE_ROOTS = {"cteProc", "CTe", "cteOSProc", "CTeOS"}
_EVENT_ROOTS = {"procEventoNFe", "procEventoCTe", "evento", "eventoCTe", "procCancNFe"}
_SUMMARY_ROOTS = {"resNFe", "resEvento", "resCTe"}


def parse_fiscal_xml(content: bytes) -> ParsedXml:
    """Interpreta um XML fiscal ou explica por que não o usa.

    Levanta `FiscalXmlError` para XML quebrado, inseguro ou com chave inválida; devolve
    `Ignored` para documento legítimo que o Contraprova não confere (resumo, homologação,
    tipo não suportado).
    """

    root = parse_root(content)
    name = _local(root.tag)
    if name in _NFE_ROOTS:
        return _parse_nfe(root)
    if name in _CTE_ROOTS:
        return _parse_cte(root)
    if name in _EVENT_ROOTS:
        return _parse_event(root)
    if name in _SUMMARY_ROOTS:
        return Ignored("resumo", "Resumo da SEFAZ, sem os valores do documento")
    return Ignored("tipo_nao_suportado", f"Documento <{name[:40]}> não conferido")


def company_direction(doc: ParsedNfe | ParsedCte, company_doc: str) -> str:
    """`E` (entrada), `S` (saída) ou `X` (nota de outra empresa), pelo CNPJ da empresa.

    NF-e: o emitente é a empresa → saída, ou entrada própria quando tpNF = 0; o destinatário
    é a empresa → entrada. CT-e: o emitente é a empresa → prestação (saída); a empresa em
    qualquer outra parte (tomador, remetente…) → aquisição (entrada).
    """

    company = company_doc.upper()
    if isinstance(doc, ParsedNfe):
        if doc.emit_doc == company:
            return "E" if doc.tp_nf == "0" else "S"
        if doc.dest_doc == company:
            return "E"
        return "X"
    if doc.emit_doc == company:
        return "S"
    if company in doc.party_docs:
        return "E"
    return "X"


def counterpart_uf(doc: ParsedNfe | ParsedCte, direction: str) -> str:
    """UF da contraparte: destinatário na saída, emitente na entrada (regra 8 de D-301)."""

    if isinstance(doc, ParsedCte):
        return doc.emit_uf if direction == "E" else ""
    return doc.dest_uf if direction == "S" else doc.emit_uf


def status_group(c_stat: str) -> str:
    """`autorizada`, `denegada`, `cancelada` ou `sem_protocolo`."""

    if not c_stat:
        return "sem_protocolo"
    if c_stat in AUTHORIZED_STATUS:
        return "autorizada"
    if c_stat in DENIED_STATUS:
        return "denegada"
    if c_stat in CANCELLED_STATUS:
        return "cancelada"
    return "outro"
