"""Contas sugeridas para cada parte da simulação — D-420, PC-33 (padrão provisório, a confirmar).

A sugestão repete a prática observada no Razão de setembro/2026 da SURIA (V-477): cada tipo de
parte recebe a conta que a contadora usou para o mesmo tipo de movimento, procurada **pelo nome** no
plano de contas da empresa (descoberta D-373). A conta analítica do cliente ou fornecedor da baixa
é procurada pelo nome da parte. Nada vira lançamento: é evidência para a contadora confirmar (Q-50
e seguintes).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from apps.hub.multisource.common import MultisourceError, normalize_name
from apps.hub.multisource.matching import LineResult, Part, SimulationResult

# Nomes de conta da prática de setembro/2026 (Razão da conta Sicredi da SURIA).
RECEIPT_BANK = "COBRANCA"
PAYMENT_BANK = "PAGAMENTO DE FORNECEDORES"
INTEREST = "JUROS ATIVOS"
INVESTMENT = "APLICACAO SICREDINVEST AUTOMATICO"
INVESTMENT_INCOME = "RECEITA DE APLICACOES FINANCEIRAS"
INVESTMENT_TAX = "IRRF S APLICACAO FINANCEIRA"
LOAN_INTEREST = "JUROS PASSIVOS"
TAB_ACCOUNTS = {"CEF": "CAIXA ECONOMICA FEDERAL", "SICREDI": "BANCO SICREDI"}
# Natureza informada pelo caixa do cliente -> nome (ou início do nome) da conta usada em setembro.
NATURE_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (r"TARIFA|CESTA|CUSTAS|PROTESTO", ("DESPESAS BANCARIAS",), ""),
    (r"FGTS", ("FGTS A RECOLHER",), ""),
    (r"SIMPLES", ("SIMPLES A RECOLHER",), ""),
    (r"ICMS|DIFAL|DIFERENCIAL", ("ICMS DIFERENCIAL S COMPRAS",), ""),
    (r"CONSIGNADO", ("EMPRESTIMOS CONSIGNADOS",), ""),
    (
        r"DISTRIBUI\w* LUCRO|LUCROS",
        ("EMPRESTIMO AO SOCIO*", "EMPRESTIMO A SOCIA*"),
        "em setembro, PIX aos sócios foi lançado como empréstimo aos sócios, meio a meio",
    ),
    (r"SALARIO|FOLHA|ESTAGIAR|PRO ?LABORE", (PAYMENT_BANK,), "prática de setembro para a folha"),
    (r"FATURA|CARTAO", (PAYMENT_BANK,), "prática de setembro para a fatura do cartão"),
)


@dataclass(frozen=True)
class ChartAccount:
    code: int
    classification: str
    name: str

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


@dataclass(frozen=True)
class Suggestion:
    role: str  # "banco" (contrapartida do banco) ou "baixa" (lançamento da baixa do título)
    accounts: tuple[ChartAccount, ...]
    note: str = ""

    def __str__(self) -> str:
        names = " + ".join(str(a) for a in self.accounts) or "sem conta no plano"
        return f"{self.role}: {names}" + (f" ({self.note})" if self.note else "")


def _plain(value: str) -> str:
    # O Domínio acrescenta " - código" ao nome do cliente/fornecedor no plano e nos relatórios.
    return normalize_name(re.sub(r"\s*-\s*\d+\s*$", "", value or ""))


class Chart:
    """Contas analíticas ativas de um plano, para procurar por nome."""

    def __init__(self, rows: Iterable[dict[str, object]]):
        self.accounts: list[ChartAccount] = []
        groups: dict[str, str] = {}
        for row in rows:
            name = str(row.get("account_name_raw") or "").strip()
            classification = str(row.get("classification_raw") or "").strip()
            kind = str(row.get("account_type_raw") or "").strip()
            if kind == "S":
                groups[_plain(name)] = classification
                continue
            if str(row.get("account_status_raw") or "").strip() == "I":
                continue
            self.accounts.append(ChartAccount(int(str(row["account_code"])), classification, name))
        self.by_name: dict[str, list[ChartAccount]] = {}
        for account in self.accounts:
            self.by_name.setdefault(_plain(account.name), []).append(account)
        self.customers = groups.get("CLIENTES", "")
        self.suppliers = groups.get("FORNECEDORES", "")

    def __len__(self) -> int:
        return len(self.accounts)

    def named(self, pattern: str) -> tuple[ChartAccount, ...]:
        """Conta de nome igual; `*` no fim aceita qualquer complemento (ex.: um por sócio)."""
        wanted = _plain(pattern.rstrip("*"))
        if pattern.endswith("*"):
            return tuple(
                a for key, items in self.by_name.items() if key.startswith(wanted) for a in items
            )
        return tuple(self.by_name.get(wanted, ()))

    def party(self, kind: str, name: str) -> tuple[ChartAccount, ...]:
        prefix = self.customers if kind == "receivable" else self.suppliers
        wanted = _plain(name)
        if not prefix or not wanted:
            return ()
        return tuple(a for a in self.by_name.get(wanted, ()) if a.classification.startswith(prefix))

    def containing_digits(self, digits: str) -> tuple[ChartAccount, ...]:
        return tuple(
            a
            for a in self.accounts
            if digits and digits in re.sub(r"\D", "", a.name) and not a.name.startswith("(-)")
        )


def read_chart_jsonl(content: bytes, chart_company_code: int) -> Chart:
    """Plano no contrato da descoberta D-373 (`chart-accounts.jsonl`), filtrado pela empresa."""
    rows = []
    for number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MultisourceError(f"Plano de contas: linha {number} inválida.") from exc
        if row.get("chart_company_code") == chart_company_code:
            rows.append(row)
    if not rows:
        raise MultisourceError(f"Plano de contas: empresa do plano {chart_company_code} ausente.")
    return Chart(rows)


def _bank_side(line: LineResult) -> str:
    return RECEIPT_BANK if line.bank.amount_cents > 0 else PAYMENT_BANK


def _nature(line: LineResult, part: Part, chart: Chart) -> list[Suggestion]:
    text = _plain(part.label)
    for pattern, names, note in NATURE_RULES:
        if re.search(pattern, text):
            found = tuple(a for name in names for a in chart.named(name))
            return [Suggestion("banco", found, note)]
    if line.bank.tax_id or line.bank.counterparty:
        # Em setembro, todo PIX/boleto pago foi contra PAGAMENTO DE FORNECEDORES e todo recebido
        # contra COBRANÇA.
        return [Suggestion("banco", chart.named(_bank_side(line)))]
    return []


def suggest_part(
    line: LineResult, part: Part, chart: Chart, result: SimulationResult
) -> list[Suggestion]:
    """Sugestões para uma parte; lista vazia quando a prática de setembro não cobre o caso."""
    if part.kind in ("receivable", "payable"):
        item = result.installments.get(part.installment_key) if part.installment_key else None
        bank = RECEIPT_BANK if part.kind == "receivable" else PAYMENT_BANK
        party = chart.party(part.kind, item.party_name) if item else ()
        return [
            Suggestion("banco", chart.named(bank)),
            Suggestion("baixa", party, "" if party else "conta do cliente/fornecedor não achada"),
        ]
    if part.kind == "interest":
        return [
            Suggestion("banco", chart.named(RECEIPT_BANK)),
            Suggestion("baixa", chart.named(INTEREST), "Q-53"),
        ]
    if part.kind == "document":
        return [Suggestion("banco", chart.named(_bank_side(line)), "título fora da posição")]
    if part.kind == "investment":
        return [Suggestion("banco", chart.named(INVESTMENT))]
    if part.kind == "transfer":
        other = part.source.upper()
        return [Suggestion("banco", chart.named(TAB_ACCOUNTS.get(other, other)), "Q-57")]
    if part.kind == "loan":
        contract = re.search(r"Empréstimo (\S+)", part.label)
        digits = re.sub(r"\D", "", contract[1]) if contract else ""
        principal = chart.containing_digits(digits)
        return [
            Suggestion(
                "banco",
                principal + chart.named(LOAN_INTEREST),
                "principal + juros; divisão a definir (Q-55)",
            )
        ]
    if part.kind == "card":
        return [Suggestion("banco", chart.named(PAYMENT_BANK), "prática de setembro (Q-56)")]
    if part.kind == "nature":
        return _nature(line, part, chart)
    return []


@dataclass
class AccountSuggestions:
    by_part: dict[int, list[Suggestion]]
    parts: int
    covered: int
    missing_party: int
    roles: Counter[str]

    def for_part(self, part: Part) -> list[Suggestion]:
        return self.by_part.get(id(part), [])

    def text(self, part: Part) -> str:
        return "; ".join(str(s) for s in self.for_part(part))


def suggest_accounts(result: SimulationResult, chart: Chart) -> AccountSuggestions:
    by_part: dict[int, list[Suggestion]] = {}
    parts = covered = missing_party = 0
    roles: Counter[str] = Counter()
    for line in result.lines:
        for part in line.parts:
            parts += 1
            found = suggest_part(line, part, chart, result)
            by_part[id(part)] = found
            if found and all(s.accounts for s in found):
                covered += 1
            missing_party += any(s.role == "baixa" and not s.accounts for s in found)
            for suggestion in found:
                for account in suggestion.accounts:
                    roles[f"{suggestion.role}: {account}"] += 1
    return AccountSuggestions(by_part, parts, covered, missing_party, roles)


def summary_lines(suggestions: AccountSuggestions, *, chart_size: int) -> list[str]:
    lines = [
        "",
        "## Contas sugeridas — a confirmar com a contadora (D-420)",
        "",
        f"- Plano de contas lido: {chart_size} contas analíticas ativas.",
        f"- Partes com conta sugerida: {suggestions.covered} de {suggestions.parts}.",
        "- Baixas sem conta do cliente/fornecedor com o mesmo nome no plano: "
        f"{suggestions.missing_party}.",
        "- Prática observada no Razão de setembro; nenhuma sugestão vira lançamento.",
        "",
        "| Uso | Partes |",
        "|---|---:|",
    ]
    banco = [(k, n) for k, n in suggestions.roles.most_common() if k.startswith("banco:")]
    for key, count in banco[:15]:
        lines.append(f"| {key} | {count} |")
    baixa = sum(n for k, n in suggestions.roles.items() if k.startswith("baixa:"))
    lines.append(f"| baixa: contas de clientes, fornecedores e juros | {baixa} |")
    return lines


def chart_for_company(company: object) -> Chart | None:
    """Plano da empresa pela descoberta D-373 mais recente e consistente; None sem plano único."""
    from apps.hub.account_auto_link import _owners
    from apps.hub.account_discovery import latest_consistent_discovery
    from apps.hub.models import (
        ReconciliationCompanyDiscovery,
        ReconciliationDiscoveredChartAccount,
    )

    office = getattr(company, "organization", None)
    discovery = latest_consistent_discovery(office) if office is not None else None
    if discovery is None:
        return None
    record = ReconciliationCompanyDiscovery.objects.filter(
        discovery=discovery, organization=office, company=company
    ).first()
    plans: Sequence[int] = sorted(set(_owners(record))) if record else ()
    if len(plans) != 1:
        return None
    rows = ReconciliationDiscoveredChartAccount.objects.filter(
        discovery=discovery, organization=office, chart_company_code=plans[0]
    ).values_list("row", flat=True)
    chart = Chart(rows)
    return chart if len(chart) else None
