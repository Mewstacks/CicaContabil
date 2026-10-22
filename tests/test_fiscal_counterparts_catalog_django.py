"""Contrato `fiscal_counterparts.v1` e a regra de despacho sob demanda.

O dataset alimenta a fila própria da Contraprova (`contraprova/jobs/next`) e nunca o
ciclo diário de `profitability/datasets`, nem depois de validado.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import shutil
from pathlib import Path
from typing import Any

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import Connector
from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.organizations.models import Organization
from apps.profitability.catalog import load_catalog

REAL_ROOT = Path(__file__).resolve().parents[1] / "contracts" / "datasets"
CHAVE = "dominio:fiscal_counterparts"

PARAMETROS_ESPERADOS = [
    ("codi_emp_sai", "Int"),
    ("start_sai", "Date"),
    ("end_sai", "Date"),
    ("codi_emp_ent", "Int"),
    ("start_ent", "Date"),
    ("end_ent", "Date"),
]


class FiscalCounterpartsContractTests(TestCase):
    def test_hash_confere_e_contrato_esta_completo(self) -> None:
        definicao = load_catalog(REAL_ROOT).definitions[CHAVE]

        assert definicao.query_sha256 == hashlib.sha256(definicao.sql.encode()).hexdigest()
        assert definicao.schema_version == 1
        assert [(p.name, p.odbc_type) for p in definicao.parameters] == PARAMETROS_ESPERADOS
        assert [c["name"] for c in definicao.columns] == ["chave_nfe", "direcao", "uf"]
        assert definicao.identity_columns == ("chave_nfe", "direcao")
        assert definicao.allowed_run_kinds == ("full",)
        assert definicao.max_rows_per_run == 200000
        assert definicao.dispatch == "on_demand"
        assert definicao.sql.count("?") == 6
        assert "\r" not in definicao.sql

    def test_manifest_real_segue_nao_validado(self) -> None:
        assert load_catalog(REAL_ROOT).definitions[CHAVE].validated is False


class OnDemandNotListedTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        credentials = redeem_enrollment(
            code=issue_enrollment(organization=self.office).code,
            label="Servidor Domínio",
            fingerprint="device-fp",
        )
        self.agent_id = credentials.agent_id
        self.secret = credentials.shared_secret
        Connector.objects.create(
            organization=self.office, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )

    def _datasets(self) -> Any:
        body = json.dumps({"source_system": "dominio"}).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            self.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return Client().post(
            reverse("agent-v2-profitability-datasets"),
            data=body,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": str(self.agent_id),
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )

    def _root_validado(self, tmp_path: Path) -> Path:
        root = tmp_path / "datasets"
        shutil.copytree(REAL_ROOT, root)
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["datasets"]:
            if item["sourceSystem"] == "dominio" and item["code"] == "fiscal_counterparts":
                item["validated"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return root

    def test_nunca_listado_mesmo_validado(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._root_validado(Path(tmp))
            assert load_catalog(root).definitions[CHAVE].validated is True
            with override_settings(PROFITABILITY_SYNC_ENABLED=True, DATASET_CATALOG_ROOT=str(root)):
                codigos = {item["code"] for item in self._datasets().json()["datasets"]}

        assert "companies" in codigos
        assert "fiscal_counterparts" not in codigos
