"""Geradores de EFD ICMS/IPI e XML fiscal sintéticos.

Servem aos testes e ao `seed_crosscheck` (somente com DEBUG). Tudo é fictício: CNPJ de
exemplo com dígitos verificadores válidos, nomes genéricos. Nada aqui lê ou imita dado de
cliente. Os arquivos saem consistentes (9900 e 9999 corretos, DV da chave válido) e cada
gerador tem uma chave para estragar de propósito o que o teste quer provar.
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from .engine.keys import with_check_digit


def make_cnpj(base8: str = "12345678", branch: str = "0001") -> str:
    """CNPJ numérico com os dois dígitos verificadores corretos."""

    digits = [int(char) for char in base8 + branch]
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        total = sum(d * w for d, w in zip(digits, weights, strict=False))
        rest = total % 11
        digits.append(0 if rest < 2 else 11 - rest)
    return "".join(str(d) for d in digits)


def make_key(
    *,
    cnpj: str,
    number: int,
    model: str = "55",
    series: int = 1,
    uf: str = "35",
    aamm: str = "2609",
    numeric_code: str = "12345678",
) -> str:
    base = f"{uf}{aamm}{cnpj}{model}{series:03d}{number:09d}1{numeric_code}"
    return with_check_digit(base)


# -- EFD ---------------------------------------------------------------------------------
@dataclass
class AnalyticSpec:
    cst: str = "000"
    cfop: str = "1102"
    aliq: str = "18,00"
    vl_opr: str = "100,00"
    vl_bc: str = "100,00"
    vl_icms: str = "18,00"
    vl_bc_st: str = "0,00"
    vl_icms_st: str = "0,00"
    vl_red_bc: str = "0,00"
    vl_ipi: str = "0,00"
    cod_obs: str = ""


@dataclass
class DocSpec:
    reg: str = "C100"
    number: int = 1
    key: str = ""
    ind_oper: str = "0"
    ind_emit: str = "1"
    cod_part: str = "FORN1"
    cod_mod: str = "55"
    cod_sit: str = "00"
    ser: str = "1"
    sub: str = ""
    dt_doc: str = "01092026"
    dt_es: str = "02092026"
    vl_doc: str = "100,00"
    vl_desc: str = "0,00"
    vl_merc: str = "100,00"
    vl_bc_icms: str = "100,00"
    vl_icms: str = "18,00"
    vl_bc_icms_st: str = "0,00"
    vl_icms_st: str = "0,00"
    vl_ipi: str = "0,00"
    vl_serv: str = "100,00"
    chv_ref: str = ""
    analytics: list[AnalyticSpec] = field(default_factory=lambda: [AnalyticSpec()])
    #: Substitui os campos do registro por texto cru (para provar tolerância a lixo).
    raw_override: str = ""


@dataclass
class EfdSpec:
    cnpj: str = field(default_factory=make_cnpj)
    nome: str = "EMPRESA TESTE LTDA"
    uf: str = "SP"
    dt_ini: str = "01092026"
    dt_fin: str = "30092026"
    cod_ver: str = "019"
    cod_fin: str = "0"
    docs: list[DocSpec] = field(default_factory=list)


def _c100(doc: DocSpec) -> str:
    cancelled = doc.cod_sit in {"02", "03", "04", "05"}
    values = [
        doc.ind_oper,
        doc.ind_emit,
        "" if doc.cod_mod == "65" else doc.cod_part,
        doc.cod_mod,
        doc.cod_sit,
        doc.ser,
        str(doc.number),
        doc.key,
    ]
    if cancelled:
        values += [""] * 20
    else:
        values += [
            doc.dt_doc,
            doc.dt_es,
            doc.vl_doc,
            "0",
            doc.vl_desc,
            "",
            doc.vl_merc,
            "9",
            "",
            "",
            "",
            doc.vl_bc_icms,
            doc.vl_icms,
            doc.vl_bc_icms_st,
            doc.vl_icms_st,
            doc.vl_ipi,
            "0,00",
            "0,00",
            "",
            "",
        ]
    return "|C100|" + "|".join(values) + "|"


def _d100(doc: DocSpec) -> str:
    values = [
        doc.ind_oper,
        doc.ind_emit,
        doc.cod_part,
        doc.cod_mod,
        doc.cod_sit,
        doc.ser,
        doc.sub,
        str(doc.number),
        doc.key,
        doc.dt_doc,
        doc.dt_es,
        "0",
        doc.chv_ref,
        doc.vl_doc,
        doc.vl_desc,
        "0",
        doc.vl_serv,
        doc.vl_bc_icms,
        doc.vl_icms,
        "0,00",
        "",
        "",
        "3550308",
        "3304557",
    ]
    return "|D100|" + "|".join(values) + "|"


def _analytic(reg: str, item: AnalyticSpec) -> str:
    if reg == "C190":
        values = [
            item.cst,
            item.cfop,
            item.aliq,
            item.vl_opr,
            item.vl_bc,
            item.vl_icms,
            item.vl_bc_st,
            item.vl_icms_st,
            item.vl_red_bc,
            item.vl_ipi,
            item.cod_obs,
        ]
    else:
        values = [
            item.cst,
            item.cfop,
            item.aliq,
            item.vl_opr,
            item.vl_bc,
            item.vl_icms,
            item.vl_red_bc,
            item.cod_obs,
        ]
    return f"|{reg}|" + "|".join(values) + "|"


def build_efd(
    spec: EfdSpec,
    *,
    eol: str = "\r\n",
    encoding: str = "latin-1",
    omit_trailer: bool = False,
    wrong_total: int | None = None,
    wrong_count: tuple[str, int] | None = None,
    extra_lines: tuple[str, ...] = (),
) -> bytes:
    """EFD consistente (9900/9999 corretos) com ganchos para estragar um ponto."""

    header = (
        f"|0000|{spec.cod_ver}|{spec.cod_fin}|{spec.dt_ini}|{spec.dt_fin}|{spec.nome}|"
        f"{spec.cnpj}||{spec.uf}|111222333444|3550308|||A|1|"
    )
    block0 = [header, "|0001|0|"]
    participants = list(dict.fromkeys(doc.cod_part for doc in spec.docs if doc.cod_part))
    for code in participants:
        block0.append(
            f"|0150|{code}|PARTICIPANTE {code}|1058|98765432000198||111|3550308||RUA X|1||CENTRO|"
        )
    block0.append(f"|0990|{len(block0) + 1}|")

    block_c = ["|C001|0|"]
    block_d = ["|D001|0|"]
    for doc in spec.docs:
        if doc.raw_override:
            (block_c if doc.reg == "C100" else block_d).append(doc.raw_override)
        elif doc.reg == "C100":
            block_c.append(_c100(doc))
        else:
            block_d.append(_d100(doc))
        if doc.cod_sit in {"02", "03", "04", "05"}:
            continue
        target = block_c if doc.reg == "C100" else block_d
        analytic_reg = "C190" if doc.reg == "C100" else "D190"
        target.extend(_analytic(analytic_reg, item) for item in doc.analytics)
    block_c.extend(extra_lines)
    block_c.append(f"|C990|{len(block_c) + 1}|")
    block_d.append(f"|D990|{len(block_d) + 1}|")
    block_e = ["|E001|1|", "|E990|2|"]

    body = block0 + block_c + block_d + block_e + ["|9001|0|"]
    if omit_trailer:
        return (eol.join(body) + eol).encode(encoding)

    counts = Counter(line[1:5] for line in body)
    registers = sorted({*counts, "9900", "9990", "9999"})
    counts["9900"] = len(registers)
    counts["9990"] = 1
    counts["9999"] = 1
    declared = [f"|9900|{reg}|{counts[reg]}|" for reg in registers]
    if wrong_count is not None:
        declared = [
            f"|9900|{reg}|{wrong_count[1]}|" if reg == wrong_count[0] else line
            for reg, line in zip(registers, declared, strict=True)
        ]
    block9 = ["|9001|0|"]
    lines = body[:-1] + block9 + declared
    lines.append(f"|9990|{1 + len(declared) + 2}|")
    total = wrong_total if wrong_total is not None else len(lines) + 1
    lines.append(f"|9999|{total}|")
    return (eol.join(lines) + eol).encode(encoding)


# -- XML ---------------------------------------------------------------------------------
NFE_NS = "http://www.portalfiscal.inf.br/nfe"
CTE_NS = "http://www.portalfiscal.inf.br/cte"


@dataclass
class ItemSpec:
    cfop: str = "5102"
    group: str = "ICMS00"
    v_prod: str = "100.00"
    v_bc: str = "100.00"
    p_icms: str = "18.0000"
    v_icms: str = "18.00"
    v_cred_sn: str = ""
    v_icms_op: str = ""
    p_dif: str = ""
    v_icms_dif: str = ""


@dataclass
class NfeSpec:
    key: str
    emit_cnpj: str
    dest_cnpj: str
    number: int = 1
    model: str = "55"
    emit_uf: str = "SP"
    dest_uf: str = "SP"
    tp_nf: str = "1"
    fin_nfe: str = "1"
    items: list[ItemSpec] = field(default_factory=lambda: [ItemSpec()])
    v_nf: str = "100.00"
    v_icms: str = "18.00"
    v_ipi: str = "0.00"
    v_ipi_devol: str = "0.00"
    c_stat: str = "100"
    protocol: bool = True
    wrapper: bool = True
    namespace: bool = True
    tp_amb: str = "1"
    doctype: str = ""


def _item_xml(index: int, item: ItemSpec) -> str:
    if item.group == "ICMS51":
        icms = (
            f"<ICMS51><orig>0</orig><CST>51</CST><modBC>3</modBC><vBC>{item.v_bc}</vBC>"
            f"<pICMS>{item.p_icms}</pICMS><vICMSOp>{item.v_icms_op}</vICMSOp>"
            f"<pDif>{item.p_dif}</pDif><vICMSDif>{item.v_icms_dif}</vICMSDif>"
            f"<vICMS>{item.v_icms}</vICMS></ICMS51>"
        )
    elif item.group.startswith("ICMSSN"):
        credit = (
            f"<pCredSN>2.0000</pCredSN><vCredICMSSN>{item.v_cred_sn}</vCredICMSSN>"
            if item.v_cred_sn
            else ""
        )
        icms = (
            f"<{item.group}><orig>0</orig><CSOSN>{item.group[-3:]}</CSOSN>{credit}</{item.group}>"
        )
    else:
        icms = (
            f"<{item.group}><orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>{item.v_bc}</vBC>"
            f"<pICMS>{item.p_icms}</pICMS><vICMS>{item.v_icms}</vICMS></{item.group}>"
        )
    return (
        f'<det nItem="{index}"><prod><cProd>P{index}</cProd><xProd>Produto {index}</xProd>'
        f"<NCM>01012100</NCM><CFOP>{item.cfop}</CFOP><vProd>{item.v_prod}</vProd></prod>"
        f"<imposto><ICMS>{icms}</ICMS></imposto></det>"
    )


def build_nfe_xml(spec: NfeSpec) -> bytes:
    namespace = f' xmlns="{NFE_NS}"' if spec.namespace else ""
    items = "".join(_item_xml(i, item) for i, item in enumerate(spec.items, start=1))
    inner = (
        f'<infNFe Id="NFe{spec.key}" versao="4.00">'
        f"<ide><mod>{spec.model}</mod><serie>1</serie><nNF>{spec.number}</nNF>"
        f"<dhEmi>2026-09-01T10:00:00-03:00</dhEmi><tpNF>{spec.tp_nf}</tpNF>"
        f"<tpAmb>{spec.tp_amb}</tpAmb><finNFe>{spec.fin_nfe}</finNFe></ide>"
        f"<emit><CNPJ>{spec.emit_cnpj}</CNPJ><xNome>EMITENTE TESTE</xNome>"
        f"<enderEmit><UF>{spec.emit_uf}</UF></enderEmit></emit>"
        f"<dest><CNPJ>{spec.dest_cnpj}</CNPJ><xNome>DESTINATARIO TESTE</xNome>"
        f"<enderDest><UF>{spec.dest_uf}</UF></enderDest></dest>"
        f"{items}"
        f"<total><ICMSTot><vBC>100.00</vBC><vICMS>{spec.v_icms}</vICMS><vProd>100.00</vProd>"
        f"<vIPI>{spec.v_ipi}</vIPI><vIPIDevol>{spec.v_ipi_devol}</vIPIDevol>"
        f"<vNF>{spec.v_nf}</vNF></ICMSTot></total></infNFe>"
    )
    nfe = f"<NFe{namespace}>{inner}</NFe>"
    if not spec.wrapper:
        body = nfe
    else:
        protocol = (
            f"<protNFe versao='4.00'><infProt><tpAmb>1</tpAmb><chNFe>{spec.key}</chNFe>"
            f"<cStat>{spec.c_stat}</cStat><nProt>135260000000001</nProt></infProt></protNFe>"
            if spec.protocol
            else ""
        )
        body = f'<nfeProc{namespace} versao="4.00">{nfe}{protocol}</nfeProc>'
    return f'<?xml version="1.0" encoding="UTF-8"?>{spec.doctype}{body}'.encode()


@dataclass
class CteSpec:
    key: str
    emit_cnpj: str
    tomador_cnpj: str
    number: int = 1
    emit_uf: str = "SP"
    v_tprest: str = "100.00"
    v_icms: str = "12.00"
    v_bc: str = "100.00"
    c_stat: str = "100"


def build_cte_xml(spec: CteSpec) -> bytes:
    inner = (
        f'<infCte Id="CTe{spec.key}" versao="4.00"><ide><mod>57</mod><serie>1</serie>'
        f"<nCT>{spec.number}</nCT><dhEmi>2026-09-01T10:00:00-03:00</dhEmi><tpAmb>1</tpAmb>"
        "<toma3><toma>3</toma></toma3></ide>"
        f"<emit><CNPJ>{spec.emit_cnpj}</CNPJ><xNome>TRANSPORTADORA TESTE</xNome>"
        f"<enderEmit><UF>{spec.emit_uf}</UF></enderEmit></emit>"
        f"<dest><CNPJ>{spec.tomador_cnpj}</CNPJ><xNome>TOMADOR TESTE</xNome></dest>"
        f"<vPrest><vTPrest>{spec.v_tprest}</vTPrest><vRec>{spec.v_tprest}</vRec></vPrest>"
        f"<imp><ICMS><ICMS00><CST>00</CST><vBC>{spec.v_bc}</vBC><pICMS>12.00</pICMS>"
        f"<vICMS>{spec.v_icms}</vICMS></ICMS00></ICMS></imp></infCte>"
    )
    protocol = (
        f"<protCTe versao='4.00'><infProt><tpAmb>1</tpAmb><chCTe>{spec.key}</chCTe>"
        f"<cStat>{spec.c_stat}</cStat></infProt></protCTe>"
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><cteProc xmlns="{CTE_NS}" versao="4.00">'
        f"<CTe>{inner}</CTe>{protocol}</cteProc>"
    ).encode()


def build_cancel_event_xml(key: str, *, c_stat: str = "135") -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<procEventoNFe xmlns="{NFE_NS}" versao="1.00"><evento versao="1.00"><infEvento>'
        f"<chNFe>{key}</chNFe><tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento></infEvento></evento>"
        f"<retEvento versao='1.00'><infEvento><cStat>{c_stat}</cStat><chNFe>{key}</chNFe>"
        "</infEvento></retEvento></procEventoNFe>"
    ).encode()


def build_zip(files: dict[str, bytes], *, compress: bool = True) -> bytes:
    buffer = io.BytesIO()
    method = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(buffer, "w", method) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()
