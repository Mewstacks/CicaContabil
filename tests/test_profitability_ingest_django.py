"""A ingestão: da página que o agente envia até a linha do cadastro.

O que este arquivo prova, além do caminho feliz, são as três guardas que
sustentam a confiabilidade do ciclo — identidade por hash com ordinal,
reconciliação que marca em vez de apagar, e orçamento de rejeição com o piso de
que rejeitar tudo é falha — e a ponte que D-109 criou: a linha do ERP encontra a
empresa que a carteira do hub já tem, em vez de cadastrar uma segunda.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

import pytest
from django.test import TestCase

from apps.hub.models import ClientCompany, Connector, OfficeProfile
from apps.organizations.models import Organization
from apps.profitability.catalog import load_catalog
from apps.profitability.ingest import process_run
from apps.profitability.models import (
    ClienteCompetenciaMetrics,
    Colaborador,
    CompanyErpProfile,
    Competencia,
    IngestBatch,
    IngestRun,
    Mensalidade,
    RegistroHoras,
    SalarioColaborador,
    ServicoFaturado,
    SistemaOrigem,
    StatusCorrespondencia,
    UsuarioErp,
)

D = Decimal


class IngestTestCase(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.connector = Connector.objects.create(
            organization=self.office, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )
        self.catalog = load_catalog()

    def _run(
        self,
        dataset_code: str,
        rows: list[dict[str, Any]],
        *,
        source_system: str = SistemaOrigem.DOMINIO,
        run_kind: str = IngestRun.RunKind.FULL,
        parameters: list[dict[str, Any]] | None = None,
        key: str = "",
        query_sha256: str | None = None,
    ) -> IngestRun:
        definition = self.catalog.get(source_system, dataset_code)
        run = IngestRun.objects.create(
            organization=self.office,
            connector=self.connector,
            source_system=source_system,
            dataset_code=dataset_code,
            schema_version=definition.schema_version,
            query_sha256=query_sha256 or definition.query_sha256,
            run_kind=run_kind,
            parameters=parameters or [],
            idempotency_key=key or f"{dataset_code}-{IngestRun.objects.count()}",
            status=IngestRun.Status.PROCESSING,
            row_count=len(rows),
            batch_count=1,
        )
        payload = json.dumps(rows)
        IngestBatch.objects.create(
            organization=self.office,
            run=run,
            sequence=0,
            row_count=len(rows),
            checksum_sha256=hashlib.sha256(payload.encode()).hexdigest(),
            payload=payload,
        )
        return run

    def _ingest(self, dataset_code: str, rows: list[dict[str, Any]], **kwargs: Any) -> IngestRun:
        run = self._run(dataset_code, rows, **kwargs)
        process_run(run.id)
        return run

    def _company_row(
        self, codi_emp: int, razao: str, documento: str, situacao: str = "A"
    ) -> dict[str, Any]:
        return {
            "codi_emp": codi_emp,
            "razao_emp": razao,
            "cgce_emp": documento,
            "situacao": situacao,
        }


class CarteiraUnicaTests(IngestTestCase):
    def test_empresa_que_o_hub_ja_tem_nao_vira_uma_segunda(self) -> None:
        """É o comportamento que D-109 existe para garantir."""

        existente = ClientCompany.objects.create(
            organization=self.office, name="Padaria Central", dominio_code="25"
        )

        self._ingest(
            "companies", [self._company_row(25, "PADARIA CENTRAL LTDA", "12.345.678/0001-99")]
        )

        assert ClientCompany.objects.count() == 1
        perfil = CompanyErpProfile.objects.get()
        assert perfil.empresa_id == existente.id
        assert perfil.codi_emp == 25
        existente.refresh_from_db()
        assert existente.name == "PADARIA CENTRAL LTDA"

    def test_empresa_desconhecida_entra_na_carteira_com_o_codigo_dominio(self) -> None:
        self._ingest("companies", [self._company_row(25, "PADARIA LTDA", "12.345.678/0001-99")])

        empresa = ClientCompany.objects.get()
        assert empresa.dominio_code == "25"
        assert empresa.name == "PADARIA LTDA"
        assert empresa.active is True

    def test_siescon_nao_escreve_o_codigo_dominio(self) -> None:
        """NFS-e, conciliação e DTE casam empresa por esse campo; o Siescon numera o seu."""

        self._ingest(
            "companies",
            [self._company_row(711, "PADARIA LTDA", "12.345.678/0001-99")],
            source_system=SistemaOrigem.SIESCON,
        )

        empresa = ClientCompany.objects.get()
        assert empresa.dominio_code == ""
        assert CompanyErpProfile.objects.get().codi_emp == 711

    def test_a_gemea_do_siescon_encontra_a_empresa_pelo_documento(self) -> None:
        self._ingest("companies", [self._company_row(25, "PADARIA LTDA", "12.345.678/0001-99")])
        self._ingest(
            "companies",
            [self._company_row(711, "PADARIA LTDA", "12.345.678/0001-99")],
            source_system=SistemaOrigem.SIESCON,
        )

        # Uma empresa na carteira, dois perfis de ERP apontando para ela.
        assert ClientCompany.objects.count() == 1
        assert CompanyErpProfile.objects.count() == 2
        assert {p.sistema_origem for p in CompanyErpProfile.objects.all()} == {"dominio", "siescon"}

    def test_escritorio_que_exige_codigo_dominio_recusa_empresa_so_do_siescon(self) -> None:
        """A regra do escritório não pode ser furada por um caminho que o formulário não vê."""

        OfficeProfile.objects.create(organization=self.office, require_dominio_code=True)

        run = self._run(
            "companies",
            [self._company_row(711, "SO NO SIESCON", "99.999.999/0001-99")],
            source_system=SistemaOrigem.SIESCON,
        )
        with pytest.raises(ValueError, match="todas as 1 linhas foram rejeitadas"):
            process_run(run.id)

        assert ClientCompany.objects.count() == 0

    def test_empresa_inativa_continua_cadastrada_e_sai_da_carteira(self) -> None:
        """Filtrar na origem faria a reconciliação sumir com o cadastro."""

        self._ingest("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99", "I")])

        empresa = ClientCompany.objects.get()
        assert empresa.active is False
        assert CompanyErpProfile.objects.get().deleted_at is None


class ContratoTests(IngestTestCase):
    def test_coluna_fora_do_contrato_falha_o_ciclo_inteiro(self) -> None:
        run = self._run("companies", [{"codi_emp": 25, "razao_emp": "X", "cgce_emp": "1"}])

        with pytest.raises(ValueError, match="divergem do contrato"):
            process_run(run.id)

    def test_consulta_diferente_da_vigente_nao_e_aplicada(self) -> None:
        """Fixar o hash existe justamente para isto."""

        run = self._run(
            "companies",
            [self._company_row(25, "PADARIA", "12.345.678/0001-99")],
            query_sha256="f" * 64,
        )

        with pytest.raises(ValueError, match="não é a do contrato vigente"):
            process_run(run.id)

    def test_contrato_ainda_nao_validado_nao_e_despachado(self) -> None:
        run = self._run(
            "salaries",
            [],
            parameters=[{"name": "codi_emp", "value": 1}],
        )

        with pytest.raises(ValueError, match="não validado"):
            process_run(run.id)

    def test_pagina_adulterada_nao_e_aplicada(self) -> None:
        run = self._run("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99")])
        batch = IngestBatch.objects.get(run=run)
        batch.payload = json.dumps([self._company_row(99, "OUTRA", "99.999.999/0001-99")])
        batch.save(update_fields=["payload"])

        with pytest.raises(ValueError, match="não confere com a soma"):
            process_run(run.id)

    def test_contagem_divergente_do_declarado_falha(self) -> None:
        run = self._run("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99")])
        run.row_count = 5
        run.save(update_fields=["row_count"])

        with pytest.raises(ValueError, match="Contagem processada diverge"):
            process_run(run.id)


class HorasTests(IngestTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._ingest("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99")])
        self._ingest("users", [{"i_usuario": "ANA.W", "situacao": 1, "nome": "Ana Woltmann"}])
        self.empresa = ClientCompany.objects.get()

    def _hora(self, inicio: str, fim: str, data: str = "2026-09-10") -> dict[str, Any]:
        return {
            "codi_emp": 25,
            "usua_log": "ANA.W",
            "data_log": data,
            "tini_log": inicio,
            "tfim_log": fim,
            "dfim_log": None,
        }

    def _run_horas(self, rows: list[dict[str, Any]], **kwargs: Any) -> IngestRun:
        return self._run(
            "automatic_hours",
            rows,
            parameters=[
                {"name": "start_date", "value": "2026-09-01"},
                {"name": "end_date", "value": "2026-09-30"},
            ],
            **kwargs,
        )

    def test_horas_entram_ligadas_a_empresa_e_ao_usuario(self) -> None:
        process_run(self._run_horas([self._hora("09:00:00", "10:30:00")]).id)

        registro = RegistroHoras.objects.get()
        assert registro.empresa_id == self.empresa.id
        assert registro.duracao_minutos == 90
        assert registro.competencia == "2026-09"
        assert registro.usuario_erp is not None
        assert Competencia.objects.filter(competencia="2026-09").exists()

    def test_linhas_iguais_convivem_pelo_ordinal(self) -> None:
        """Duas sessões idênticas são legítimas; o ordinal preserva as duas."""

        process_run(self._run_horas([self._hora("09:00:00", "10:00:00")] * 2).id)

        assert RegistroHoras.objects.count() == 2
        assert set(RegistroHoras.objects.values_list("occurrence_index", flat=True)) == {0, 1}

    def test_repetir_o_ciclo_converge_em_vez_de_duplicar(self) -> None:
        linhas = [self._hora("09:00:00", "10:00:00"), self._hora("14:00:00", "15:00:00")]
        process_run(self._run_horas(linhas, key="h1").id)
        process_run(self._run_horas(linhas, key="h2").id)

        assert RegistroHoras.objects.count() == 2

    def test_sessao_que_atravessa_a_meia_noite(self) -> None:
        process_run(self._run_horas([self._hora("23:30:00", "00:30:00")]).id)

        registro = RegistroHoras.objects.get()
        assert registro.duracao_minutos == 60
        assert str(registro.data_fim) == "2026-09-11"

    def test_ciclo_completo_marca_como_removido_o_que_a_fonte_nao_trouxe(self) -> None:
        """Marca, não apaga: o histórico sobrevive à sincronização."""

        process_run(self._run_horas([self._hora("09:00:00", "10:00:00")], key="h1").id)
        assert RegistroHoras.objects.filter(deleted_at__isnull=True).count() == 1

        process_run(self._run_horas([], key="h2").id)

        assert RegistroHoras.objects.count() == 1
        assert RegistroHoras.objects.filter(deleted_at__isnull=True).count() == 0

    def test_ciclo_incremental_nunca_varre(self) -> None:
        """Janela parcial não pode apagar histórico."""

        process_run(self._run_horas([self._hora("09:00:00", "10:00:00")], key="h1").id)
        process_run(self._run_horas([], key="h2", run_kind=IngestRun.RunKind.INCREMENTAL).id)

        assert RegistroHoras.objects.filter(deleted_at__isnull=True).count() == 1

    def test_hora_de_empresa_desconhecida_e_rejeitada_sem_derrubar_o_ciclo(self) -> None:
        linhas = [
            self._hora("09:00:00", "10:00:00"),
            {**self._hora("09:00:00", "10:00:00"), "codi_emp": 999},
        ]
        run = self._run_horas(linhas)

        process_run(run.id)

        run.refresh_from_db()
        assert run.status == IngestRun.Status.SUCCEEDED
        assert run.rejected_count == 1
        assert run.rejection_sample[0]["motivo"] == "Empresa das horas não está no cadastro."
        assert "codi_emp" not in json.dumps(run.rejection_sample)
        assert RegistroHoras.objects.filter(deleted_at__isnull=True).count() == 1

    def test_ciclo_que_rejeitou_tudo_falha(self) -> None:
        """Foi assim que um conjunto de 44 usuários reportou sucesso sem gravar ninguém."""

        run = self._run_horas([{**self._hora("09:00:00", "10:00:00"), "codi_emp": 999}] * 3)

        with pytest.raises(ValueError, match="todas as 3 linhas foram rejeitadas"):
            process_run(run.id)

    def test_acima_do_orcamento_o_ciclo_falha(self) -> None:
        boas = [self._hora("09:00:00", "10:00:00", data=f"2026-09-{d:02d}") for d in range(1, 29)]
        ruins = [{**self._hora("09:00:00", "10:00:00"), "codi_emp": 999}] * 101
        run = self._run_horas(boas + ruins)

        with pytest.raises(ValueError, match="acima do limite"):
            process_run(run.id)

    def test_o_ciclo_reprojeta_a_competencia_que_tocou(self) -> None:
        process_run(self._run_horas([self._hora("09:00:00", "10:00:00")]).id)

        assert ClienteCompetenciaMetrics.objects.filter(
            empresa=self.empresa, competencia="2026-09"
        ).exists()


class FolhaEReceitaTests(IngestTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._ingest(
            "companies",
            [
                self._company_row(25, "PADARIA", "12.345.678/0001-99"),
                self._company_row(1, "CONTABILIDADE", "99.999.999/0001-99"),
            ],
        )
        self.fonte = CompanyErpProfile.objects.get(codi_emp=1)
        self.cliente = CompanyErpProfile.objects.get(codi_emp=25).empresa

    def _armar(self, papel: str) -> None:
        self.fonte.papel = [papel]
        self.fonte.save(update_fields=["papel", "updated_at"])

    def test_folha_sem_fonte_armada_e_recusada(self) -> None:
        """Nada vem armado: errar para o lado permissivo importaria salário de todo cliente."""

        run = self._run(
            "salaries",
            [
                {
                    "codi_emp": 1,
                    "i_empregados": 7,
                    "nome": "Ana Woltmann",
                    "ultima_competencia": "2026-09",
                    "salario_mais_recente": "3000.00",
                }
            ],
            source_system=SistemaOrigem.SIESCON,
            parameters=[{"name": "codi_emp", "value": 1}],
        )

        # A folha do Siescon deriva a empresa do contexto, não da linha: sem fonte
        # armada o ciclo nem chega a processar linha, o que é a recusa mais cedo
        # possível.
        with pytest.raises(ValueError, match="Nenhuma empresa marcada como payroll_source"):
            process_run(run.id)

    def test_folha_com_fonte_armada_cria_colaborador_e_salario(self) -> None:
        self._ingest(
            "companies",
            [self._company_row(1, "CONTABILIDADE", "99.999.999/0001-99")],
            source_system=SistemaOrigem.SIESCON,
        )
        fonte_siescon = CompanyErpProfile.objects.get(sistema_origem="siescon", codi_emp=1)
        fonte_siescon.papel = ["payroll_source"]
        fonte_siescon.save(update_fields=["papel", "updated_at"])

        self._ingest(
            "salaries",
            [
                {
                    "i_empregados": 7,
                    "nome": "Ana Woltmann",
                    "salario_mais_recente": "3000.00",
                }
            ],
            source_system=SistemaOrigem.SIESCON,
            parameters=[{"name": "codi_emp", "value": 1}],
        )

        colaborador = Colaborador.objects.get()
        assert colaborador.nome == "Ana Woltmann"
        assert colaborador.i_empregados == 7
        assert SalarioColaborador.objects.get().salario == D("3000.00")

    def test_honorario_casa_o_cliente_pelo_documento(self) -> None:
        self._armar("billing_source")

        self._ingest(
            "billing_honorarios",
            [
                {
                    "codi_emp_origem": 1,
                    "codi_cli": 3,
                    "nome_cli": "PADARIA",
                    "documento_cli": "12.345.678/0001-99",
                    "ano_servico": 2026,
                    "mes_servico": 8,
                    "valor": "1500.00",
                }
            ],
            parameters=[
                {"name": "start_date", "value": "2026-08-01"},
                {"name": "end_date", "value": "2026-08-31"},
            ],
        )

        servico = ServicoFaturado.objects.get()
        assert servico.empresa_id == self.cliente.id
        assert servico.forma_localizacao == StatusCorrespondencia.CPF_CNPJ
        mensalidade = Mensalidade.objects.get()
        assert mensalidade.valor == D("1500.00")
        assert mensalidade.competencia == "2026-08"

    def test_honorario_sem_documento_casa_pela_razao_social(self) -> None:
        self._armar("billing_source")

        self._ingest(
            "billing_honorarios",
            [
                {
                    "codi_emp_origem": 1,
                    "codi_cli": 3,
                    "nome_cli": "padaria",
                    "documento_cli": "",
                    "ano_servico": 2026,
                    "mes_servico": 8,
                    "valor": "1500.00",
                }
            ],
            parameters=[
                {"name": "start_date", "value": "2026-08-01"},
                {"name": "end_date", "value": "2026-08-31"},
            ],
        )

        servico = ServicoFaturado.objects.get()
        assert servico.empresa_id == self.cliente.id
        assert servico.forma_localizacao == StatusCorrespondencia.RAZAO_SOCIAL

    def test_correcao_manual_da_mensalidade_sobrevive_ao_ciclo(self) -> None:
        self._armar("billing_source")
        linha = {
            "codi_emp_origem": 1,
            "codi_cli": 3,
            "nome_cli": "PADARIA",
            "documento_cli": "12.345.678/0001-99",
            "ano_servico": 2026,
            "mes_servico": 8,
            "valor": "1500.00",
        }
        janela = [
            {"name": "start_date", "value": "2026-08-01"},
            {"name": "end_date", "value": "2026-08-31"},
        ]
        self._ingest("billing_honorarios", [linha], parameters=janela, key="b1")

        mensalidade = Mensalidade.objects.get()
        mensalidade.manual_override = D("2000.00")
        mensalidade.save(update_fields=["manual_override", "updated_at"])

        self._ingest("billing_honorarios", [linha], parameters=janela, key="b2")

        mensalidade.refresh_from_db()
        assert mensalidade.manual_override == D("2000.00")
        assert mensalidade.valor_efetivo == D("2000.00")


class UsuariosETributacaoTests(IngestTestCase):
    def test_usuario_guarda_o_login_como_texto(self) -> None:
        """Tratá-lo como inteiro rejeitava toda linha de horas, em silêncio."""

        self._ingest("users", [{"i_usuario": "ANA.W", "situacao": 1, "nome": "Ana"}])

        assert UsuarioErp.objects.get().i_usuario == "ANA.W"

    def test_usuario_que_sumiu_da_fonte_e_desativado_sem_ser_apagado(self) -> None:
        self._ingest("users", [{"i_usuario": "ANA.W", "situacao": 1, "nome": "Ana"}], key="u1")
        self._ingest("users", [], key="u2")

        usuario = UsuarioErp.objects.get()
        assert usuario.ativo is False

    def test_tributacao_aplica_o_regime_a_empresa(self) -> None:
        self._ingest("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99")])

        self._ingest(
            "taxation",
            [{"codi_emp": 25, "vigencia_par": "2026-01-01", "rfed_par": 5}],
        )

        perfil = CompanyErpProfile.objects.get()
        assert perfil.regime_codigo == 5
        assert perfil.regime == "Lucro Presumido"

    def test_o_ciclo_liga_o_usuario_ao_colaborador_no_fim(self) -> None:
        """A folha chega num ciclo separado; o vínculo é resolvido depois de gravar tudo."""

        Colaborador.objects.create(
            organization=self.office, codigo="A", nome="Ana Paula Velho Wolff"
        )

        self._ingest("users", [{"i_usuario": "ANA.W", "situacao": 1, "nome": "Ana Paula Wolff"}])

        assert UsuarioErp.objects.get().colaborador is not None


class IsolamentoTests(IngestTestCase):
    def test_o_ciclo_nao_enxerga_o_cadastro_de_outro_escritorio(self) -> None:
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        ClientCompany.objects.create(organization=vizinho, name="Alheia", dominio_code="25")

        self._ingest("companies", [self._company_row(25, "PADARIA", "12.345.678/0001-99")])

        assert ClientCompany.objects.filter(organization=self.office).count() == 1
        assert ClientCompany.objects.filter(organization=vizinho).count() == 1
        assert CompanyErpProfile.objects.get().organization_id == self.office.id

    def test_os_dois_erps_nao_se_sobrescrevem(self) -> None:
        """`codi_emp` só é único dentro de um sistema."""

        self._ingest("companies", [self._company_row(25, "DO DOMINIO", "11.111.111/0001-11")])
        self._ingest(
            "companies",
            [self._company_row(25, "DO SIESCON", "22.222.222/0001-22")],
            source_system=SistemaOrigem.SIESCON,
        )

        assert CompanyErpProfile.objects.count() == 2
        assert ClientCompany.objects.count() == 2
