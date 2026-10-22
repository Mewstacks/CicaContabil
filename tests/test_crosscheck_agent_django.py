"""UF x Domínio pelo agente Windows: fila "pull", portões, idempotência e conferência completa.

O agente nunca recebe SQL: só código, versão, hash e parâmetros do contrato. O servidor reivindica
sem duplicar, devolve trabalho abandonado, aceita página repetida sem efeito, impõe o teto de linhas
e fecha só se a contagem bater. Tudo atrás de `CONTRAPROVA_AGENT_ENABLED`, desligado por padrão.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.crosscheck import agent, retention, services
from apps.crosscheck.engine.tools import UF_DOMINIO
from apps.crosscheck.models import CrosscheckAgentJob, CrosscheckDominioRow, CrosscheckRun
from apps.crosscheck.tasks import recover_runs
from apps.hub.models import ClientCompany, Connector
from apps.intelligence.agents import issue_enrollment, redeem_enrollment, revoke_agent
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.profitability.catalog import load_catalog
from apps.profitability.models import CompanyErpProfile
from crosscheck_support import AgentCase, chave, nfe, zip_upload

LIGADO = override_settings(CONTRAPROVA_AGENT_ENABLED=True)


class PortaoTests(AgentCase):
    def test_desligado_toda_rota_responde_404_mesmo_assinada(self) -> None:
        job = "00000000-0000-0000-0000-000000000001"

        assert self.next().status_code == 404
        assert self.batch(job, 0, []).status_code == 404
        assert self.complete(job, 0, 0).status_code == 404
        assert (
            self.post("agent-v2-crosscheck-failure", {"error_code": "odbc_error"}, job).status_code
            == 404
        )

    @LIGADO
    def test_assinatura_errada_e_agente_revogado_nao_passam(self) -> None:
        assert self.next(secret="outro-segredo").status_code == 401

        revoke_agent(agent=EdgeAgent.objects.get(id=self.agent_id))

        assert self.next().status_code == 401

    @LIGADO
    def test_sem_conector_do_dominio_nao_ha_trabalho(self) -> None:
        self.requested()
        Connector.objects.update(enabled=False)

        assert self.next().json() == {"job": None}

    @LIGADO
    def test_sistema_de_origem_desconhecido_e_recusado(self) -> None:
        resposta = self.post("agent-v2-crosscheck-next", {"source_system": "siescon"})

        assert resposta.status_code == 400

    def test_o_dataset_nunca_aparece_na_lista_de_rentabilidade(self) -> None:
        definicao = load_catalog().get("dominio", agent.DATASET_CODE)

        assert definicao.validated is False
        assert definicao.dispatch == "on_demand"


class CodiEmpTests(AgentCase):
    def test_codigo_do_cadastro_sem_zeros_a_esquerda(self) -> None:
        ClientCompany.objects.filter(pk=self.company.pk).update(dominio_code="0101")

        assert agent.resolve_dominio_codi_emp(ClientCompany.objects.get(pk=self.company.pk)) == 101

    def test_perfil_erp_e_cadastro_concordando(self) -> None:
        CompanyErpProfile.objects.create(
            organization=self.office, empresa=self.company, codi_emp=25, papel=[]
        )

        assert agent.resolve_dominio_codi_emp(self.company) == 25

    def test_perfil_erp_divergente_do_cadastro_e_recusado(self) -> None:
        CompanyErpProfile.objects.create(
            organization=self.office, empresa=self.company, codi_emp=99, papel=[]
        )

        with self.assertRaises(services.CrosscheckError) as erro:
            agent.resolve_dominio_codi_emp(self.company)
        assert erro.exception.code == "codi_emp"

    def test_outra_empresa_com_o_mesmo_codigo_normalizado_e_recusada(self) -> None:
        ClientCompany.objects.create(organization=self.office, name="Gêmea", dominio_code="025")

        with self.assertRaises(services.CrosscheckError):
            agent.resolve_dominio_codi_emp(self.company)

    def test_sem_codigo_ou_com_codigo_nao_numerico_e_recusado(self) -> None:
        sem = ClientCompany.objects.create(organization=self.office, name="Sem código")
        letras = ClientCompany.objects.create(
            organization=self.office, name="Com letras", dominio_code="A25"
        )

        for empresa in (sem, letras):
            with self.assertRaises(services.CrosscheckError):
                agent.resolve_dominio_codi_emp(empresa)

    def test_nunca_deduz_do_cnpj(self) -> None:
        ClientCompany.objects.filter(pk=self.company.pk).update(dominio_code="")

        with self.assertRaises(services.CrosscheckError):
            agent.resolve_dominio_codi_emp(ClientCompany.objects.get(pk=self.company.pk))


class PedidoTests(AgentCase):
    def test_fonte_agente_exige_o_sinalizador(self) -> None:
        with self.assertRaises(services.CrosscheckError):
            self.uf_draft()

    @LIGADO
    def test_pedido_leva_so_o_contrato_na_ordem_do_manifesto(self) -> None:
        _run, job = self.requested()

        definicao = load_catalog().get("dominio", agent.DATASET_CODE)
        assert job.state == CrosscheckAgentJob.State.QUEUED
        assert job.dataset_code == "fiscal_counterparts"
        assert job.query_sha256 == definicao.query_sha256
        assert [p["name"] for p in job.parameters] == [p.name for p in definicao.parameters]
        assert [p["odbc_type"] for p in job.parameters] == [
            p.odbc_type for p in definicao.parameters
        ]
        valores = {p["name"]: p["value"] for p in job.parameters}
        assert valores["codi_emp_sai"] == valores["codi_emp_ent"] == 25
        assert valores["start_sai"] == "2026-08-01"
        assert valores["end_sai"] == "2026-10-31"
        assert job.row_limit == definicao.max_rows_per_run

    @LIGADO
    def test_janela_de_dezembro_e_janeiro_atravessa_o_ano(self) -> None:
        assert agent._window(date(2026, 12, 1)) == (date(2026, 11, 1), date(2027, 1, 31))
        assert agent._window(date(2027, 1, 1)) == (date(2026, 12, 1), date(2027, 2, 28))

    @LIGADO
    def test_segundo_pedido_com_o_primeiro_ativo_e_recusado(self) -> None:
        run, _ = self.requested()

        with self.assertRaises(services.CrosscheckError) as erro:
            agent.request_agent_job(run, actor=self.user)
        assert erro.exception.code == "active"

    @LIGADO
    def test_sem_conector_habilitado_nao_pede(self) -> None:
        Connector.objects.update(enabled=False)

        with self.assertRaises(services.CrosscheckError):
            agent.request_agent_job(self.uf_draft(), actor=self.user)

    @LIGADO
    def test_pedido_audita_sem_dado_pessoal(self) -> None:
        run, job = self.requested()

        evento = AuditEvent.objects.get(action="crosscheck.agent.requested")
        assert evento.metadata == {
            "run_id": str(run.id),
            "tool": UF_DOMINIO,
            "job_id": str(job.id),
        }

    @LIGADO
    def test_conferencia_por_agente_recusa_arquivo_do_dominio(self) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        run = self.uf_draft()

        resultado = services.attach_files(
            run,
            "dominio",
            [SimpleUploadedFile("d.csv", b"chave;uf\n")],
            actor=self.user,
        )

        assert resultado.errors and not resultado.stored


@LIGADO
class ProtocoloTests(AgentCase):
    def test_reivindica_e_devolve_o_mesmo_trabalho_ao_mesmo_agente(self) -> None:
        _run, job = self.requested()

        primeiro = self.next().json()["job"]
        segundo = self.next().json()["job"]

        assert primeiro == segundo
        assert primeiro["id"] == str(job.id)
        assert primeiro["schema_version"] == 1
        assert primeiro["page_size"] == 500
        assert len(primeiro["parameters"]) == 6
        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.CLAIMED
        assert job.claimed_by == str(self.agent_id)

    def test_agente_de_outro_escritorio_nao_ve_o_trabalho(self) -> None:
        self.requested()
        outro = Organization.objects.create(name="Vizinho", slug="vizinho-agente")
        Connector.objects.create(
            organization=outro, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )
        credenciais = redeem_enrollment(
            code=issue_enrollment(organization=outro).code, label="Outro", fingerprint="fp-2"
        )

        resposta = self.next(secret=credenciais.shared_secret, agent_id=credenciais.agent_id)

        assert resposta.json() == {"job": None}

    def test_sem_trabalho_devolve_nulo(self) -> None:
        assert self.next().json() == {"job": None}

    def test_pagina_aceita_repetida_e_fora_de_ordem(self) -> None:
        _run, job = self.requested()
        self.next()

        primeira = self.batch(job.id, 0, [self.row(1), self.row(2)])
        repetida = self.batch(job.id, 0, [self.row(1), self.row(2)])
        pulou = self.batch(job.id, 2, [self.row(3)])
        segunda = self.batch(job.id, 1, [self.row(3, "RJ", "S")])

        assert primeira.json() == {"status": "accepted"}
        assert repetida.json() == {"status": "duplicate"}
        assert pulou.status_code == 409
        assert segunda.json() == {"status": "accepted"}
        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.RECEIVING
        assert (job.next_sequence, job.rows_received) == (2, 3)
        assert CrosscheckDominioRow.objects.filter(job=job).count() == 3

    def test_linha_invalida_recusa_a_pagina_inteira(self) -> None:
        _run, job = self.requested()
        self.next()
        invalidas = [
            {"chave_nfe": "123", "direcao": "E", "uf": "SP"},
            {"chave_nfe": chave(1), "direcao": "X", "uf": "SP"},
            {"chave_nfe": chave(1), "direcao": "E", "uf": "ZZ"},
        ]

        for linha in invalidas:
            assert self.batch(job.id, 0, [self.row(9), linha]).status_code == 400
        assert (
            self.post(
                "agent-v2-crosscheck-batch", {"sequence": "x", "rows": []}, job.id
            ).status_code
            == 400
        )
        assert not CrosscheckDominioRow.objects.exists()

    def test_uf_vazia_e_aceita_e_repetida_na_mesma_chave_e_descartada(self) -> None:
        _run, job = self.requested()
        self.next()

        resposta = self.batch(job.id, 0, [self.row(1, ""), self.row(1, "SP")])

        assert resposta.status_code == 200
        assert CrosscheckDominioRow.objects.filter(job=job).count() == 1

    def test_teto_de_linhas_derruba_o_trabalho(self) -> None:
        _run, job = self.requested()
        self.next()
        CrosscheckAgentJob.objects.filter(pk=job.pk).update(row_limit=2)

        resposta = self.batch(job.id, 0, [self.row(1), self.row(2), self.row(3)])

        assert resposta.status_code == 413
        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.FAILED
        assert job.error_code == "row_limit"
        assert not CrosscheckDominioRow.objects.exists()

    def test_pagina_de_trabalho_alheio_ou_nao_reivindicado_e_404(self) -> None:
        _run, job = self.requested()

        assert self.batch(job.id, 0, [self.row(1)]).status_code == 404

    def test_fechamento_confere_a_contagem(self) -> None:
        _run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1), self.row(2)])

        divergente = self.complete(job.id, 3, 1)

        assert divergente.status_code == 409
        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.FAILED
        assert job.error_code == "contagem_diverge"

    def test_fechamento_correto_e_repeticao(self) -> None:
        run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1), self.row(2)])

        assert self.complete(job.id, 2, 1).json() == {"status": "completed"}
        assert self.complete(job.id, 2, 1).json() == {"status": "duplicate"}

        assert agent.rows_ready(run) is True
        assert AuditEvent.objects.filter(action="crosscheck.agent.received").count() == 1

    def test_falha_com_codigo_conhecido_e_desconhecido(self) -> None:
        _run, job = self.requested()
        self.next()

        resposta = self.post(
            "agent-v2-crosscheck-failure",
            {"error_code": "invente-um-codigo", "detail": "x" * 500},
            job.id,
        )

        assert resposta.json() == {"status": "recorded"}
        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.FAILED
        assert job.error_code == "agent_error"
        assert len(job.error_detail) == 200
        evento = AuditEvent.objects.get(action="crosscheck.agent.failed")
        assert evento.success is False

    def test_falha_conhecida_vira_mensagem_na_tela(self) -> None:
        run, job = self.requested()
        self.next()
        self.post("agent-v2-crosscheck-failure", {"error_code": "odbc_error"}, job.id)

        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))

        self.assertContains(pagina, "Falhou")
        self.assertContains(pagina, "não conseguiu consultar o Domínio")
        self.assertContains(pagina, "Consultar")

    def test_trabalho_abandonado_volta_para_outro_agente_e_recomeca_do_zero(self) -> None:
        _run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1), self.row(2)])
        CrosscheckAgentJob.objects.filter(pk=job.pk).update(
            claimed_by="agente-que-sumiu",
            last_activity_at=timezone.now() - agent.JOB_STALE_AFTER - timedelta(minutes=1),
        )

        retomado = self.next().json()["job"]

        assert retomado["id"] == str(job.id)
        job.refresh_from_db()
        assert job.claimed_by == str(self.agent_id)
        assert (job.next_sequence, job.rows_received) == (0, 0)
        assert not CrosscheckDominioRow.objects.exists()

    def test_conferencia_que_saiu_do_rascunho_expira_o_trabalho(self) -> None:
        run, job = self.requested()
        CrosscheckRun.objects.filter(pk=run.pk).update(state=CrosscheckRun.State.CANCELED)

        assert self.next().json() == {"job": None}

        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.EXPIRED


@LIGADO
class ConferenciaDePontaAPontaTests(AgentCase):
    def test_uf_do_xml_contra_o_dominio_recebido_do_agente(self) -> None:
        run = self.uf_draft()
        self.attach(
            run,
            "xml",
            zip_upload(
                nfe(1, emit_uf="SP"),
                nfe(2, emit_uf="SP"),
                nfe(3, emit_uf="MG"),
            ),
        )
        job = agent.request_agent_job(run, actor=self.user)
        self.next()
        self.batch(job.id, 0, [self.row(1, "SP"), self.row(2, "RJ")])
        self.complete(job.id, 2, 1)

        # O terceiro XML não está no Domínio: a conferência roda e o reporta.
        with self.captureOnCommitCallbacks(execute=True):
            resposta = self.client.post(reverse("crosscheck:run-start", args=[run.id]))
        assert resposta.status_code == 302

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.DONE
        achados = {
            (item.kind, item.number, item.left_text, item.right_text) for item in run.findings.all()
        }
        assert ("uf_divergente", "2", "SP", "RJ") in achados
        assert any(kind == "ausente_dominio" and numero == "3" for kind, numero, *_ in achados)
        assert run.matched_count == 1

    def test_sem_o_dominio_recebido_a_conferencia_nao_comeca(self) -> None:
        run = self.uf_draft()
        self.attach(run, "xml", zip_upload(nfe(1)))

        with self.assertRaises(services.CrosscheckError) as erro:
            services.start_run(run, actor=self.user)

        assert "O agente ainda não trouxe o Domínio." in erro.exception.messages

    def test_resultado_do_agente_nunca_reaproveita_resultado_antigo(self) -> None:
        primeira = self.uf_draft()
        segunda = self.uf_draft()
        for run in (primeira, segunda):
            self.attach(run, "xml", zip_upload(nfe(1)))
            job = agent.request_agent_job(run, actor=self.user)
            CrosscheckAgentJob.objects.filter(pk=job.pk).update(
                state=CrosscheckAgentJob.State.SUCCEEDED
            )
            CrosscheckDominioRow.objects.create(
                run=run, job=job, chave=chave(1), direcao="E", uf="SP"
            )
        services.start_run(primeira, actor=self.user, dispatch=False)
        services.process_run(str(primeira.id))
        primeira.refresh_from_db()
        assert primeira.state == CrosscheckRun.State.DONE

        _, reaproveitada = services.start_run(segunda, actor=self.user, dispatch=False)

        assert reaproveitada is False


@LIGADO
class TelaDoAgenteTests(AgentCase):
    def test_tela_oferece_consultar_e_enviar_arquivo(self) -> None:
        run = self.uf_draft()

        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))

        self.assertContains(pagina, "Consultar")
        self.assertContains(pagina, "Enviar arquivo")
        self.assertContains(pagina, "Sem consulta")

    def test_consultar_enfileira_e_mostra_o_estado(self) -> None:
        run = self.uf_draft()

        resposta = self.client.post(reverse("crosscheck:run-agent-request", args=[run.id]))

        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[run.id]))
        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))
        self.assertContains(pagina, "Na fila")
        self.assertContains(pagina, "data-agent-block")
        corpo = self.client.get(reverse("crosscheck:run-status", args=[run.id])).json()
        assert corpo["agent"]["state"] == "queued"

    def test_recebido_mostra_a_contagem_de_chaves(self) -> None:
        run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1), self.row(2)])
        self.complete(job.id, 2, 1)

        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))

        self.assertContains(pagina, "Recebido")
        self.assertContains(pagina, "2 chaves")

    def test_saida_para_arquivo_descarta_a_consulta_e_mostra_o_envio(self) -> None:
        run, job = self.requested()

        self.client.post(reverse("crosscheck:run-agent-file", args=[run.id]))

        run.refresh_from_db()
        job.refresh_from_db()
        assert run.options["dominio_source"] == "arquivo"
        assert job.state == CrosscheckAgentJob.State.EXPIRED
        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))
        self.assertContains(pagina, 'id="file-dominio"')

    def test_pedido_com_sinalizador_desligado_e_recusado_com_mensagem(self) -> None:
        run = self.uf_draft()

        with self.settings(CONTRAPROVA_AGENT_ENABLED=False):
            resposta = self.client.post(reverse("crosscheck:run-agent-request", args=[run.id]))

        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[run.id]))
        assert not CrosscheckAgentJob.objects.exists()

    def test_papel_so_de_leitura_nao_consulta(self) -> None:
        from apps.hub.models import CompanyAccessGrant
        from apps.organizations.models import Membership

        run = self.uf_draft()
        auditor = self.member(Membership.Role.AUDITOR, "aud-agente@example.com")
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=Membership.objects.get(user=auditor),
            company=self.company,
            modules=["crosscheck"],
            capabilities=["read"],
        )

        resposta = self.login(auditor).post(reverse("crosscheck:run-agent-request", args=[run.id]))

        assert resposta.status_code == 403
        assert not CrosscheckAgentJob.objects.exists()


@LIGADO
class ExpiracaoETempoTests(AgentCase):
    def test_pedido_que_ninguem_pegou_expira_e_o_recuperador_roda(self) -> None:
        _run, job = self.requested()
        CrosscheckAgentJob.objects.filter(pk=job.pk).update(
            created_at=timezone.now() - agent.JOB_STALE_AFTER - timedelta(minutes=1)
        )

        recover_runs()

        job.refresh_from_db()
        assert job.state == CrosscheckAgentJob.State.EXPIRED
        assert job.error_code == "expirado"

    def test_agente_calado_por_uma_hora_expira(self) -> None:
        _run, job = self.requested()
        self.next()
        CrosscheckAgentJob.objects.filter(pk=job.pk).update(
            last_activity_at=timezone.now() - 5 * agent.JOB_STALE_AFTER
        )

        assert agent.expire_stale_jobs() == 1

    def test_linhas_do_agente_somem_junto_com_as_entradas(self) -> None:
        run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1)])
        self.complete(job.id, 1, 1)
        CrosscheckRun.objects.filter(pk=run.pk).update(
            state=CrosscheckRun.State.FAILED,
            finished_at=timezone.now() - timedelta(days=2),
        )

        retention.purge_inputs()

        assert not CrosscheckDominioRow.objects.exists()
        run.refresh_from_db()
        assert run.inputs_purged_at is not None

    def test_leitor_de_linhas_pagina_por_id(self) -> None:
        run, job = self.requested()
        CrosscheckDominioRow.objects.bulk_create(
            [
                CrosscheckDominioRow(run=run, job=job, chave=chave(n), direcao="E", uf="SP")
                for n in range(1, 8)
            ]
        )

        linhas = list(agent.iter_rows(run))

        assert [item.key for item in linhas] == [chave(n) for n in range(1, 8)]
