"""CNPJ validation and bounded public registry lookup; never collect partner data."""

import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.core.exceptions import ValidationError


def normalize_cnpj(value: str) -> str:
    cnpj = re.sub(r"[./\-\s]", "", value).upper()
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", cnpj) or len(set(cnpj)) == 1:
        raise ValidationError("Confira o CNPJ informado.")
    base = cnpj[:12]
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        remainder = sum(
            (ord(char) - 48) * weight for char, weight in zip(base, weights, strict=True)
        ) % 11
        base += str(0 if remainder < 2 else 11 - remainder)
    if base != cnpj:
        raise ValidationError("Confira os dígitos do CNPJ informado.")
    return cnpj


def lookup_company(cnpj: str) -> dict[str, str]:
    cnpj = normalize_cnpj(cnpj)
    key = "company-registry:" + hashlib.sha256(cnpj.encode()).hexdigest()
    cached = cache.get(key)
    if isinstance(cached, dict) and all(
        isinstance(key, str) and isinstance(value, str) for key, value in cached.items()
    ):
        return cached
    result = {"status": "unavailable"}
    request = Request(
        f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
        headers={"Accept": "application/json", "User-Agent": "CICA/1.0"},
    )
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - fixed HTTPS origin
            data = json.loads(response.read(256_001))
        if (
            isinstance(data, dict)
            and str(data.get("cnpj", "")).upper() == cnpj
            and data.get("razao_social")
        ):
            result = {"status": "found", "source": "BrasilAPI"}
            for key_name in (
                "razao_social",
                "nome_fantasia",
                "municipio",
                "uf",
                "descricao_situacao_cadastral",
                "cnae_fiscal_descricao",
                "data_inicio_atividade",
                "descricao_tipo_de_logradouro",
                "logradouro",
                "numero",
                "complemento",
                "bairro",
                "cep",
            ):
                result[key_name] = str(data.get(key_name) or "")[:240]
    except HTTPError as error:
        result = {"status": "not_found" if error.code == 404 else "unavailable"}
    except (URLError, TimeoutError, OSError, ValueError):
        pass
    cache.set(key, result, 3600 if result["status"] == "found" else 60)
    return result
