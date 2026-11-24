"""Orquestra uma conferência: lê os arquivos para o preparo e chama o comparador da ferramenta.

Não conhece Django nem banco do CICA: recebe caminhos de arquivos locais e um `Sink`. A
camada de cima (serviço do módulo) baixa os arquivos, cria o diretório temporário, passa o
sink que grava achados e relatório, e traduz `RunRejected` em mensagem para a tela.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .compare_icms51 import compare_icms51
from .compare_sped_sped import compare_sped_sped
from .compare_sped_xml import compare_sped_xml
from .compare_uf import compare_uf_dominio
from .dominio_file import DominioFileError, DominioReport, DominioRow, iter_dominio_rows
from .efd import EfdFormatError, EfdHeader, EfdReader
from .findings import RunCancelled, Sink
from .fiscal_xml import (
    MAX_XML_BYTES,
    FiscalXmlError,
    Ignored,
    ParsedCte,
    ParsedEvent,
    ParsedNfe,
    company_direction,
    parse_fiscal_xml,
)
from .keys import format_cnpj
from .rules import RuleSet
from .stage import Stage
from .tools import ICMS51, SPED_SPED, SPED_XML, TOOLS, UF_DOMINIO
from .zipreader import ZipLimits, ZipRejected, iter_zip_items

MAX_XML_DOCUMENTS = 10_000
_PROGRESS_EVERY = 200
_SPED_PROGRESS_EVERY = 20_000
_ZIP_MAGIC = b"PK\x03\x04"

_SKIP_MESSAGES = {
    "nao_xml": "arquivo que não é XML dentro do ZIP",
    "grande_demais": "XML acima do tamanho máximo",
    "razao_suspeita": "XML com compressão suspeita",
    "criptografado": "XML protegido por senha dentro do ZIP",
    "corrompido": "XML corrompido dentro do ZIP",
}

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Problem:
    severity: Severity
    code: str
    message: str
    file: str = ""


class RunRejected(Exception):
    """A conferência não pode rodar; `problems` explica o que corrigir."""

    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(item.message for item in problems[:3]))
        self.problems = problems


@dataclass(frozen=True)
class InputFile:
    role: str
    path: Path
    name: str


@dataclass
class FileReport:
    role: str
    name: str
    kind: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunOutcome:
    tool: str
    counts: dict[str, int]
    files: list[FileReport]
    warnings: list[Problem]
    rules: dict[str, Any]
    ingest: dict[str, int]


Comparator = Callable[[Stage, RuleSet, Sink], Counter[str]]
COMPARATORS: dict[str, Comparator] = {
    SPED_XML: compare_sped_xml,
    SPED_SPED: compare_sped_sped,
    ICMS51: compare_icms51,
    UF_DOMINIO: compare_uf_dominio,
}


def _check(sink: Sink) -> None:
    if sink.cancelled():
        raise RunCancelled


def _cnpj_root(doc: str) -> str:
    return doc[:8]


def _check_company(
    header: EfdHeader, name: str, company_doc: str, competence: str, warnings: list[Problem]
) -> list[Problem]:
    errors: list[Problem] = []
    if company_doc:
        if header.cnpj == company_doc:
            pass
        elif _cnpj_root(header.cnpj) == _cnpj_root(company_doc):
            warnings.append(
                Problem(
                    "warning",
                    "outro_estabelecimento",
                    "O SPED é de outro estabelecimento da mesma empresa "
                    f"(CNPJ {format_cnpj(header.cnpj)}); a conferência segue com ele.",
                    name,
                )
            )
        else:
            errors.append(
                Problem(
                    "error",
                    "empresa_diferente",
                    f"O SPED é do CNPJ {format_cnpj(header.cnpj)}, "
                    "que não é o da empresa escolhida.",
                    name,
                )
            )
    if competence and header.competence != competence:
        warnings.append(
            Problem(
                "warning",
                "competencia_diferente",
                f"O SPED é da competência {header.dt_ini.month:02d}/{header.dt_ini.year}, "
                "diferente da escolhida.",
                name,
            )
        )
    return errors


def _ingest_sped(
    stage: Stage,
    item: InputFile,
    side: int,
    company_doc: str,
    competence: str,
    sink: Sink,
    warnings: list[Problem],
) -> tuple[FileReport, list[Problem], EfdHeader | None]:
    errors: list[Problem] = []
    with item.path.open("rb") as handle:
        reader = EfdReader(handle)
        try:
            for position, doc in enumerate(reader.documents(), start=1):
                stage.add_sped_document(side, doc)
                if position % _SPED_PROGRESS_EVERY == 0:
                    _check(sink)
                    sink.progress("Lendo SPED", position, None)
        except EfdFormatError as exc:
            errors.append(Problem("error", exc.code, exc.message, item.name))
            return FileReport(item.role, item.name, "efd"), errors, None
    summary = reader.summary()
    for issue in summary.issues:
        problem = Problem(issue.severity, issue.code, issue.message, item.name)
        (errors if issue.severity == "error" else warnings).append(problem)
    header = summary.header
    if header is not None:
        errors.extend(_check_company(header, item.name, company_doc, competence, warnings))
    details: dict[str, Any] = {
        "linhas": summary.physical_lines,
        "codificacao": summary.encoding,
        "fim_de_linha": summary.line_ending,
        "c100": summary.counts.get("C100", 0),
        "d100": summary.counts.get("D100", 0),
        "c190": summary.counts.get("C190", 0),
        "d190": summary.counts.get("D190", 0),
        "avisos_omitidos": summary.issue_overflow,
    }
    if header is not None:
        details.update(
            cnpj=header.cnpj,
            nome=header.nome,
            uf=header.uf,
            competencia=header.competence,
            periodo=[header.dt_ini.isoformat(), header.dt_fin.isoformat()],
            cod_ver=header.cod_ver,
            finalidade="substituto" if header.cod_fin == "1" else "original",
        )
    return FileReport(item.role, item.name, "efd", details), errors, header


def _xml_items(item: InputFile) -> Iterable[tuple[str, bytes | None, str]]:
    """(nome, conteúdo, motivo) de cada XML do arquivo, seja ele ZIP ou XML solto."""

    with item.path.open("rb") as handle:
        head = handle.read(4)
        handle.seek(0)
        if head == _ZIP_MAGIC or item.name.lower().endswith(".zip"):
            try:
                for entry in iter_zip_items(handle, ZipLimits()):
                    yield entry.name, entry.data, entry.problem
            except ZipRejected as exc:
                yield item.name, None, f"zip:{exc.code}:{exc}"
            return
        data = handle.read(MAX_XML_BYTES + 1)
    yield item.name, data, ""


def _ingest_xml(
    stage: Stage,
    item: InputFile,
    direction_doc: str,
    sink: Sink,
    totals: Counter[str],
) -> FileReport:
    before = Counter(totals)
    for name, data, problem in _xml_items(item):
        if problem.startswith("zip:"):
            _, code, message = problem.split(":", 2)
            raise RunRejected([Problem("error", f"zip_{code}", message, item.name)])
        if problem == "nao_xml":
            totals["nao_xml"] += 1
            stage.add_skip(name, problem, _SKIP_MESSAGES[problem])
            continue
        totals["arquivos"] += 1
        if totals["arquivos"] > MAX_XML_DOCUMENTS:
            raise RunRejected(
                [
                    Problem(
                        "error",
                        "xml_demais",
                        f"A conferência aceita até {MAX_XML_DOCUMENTS} XML; divida o lote.",
                        item.name,
                    )
                ]
            )
        if totals["arquivos"] % _PROGRESS_EVERY == 0:
            _check(sink)
            sink.progress("Lendo XML", totals["arquivos"], None)
        if data is None:
            totals["recusados"] += 1
            stage.add_skip(name, problem, _SKIP_MESSAGES.get(problem, problem))
            continue
        try:
            parsed = parse_fiscal_xml(data)
        except FiscalXmlError as exc:
            totals["invalidos"] += 1
            stage.add_skip(name, exc.code, exc.message)
            continue
        if isinstance(parsed, Ignored):
            totals["ignorados"] += 1
            stage.add_skip(name, parsed.reason, parsed.detail)
        elif isinstance(parsed, ParsedEvent):
            totals["eventos"] += 1
            stage.add_event(parsed, name)
        elif isinstance(parsed, (ParsedNfe, ParsedCte)):
            direction = company_direction(parsed, direction_doc)
            if direction == "X":
                totals["outra_empresa"] += 1
                stage.add_skip(name, "outra_empresa", "XML que não é da empresa da conferência")
                continue
            if stage.add_xml(parsed, source=name, direction=direction):
                totals["nfe" if isinstance(parsed, ParsedNfe) else "cte"] += 1
            else:
                totals["duplicados"] += 1
                stage.add_skip(name, "duplicado", "Chave de acesso repetida; vale o primeiro XML")
    gained = {key: totals[key] - before[key] for key in totals if totals[key] != before[key]}
    return FileReport(item.role, item.name, "xml", gained)


def _ingest_dominio(
    stage: Stage,
    item: InputFile | None,
    rows: Iterable[DominioRow] | None,
    sink: Sink,
    warnings: list[Problem],
) -> FileReport | None:
    report = DominioReport()
    if rows is None:
        if item is None:
            return None
        try:
            with item.path.open("rb") as handle:
                for loaded, row in enumerate(iter_dominio_rows(handle, item.name, report), start=1):
                    stage.add_dominio(row.key, row.direcao, row.uf)
                    if loaded % 20_000 == 0:
                        _check(sink)
        except DominioFileError as exc:
            raise RunRejected([Problem("error", "dominio_invalido", str(exc), item.name)]) from exc
        name, kind = item.name, "dominio"
        role = item.role
    else:
        loaded = 0
        for row in rows:
            stage.add_dominio(row.key, row.direcao, row.uf)
            loaded += 1
            if loaded % 20_000 == 0:
                _check(sink)
        report.rows_read = report.rows_valid = loaded
        name, kind, role = "Agente do Domínio", "agente", "dominio"
    warnings.extend(Problem("warning", "dominio_linha", text, name) for text in report.issues)
    if report.issue_overflow:
        warnings.append(
            Problem(
                "warning", "dominio_linhas", f"Mais {report.issue_overflow} linhas ignoradas.", name
            )
        )
    if report.rows_valid == 0:
        raise RunRejected(
            [Problem("error", "dominio_vazio", "O Domínio não trouxe nenhuma linha válida.", name)]
        )
    return FileReport(role, name, kind, {"linhas": report.rows_read, "validas": report.rows_valid})


def run_tool(
    tool: str,
    *,
    company_doc: str,
    competence: str,
    rules: RuleSet,
    inputs: list[InputFile],
    workdir: Path,
    sink: Sink,
    dominio_rows: Iterable[DominioRow] | None = None,
) -> RunOutcome:
    definition = TOOLS[tool]
    company_doc = company_doc.strip().upper()
    files: list[FileReport] = []
    warnings: list[Problem] = []
    errors: list[Problem] = []
    totals: Counter[str] = Counter()
    sped_headers: list[EfdHeader] = []

    with Stage(workdir) as stage:
        sink.progress("Preparando", 0, None)
        for item in inputs:
            role = definition.role(item.role)
            if role.kind != "efd":
                continue
            side = 2 if item.role == "sped2" else 1
            report, problems, header = _ingest_sped(
                stage, item, side, company_doc, competence, sink, warnings
            )
            files.append(report)
            errors.extend(problems)
            if header is not None:
                sped_headers.append(header)
        if errors:
            raise RunRejected(errors)

        direction_doc = (
            sped_headers[0].cnpj if definition.uses_sped and sped_headers else company_doc
        )
        if not direction_doc:
            raise RunRejected(
                [
                    Problem(
                        "error",
                        "sem_cnpj",
                        "A empresa não tem CNPJ cadastrado e não há SPED para indicar o CNPJ.",
                    )
                ]
            )
        for item in inputs:
            if definition.role(item.role).kind == "xml":
                files.append(_ingest_xml(stage, item, direction_doc, sink, totals))
        usable = totals["nfe"] + totals["cte"]
        if any(definition.role(i.role).kind == "xml" for i in inputs) and usable == 0:
            reasons = stage.skip_reasons()
            raise RunRejected(
                [
                    Problem(
                        "error",
                        "sem_xml_util",
                        "Nenhum XML de NF-e ou CT-e da empresa foi encontrado nos arquivos enviados"
                        + (
                            f" ({', '.join(f'{v} {k}' for k, v in sorted(reasons.items()))})."
                            if reasons
                            else "."
                        ),
                    )
                ]
            )
        if tool == UF_DOMINIO:
            dominio_input = next((i for i in inputs if i.role == "dominio"), None)
            dominio_report = _ingest_dominio(stage, dominio_input, dominio_rows, sink, warnings)
            if dominio_report is None:
                raise RunRejected(
                    [
                        Problem(
                            "error",
                            "sem_dominio",
                            "Falta a UF do Domínio: envie o arquivo ou consulte o agente.",
                        )
                    ]
                )
            files.append(dominio_report)

        stage.finish_loading()
        _check(sink)
        sink.progress("Comparando", 0, None)
        counts = COMPARATORS[tool](stage, rules, sink)
        skip_counts = stage.skip_reasons()

    ingest = dict(totals)
    ingest.update({f"ignorado_{reason}": total for reason, total in skip_counts.items()})
    return RunOutcome(
        tool=tool,
        counts=dict(counts),
        files=files,
        warnings=warnings,
        rules=rules.snapshot(),
        ingest=ingest,
    )
