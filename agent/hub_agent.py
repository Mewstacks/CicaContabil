"""Read-only Domínio agent skeleton. Install as a Windows service only after homologation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CompanySnapshot:
    dominio_code: str
    name: str
    cnpj_masked: str
    captured_at: str


class OdbcCursor(Protocol):
    def execute(self, query: str) -> OdbcCursor: ...
    def fetchall(self) -> list[tuple[object, ...]]: ...


COMPANIES_QUERY = """
SELECT TOP 500 codi_emp AS codigo, nome_emp AS nome, cgce_emp AS cnpj
FROM bethadba.geempre
WHERE stat_emp = 'A'
ORDER BY nome_emp
"""


def format_cnpj(value: object) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 14:
        return ""
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def read_companies(cursor: OdbcCursor) -> list[CompanySnapshot]:
    """The only query is a fixed SELECT: no interpolated identifiers or mutation statements."""
    timestamp = datetime.now().astimezone().isoformat()
    rows = cursor.execute(COMPANIES_QUERY).fetchall()
    return [
        CompanySnapshot(str(code), str(name), format_cnpj(cnpj), timestamp)
        for code, name, cnpj in rows
    ]


def serialize_companies(cursor: OdbcCursor) -> list[dict[str, str]]:
    return [asdict(company) for company in read_companies(cursor)]
