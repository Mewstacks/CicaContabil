"""Os pontos de entrada que o agente Windows usa para entregar o ERP.

O que interessa provar aqui é o portão, não o caminho feliz: a autenticação é a
mesma do resto do agente e não foi reimplementada; a sincronização nasce
desligada; o catálogo não oferece contrato não validado nem contrato que dependa
de uma fonte que ninguém armou; e uma execução só existe se o escritório tiver
conector habilitado.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ClientCompany, Connector
from apps.intelligence.agents import issue_enrollment, redeem_enrollment, revoke_agent
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.profitability.models import (
    CompanyErpProfile,
    IngestBatch,
    IngestRun,
    RegistroHoras,
    SistemaOrigem,
)

LIGADO = override_settings(PROFITABILITY_SYNC_ENABLED=True)


class AgentApiTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.client = Client()
        credentials = redeem_enrollment(
            code=issue_enrollment(organization=self.office).code,
            label="Servidor Domínio",
            fingerprint="device-fp",
        )
        self.agent_id = credentials.agent_id
        self.secret = credentials.shared_secret
        self.connector = Connector.objects.create(
            organization=self.office, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )

    def _post(self, url: str, payload: dict[str, Any], *, secret: str | None = None) -> Any:
        body = json.dumps(payload).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            (secret or self.secret).encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            url,
            data=body,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": str(self.agent_id),
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )

    def _datasets(self, **payload: Any) -> Any:
        return self._post(reverse("agent-v2-profitability-datasets"), payload)

    def _abrir(self, **payload: Any) -> Any:
        base = {
            "source_system": SistemaOrigem.DOMINIO,
            "dataset_code": "companies",
            "schema_version": 2,
            "run_kind": IngestRun.RunKind.FULL,
            "idempotency_key": "chave-1",
        }
        return self._post(reverse("agent-v2-profitability-run-open"), {**base, **payload})

    # --- portão de autenticação -------------------------------------------------

    def test_assinatura_errada_nao_passa(self) -> None:
        resposta = self._post(
            reverse("agent-v2-profitability-datasets"), {}, secret="outro-segredo"
        )
        assert resposta.status_code == 401

    def test_agente_revogado_deixa_de_ser_aceito(self) -> None:
        """A autenticação é a do agente da CICA; não há um segundo caminho aqui."""

        revoke_agent(agent=EdgeAgent.objects.get(id=self.agent_id))

        assert self._datasets().status_code == 401

    # --- sincronização desligada ------------------------------------------------

    def test_desligada_o_catalogo_volta_vazio(self) -> None:
        resposta = self._datasets()

        assert resposta.status_code == 200
        assert resposta.json() == {"datasets": [], "manifest_sha256": "", "enabled": False}

    def test_desligada_nenhuma_execucao_e_aberta(self) -> None:
        assert self._abrir().status_code == 409
        assert IngestRun.objects.count() == 0

    # --- catálogo ----------------------------------------------------------------

    @LIGADO
    def test_catalogo_nao_oferece_contrato_nao_validado(self) -> None:
        codigos = {item["code"] for item in self._datasets().json()["datasets"]}

        assert "companies" in codigos
        assert "salaries" not in codigos, "salaries do Domínio ainda não foi validado"
        assert "billing_services" not in codigos

    @LIGADO
    def test_catalogo_nao_oferece_contrato_de_fonte_nao_armada(self) -> None:
        """Nada vem armado: oferecer honorários por padrão leria a receita de todo mundo."""

        codigos = {item["code"] for item in self._datasets().json()["datasets"]}
        assert "billing_honorarios" not in codigos

        empresa = ClientCompany.objects.create(
            organization=self.office, name="Contabilidade", dominio_code="1"
        )
        CompanyErpProfile.objects.create(
            organization=self.office, empresa=empresa, codi_emp=1, papel=["billing_source"]
        )

        codigos = {item["code"] for item in self._datasets().json()["datasets"]}
        assert "billing_honorarios" in codigos

    @LIGADO
    def test_catalogo_entrega_o_hash_da_consulta_e_do_manifesto(self) -> None:
        corpo = self._datasets().json()

        assert len(corpo["manifest_sha256"]) == 64
        companies = next(d for d in corpo["datasets"] if d["code"] == "companies")
        assert len(companies["query_sha256"]) == 64
        assert companies["allowed_run_kinds"] == ["full"]

    @LIGADO
    def test_cada_erp_ve_o_proprio_catalogo(self) -> None:
        dominio = {d["code"] for d in self._datasets().json()["datasets"]}
        siescon = {
            d["code"]
            for d in self._datasets(source_system=SistemaOrigem.SIESCON).json()["datasets"]
        }

        assert "automatic_hours" in dominio
        assert "automatic_hours" not in siescon

    # --- abertura de execução ----------------------------------------------------

    @LIGADO
    def test_sem_conector_habilitado_nao_ha_execucao(self) -> None:
        """Conector que nasce sozinho é configuração aparecendo sem ninguém configurar."""

        self.connector.enabled = False
        self.connector.save(update_fields=["enabled"])

        assert self._datasets().status_code == 409
        assert self._abrir().status_code == 409

    @LIGADO
    def test_contrato_desconhecido_ou_versao_divergente_e_recusado(self) -> None:
        assert self._abrir(dataset_code="inexistente").status_code == 400
        assert self._abrir(schema_version=99).status_code == 400

    @LIGADO
    def test_tipo_de_execucao_fora_do_contrato_e_recusado(self) -> None:
        """`companies` só aceita ciclo completo."""

        assert self._abrir(run_kind=IngestRun.RunKind.INCREMENTAL).status_code == 400

    @LIGADO
    def test_a_mesma_chave_retoma_em_vez_de_duplicar(self) -> None:
        primeira = self._abrir()
        segunda = self._abrir()

        assert primeira.status_code == 201
        assert segunda.status_code == 200
        assert primeira.json()["run_id"] == segunda.json()["run_id"]
        assert IngestRun.objects.count() == 1

    # --- páginas e fechamento ----------------------------------------------------

    @LIGADO
    def test_ciclo_completo_grava_a_empresa_na_carteira(self) -> None:
        run_id = self._abrir().json()["run_id"]
        linha = {
            "codi_emp": 25,
            "razao_emp": "PADARIA LTDA",
            "cgce_emp": "12.345.678/0001-99",
            "situacao": "A",
        }
        pagina = self._post(
            reverse("agent-v2-profitability-run-batch", args=[run_id]),
            {"sequence": 0, "rows": [linha]},
        )
        assert pagina.status_code == 200

        fechamento = self._post(
            reverse("agent-v2-profitability-run-complete", args=[run_id]), {"row_count": 1}
        )
        assert fechamento.status_code == 200

        run = IngestRun.objects.get(id=run_id)
        assert run.status == IngestRun.Status.SUCCEEDED
        assert ClientCompany.objects.get().dominio_code == "25"
        assert CompanyErpProfile.objects.get().codi_emp == 25

    @LIGADO
    def test_pagina_repetida_nao_conta_duas_vezes(self) -> None:
        """Reenvio depois de queda de rede tem de convergir, não somar."""

        run_id = self._abrir().json()["run_id"]
        linha = {
            "codi_emp": 25,
            "razao_emp": "PADARIA",
            "cgce_emp": "12.345.678/0001-99",
            "situacao": "A",
        }
        url = reverse("agent-v2-profitability-run-batch", args=[run_id])
        self._post(url, {"sequence": 0, "rows": [linha]})
        segunda = self._post(url, {"sequence": 0, "rows": [linha]})

        assert segunda.json()["duplicate"] is True
        run = IngestRun.objects.get(id=run_id)
        assert run.row_count == 1
        assert IngestBatch.objects.filter(run=run).count() == 1

    @LIGADO
    def test_soma_declarada_que_nao_confere_recusa_a_pagina(self) -> None:
        run_id = self._abrir().json()["run_id"]

        resposta = self._post(
            reverse("agent-v2-profitability-run-batch", args=[run_id]),
            {"sequence": 0, "rows": [], "checksum_sha256": "f" * 64},
        )

        assert resposta.status_code == 400
        assert IngestBatch.objects.count() == 0

    @LIGADO
    def test_contagem_declarada_divergente_nao_fecha_a_execucao(self) -> None:
        run_id = self._abrir().json()["run_id"]

        resposta = self._post(
            reverse("agent-v2-profitability-run-complete", args=[run_id]), {"row_count": 7}
        )

        assert resposta.status_code == 409
        assert IngestRun.objects.get(id=run_id).status == IngestRun.Status.RECEIVING

    @LIGADO
    def test_falha_declarada_pelo_agente_fica_registrada(self) -> None:
        run_id = self._abrir().json()["run_id"]

        resposta = self._post(
            reverse("agent-v2-profitability-run-failure", args=[run_id]), {"code": "odbc_timeout"}
        )

        assert resposta.status_code == 200
        run = IngestRun.objects.get(id=run_id)
        assert run.status == IngestRun.Status.FAILED
        assert run.error_code == "odbc_timeout"

    @LIGADO
    def test_contrato_errado_deixa_a_execucao_falhada_e_nao_presa(self) -> None:
        """Sem isso a execução fica "processando" para sempre e a tela não sabe dizer o quê."""

        run_id = self._abrir().json()["run_id"]
        self._post(
            reverse("agent-v2-profitability-run-batch", args=[run_id]),
            {"sequence": 0, "rows": [{"codi_emp": 25}]},
        )

        with self.assertRaises(ValueError):
            self._post(reverse("agent-v2-profitability-run-complete", args=[run_id]), {})

        run = IngestRun.objects.get(id=run_id)
        assert run.status == IngestRun.Status.FAILED
        assert "contrato" in run.error_code

    # --- isolamento ---------------------------------------------------------------

    @LIGADO
    def test_o_agente_nao_alcanca_execucao_de_outro_escritorio(self) -> None:
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        connector = Connector.objects.create(
            organization=vizinho, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )
        alheia = IngestRun.objects.create(
            organization=vizinho,
            connector=connector,
            source_system=SistemaOrigem.DOMINIO,
            dataset_code="companies",
            schema_version=2,
            query_sha256="a" * 64,
            run_kind=IngestRun.RunKind.FULL,
            idempotency_key="alheia",
            status=IngestRun.Status.RECEIVING,
        )

        resposta = self._post(
            reverse("agent-v2-profitability-run-batch", args=[alheia.id]),
            {"sequence": 0, "rows": []},
        )

        assert resposta.status_code == 404
        assert IngestBatch.objects.count() == 0
        assert RegistroHoras.objects.count() == 0
