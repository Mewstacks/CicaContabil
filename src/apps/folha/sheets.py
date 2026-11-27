"""Planilha de controle da folha (Google Sheets): achar a aba, a linha e gravar uma vez.

A parte pura (``find_tab``, ``find_row``) não toca rede. O cliente é uma interface: em produção
``GoogleSheetsClient`` (conta de serviço), nos testes um falso. Regras do HubFedrizzi mantidas:
a marcação é gravada UMA vez por (competência, empresa, etapa) e nunca sobrescreve célula
editada à mão; a linha vem por código (só em coluna com cabeçalho "Cód"), depois CNPJ, depois
nome sem sufixo societário; duas candidatas é erro, o sistema nunca chuta.
"""

from __future__ import annotations

import base64
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from typing import Any, Protocol, cast

MONTHS = (
    ("jan", "janeiro"),
    ("fev", "fevereiro"),
    ("mar", "marco"),
    ("abr", "abril"),
    ("mai", "maio"),
    ("jun", "junho"),
    ("jul", "julho"),
    ("ago", "agosto"),
    ("set", "setembro"),
    ("out", "outubro"),
    ("nov", "novembro"),
    ("dez", "dezembro"),
)
SUFFIXES = re.compile(r"\b(ltda|me|epp|eireli|sa|s a|ss|mei|cia|comercio|industria)\b")
SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class SheetError(Exception):
    """Falha esperada da planilha (aba ou empresa não encontrada, Google fora)."""


class SheetClient(Protocol):
    def titles(self, spreadsheet_id: str) -> list[str]: ...

    def read(self, spreadsheet_id: str, a1: str) -> list[list[str]]: ...

    def write(self, spreadsheet_id: str, a1: str, value: str) -> None: ...


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in folded if not unicodedata.combining(c)).lower().strip()


def _title_matches(title: str, competence: date) -> bool:
    raw = _plain(title)
    month, year = competence.month, competence.year
    short, full = MONTHS[month - 1]
    patterns = (
        rf"^0?{month}\s*[/-]\s*{year}$",
        rf"^0?{month}{year}$",
        rf"^{year}\s*[/-]\s*0?{month}$",
        rf"^{short}\s*[/-]\s*(?:{year}|{year % 100:02d})$",
        rf"^{full}\s+(?:de\s+)?{year}$",
        rf"^{short}\s+(?:de\s+)?{year}$",
    )
    return any(re.match(p, raw) for p in patterns)


def find_tab(titles: list[str], competence: date, *, template: str = "") -> str:
    """Aba da competência: pelo modelo fixo, pelo título ou, como último recurso, pelo mês só."""

    if template:
        short, full = MONTHS[competence.month - 1]
        wanted = template.format(
            mm=f"{competence.month:02d}",
            aaaa=competence.year,
            mes3=short.capitalize(),
            mes=full.capitalize(),
        )
        if wanted in titles:
            return wanted
        raise SheetError(f"Aba '{wanted}' não existe na planilha.")
    found = [t for t in titles if _title_matches(t, competence)]
    if not found:
        _, full = MONTHS[competence.month - 1]
        only_month = [t for t in titles if _plain(t) == full]
        found = only_month if len(only_month) == 1 else []
    if len(found) != 1:
        raise SheetError("Aba da competência não encontrada ou ambígua.")
    return found[0]


def _company_key(name: str) -> str:
    cleaned = SUFFIXES.sub(" ", _plain(name))
    return re.sub(r"[^a-z0-9]+", " ", cleaned).strip()


def find_row(rows: list[list[str]], *, code: str, cnpj_digits: str = "", name: str = "") -> int:
    """Número da linha (1-based) da empresa nas colunas A:H. Levanta se não achar ou se duplicar."""

    header = next((r for r in rows[:10] if any(_plain(c).startswith("cod") for c in r)), [])
    code_cols = [i for i, c in enumerate(header) if _plain(c).startswith("cod")]

    def matches(predicate: Any) -> list[int]:
        return [
            index + 1 for index, row in enumerate(rows) if any(predicate(cell) for cell in row[:8])
        ]

    hits: list[int] = []
    if code and code_cols:
        want = code.strip().lstrip("0")
        hits = [
            index + 1
            for index, row in enumerate(rows)
            if any(
                i < len(row) and row[i].strip().lstrip("0") == want and row[i].strip()
                for i in code_cols
            )
        ]
    if not hits and cnpj_digits:
        hits = matches(lambda c: re.sub(r"\D", "", c) == cnpj_digits and len(cnpj_digits) == 14)
    if not hits and name:
        key = _company_key(name)
        hits = matches(lambda c: bool(key) and _company_key(c) == key)
    unique = sorted(set(hits))
    if not unique:
        raise SheetError("Empresa não encontrada na aba.")
    if len(unique) > 1:
        raise SheetError("Mais de uma linha candidata para a empresa.")
    return unique[0]


def a1(tab: str, column: str, row: int) -> str:
    quoted = "'" + tab.replace("'", "''") + "'"
    return f"{quoted}!{column}{row}"


class GoogleSheetsClient:
    """Sheets REST com conta de serviço (JWT RS256). A credencial vem de arquivo do servidor."""

    def __init__(self, credentials_file: str) -> None:
        with open(credentials_file, encoding="utf-8") as handle:
            info = json.load(handle)
        if info.get("type") != "service_account":
            raise SheetError("Credencial da planilha precisa ser uma conta de serviço.")
        self._email = str(info["client_email"])
        self._key = str(info["private_key"])
        self._token = ""
        self._expires = 0.0

    def _access_token(self) -> str:
        if self._token and time.time() < self._expires - 60:
            return self._token
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        def b64(data: bytes) -> bytes:
            return base64.urlsafe_b64encode(data).rstrip(b"=")

        now = int(time.time())
        head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claims = b64(
            json.dumps(
                {
                    "iss": self._email,
                    "scope": SCOPE,
                    "aud": "https://oauth2.googleapis.com/token",
                    "iat": now,
                    "exp": now + 3600,
                }
            ).encode()
        )
        key = cast(
            "rsa.RSAPrivateKey",
            serialization.load_pem_private_key(self._key.encode(), password=None),
        )
        signature = key.sign(head + b"." + claims, padding.PKCS1v15(), hashes.SHA256())
        assertion = (head + b"." + claims + b"." + b64(signature)).decode()
        body = urllib.parse.urlencode(
            {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
        ).encode()
        data = self._call("https://oauth2.googleapis.com/token", body=body, auth=False)
        self._token = str(data["access_token"])
        self._expires = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def _call(
        self, url: str, *, body: bytes | None = None, method: str = "GET", auth: bool = True
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}"} if auth else {}
        if body is not None and auth:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, method=method, headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                return json.loads(response.read())  # type: ignore[no-any-return]
        except OSError as exc:
            # Só o tipo: a mensagem pode trazer a URL com o identificador da planilha.
            raise SheetError(f"Google indisponível ({type(exc).__name__}).") from exc

    def titles(self, spreadsheet_id: str) -> list[str]:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets.properties.title"
        return [s["properties"]["title"] for s in self._call(url).get("sheets", [])]

    def read(self, spreadsheet_id: str, a1_range: str) -> list[list[str]]:
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/"
            f"{urllib.parse.quote(a1_range)}"
        )
        return [[str(c) for c in row] for row in self._call(url).get("values", [])]

    def write(self, spreadsheet_id: str, a1_range: str, value: str) -> None:
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/"
            f"{urllib.parse.quote(a1_range)}?valueInputOption=USER_ENTERED"
        )
        self._call(url, body=json.dumps({"values": [[value]]}).encode(), method="PUT")
