"""Ciclo de vida de uma conferência do Contraprova, de ponta a ponta com arquivos sintéticos.

Cobre a fila (`on_commit`), o arrendamento, o recuperador, o cancelamento, as falhas com motivo,
o corte de achados no banco, o resultado na tela, os downloads e a retenção de D-302.
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from io import BytesIO
from unittest import mock

from celery.exceptions import SoftTimeLimitExceeded
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.audit.models import AuditEvent
from apps.crosscheck import limits, retention, services
from apps.crosscheck.engine.findings import DIVERGENT, IGNORED, RunCancelled
from apps.crosscheck.engine.report import XlsxReport
from apps.crosscheck.engine.tools import SPED_XML, TOOLS
from apps.crosscheck.models import CrosscheckFinding, CrosscheckInput, CrosscheckRun
from apps.crosscheck.tasks import purge_expired_task, recover_runs
from apps.organizations.models import Membership
from crosscheck_support import (
    EMPRESA,
    CrosscheckCase,
    doc,
    nfe,
    sped_upload,
    zip_upload,
)


class CicloTests(CrosscheckCase):
    def _conferir(self, run: CrosscheckRun) -> CrosscheckRun:
        with self.captureOnCommitCallbacks(execute=True):
            resposta = self.client.post(reverse("crosscheck:run-start", args=[run.id]))
        assert resposta.status_code == 302
        run.refresh_from_db()
        return run

    def test_conferir_sem_arquivos_recusa_com_o_que_falta(self) -> None:
        run = self.draft()

        with self.assertRaises(services.CrosscheckError) as erro:
            services.start_run(run, actor=self.user)

        assert erro.exception.code == "not_ready"
        assert "Falta o arquivo: SPED." in erro.exception.messages
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.DRAFT

    def test_ciclo_completo_gera_achados_relatorio_e_auditoria(self) -> None:
        run = self.ready_run()

        run = self._conferir(run)

        assert run.state == CrosscheckRun.State.DONE
        assert run.divergent_count == 3
        assert run.ignored_count == 0
        assert run.matched_count == 1
        assert run.finding_count == 3
        assert not run.findings_truncated
        assert run.finished_at is not None
        assert run.results_expire_at is not None
        assert run.results_expire_at - run.finished_at == limits.RESULT_RETENTION
        assert run.lease_token is None
        assert run.attempts == 1
        kinds = set(CrosscheckFinding.objects.filter(run=run).values_list("kind", flat=True))
        assert kinds == {"valor_divergente", "sem_xml", "xml_nao_escriturado"}
        assert run.summary["by_kind"] == {
            "valor_divergente:divergent": 1,
            "sem_xml:divergent": 1,
            "xml_nao_escriturado:divergent": 1,
        }
        valor = CrosscheckFinding.objects.get(run=run, kind="valor_divergente")
        assert (valor.field, valor.left_cents, valor.right_cents) == ("vnf", 20000, 15000)
        assert valor.delta_cents == 5000
        assert valor.number == "2"
        acoes = set(AuditEvent.objects.values_list("action", flat=True))
        assert {"crosscheck.run.created", "crosscheck.run.queued", "crosscheck.run.done"} <= acoes

    def test_relatorio_xlsx_traz_todas_as_folhas(self) -> None:
        run = self._conferir(self.ready_run())

        with run.result_file.open("rb") as arquivo:
            livro = load_workbook(BytesIO(arquivo.read()), read_only=True)

        assert set(livro.sheetnames) == {
            "Divergências",
            "Só no SPED",
            "Só no XML",
            "Ignoradas",
            "Conferem",
            "Resumo",
        }
        linhas = list(livro["Divergências"].iter_rows(values_only=True))
        assert linhas[0][0] == "Chave"
        assert len(linhas) == 2
        assert run.result_size > 0
        assert len(run.result_sha256) == 64

    def test_auditoria_nunca_leva_cnpj_nome_ou_arquivo(self) -> None:
        self._conferir(self.ready_run())

        texto = " ".join(
            str(evento.metadata)
            for evento in AuditEvent.objects.filter(action__startswith="crosscheck.")
        )
        for proibido in (EMPRESA, "Padaria", "sped.txt", "notas.zip"):
            assert proibido not in texto

    def test_resultado_identico_e_reaproveitado_e_o_rascunho_some(self) -> None:
        primeira = self._conferir(self.ready_run())
        repetida = self.ready_run()
        arquivos = [item.content.name for item in repetida.inputs.all()]

        resposta = self.client.post(reverse("crosscheck:run-start", args=[repetida.id]))

        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[primeira.id]))
        assert not CrosscheckRun.objects.filter(pk=repetida.pk).exists()
        assert CrosscheckRun.objects.filter(state=CrosscheckRun.State.DONE).count() == 1
        assert all(not os.path.exists(self.storage_path(nome)) for nome in arquivos)

    def test_regras_diferentes_nao_reaproveitam(self) -> None:
        primeira = self._conferir(self.ready_run())
        outra = self.ready_run()
        outra.rules_snapshot = {**outra.rules_snapshot, "tolerance_cents": 500}
        outra.save()

        _, reaproveitada = services.start_run(outra, actor=self.user)

        assert reaproveitada is False
        assert CrosscheckRun.objects.exclude(pk=primeira.pk).filter(state="queued").exists()

    def test_impressao_digital_muda_com_o_motor(self) -> None:
        run = self.ready_run()
        antes = services.inputs_fingerprint(run)

        with mock.patch.object(limits, "ENGINE_VERSION", limits.ENGINE_VERSION + 1):
            depois = services.inputs_fingerprint(run)

        assert antes != depois

    def storage_path(self, nome: str) -> str:
        from apps.crosscheck.models import crosscheck_storage

        return crosscheck_storage().path(nome)

    def test_no_maximo_duas_conferencias_ativas_por_escritorio(self) -> None:
        for _ in range(limits.MAX_ACTIVE_RUNS_PER_OFFICE):
            ativa = self.ready_run()
            CrosscheckRun.objects.filter(pk=ativa.pk).update(state=CrosscheckRun.State.QUEUED)
        terceira = self.draft()
        self.attach(terceira, "sped", sped_upload([doc(9)], name="outro.txt"))
        self.attach(terceira, "xml", zip_upload(nfe(9), name="outro.zip"))

        with self.assertRaises(services.CrosscheckError) as erro:
            services.start_run(terceira, actor=self.user)

        assert erro.exception.code == "busy"

    def test_cancelar_na_fila_encerra_na_hora_e_o_worker_nao_executa(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.QUEUED

        self.client.post(reverse("crosscheck:run-cancel", args=[run.id]))
        run.refresh_from_db()

        assert run.state == CrosscheckRun.State.CANCELED
        assert run.finished_at is not None
        assert services.process_run(str(run.id)) == "not_queued"
        assert not run.findings.exists()

    def test_cancelar_rascunho_volta_para_a_lista(self) -> None:
        run = self.draft()

        resposta = self.client.post(reverse("crosscheck:run-cancel", args=[run.id]))

        self.assertRedirects(resposta, reverse("crosscheck:index"))
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.CANCELED

    def test_cancelamento_pedido_antes_do_worker_pegar(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)
        CrosscheckRun.objects.filter(pk=run.pk).update(cancel_requested_at=timezone.now())

        assert services.process_run(str(run.id)) == "canceled"

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.CANCELED

    def test_cancelar_em_execucao_so_marca_o_pedido(self) -> None:
        run = self.ready_run()
        CrosscheckRun.objects.filter(pk=run.pk).update(
            state=CrosscheckRun.State.PROCESSING,
            lease_token="11111111-1111-1111-1111-111111111111",
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        run.refresh_from_db()

        services.cancel_run(run, actor=self.user)
        run.refresh_from_db()

        assert run.state == CrosscheckRun.State.PROCESSING
        assert run.cancel_requested_at is not None

    def test_cancelar_conferencia_terminada_e_recusado(self) -> None:
        run = self._conferir(self.ready_run())

        with self.assertRaises(services.CrosscheckError):
            services.cancel_run(run, actor=self.user)

    def test_worker_percebe_o_cancelamento_e_a_perda_do_arrendamento(self) -> None:
        run = self.ready_run()
        token = "22222222-2222-2222-2222-222222222222"
        CrosscheckRun.objects.filter(pk=run.pk).update(
            state=CrosscheckRun.State.PROCESSING,
            lease_token=token,
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        relatorio = XlsxReport(TOOLS[SPED_XML], "t")
        self.addCleanup(relatorio.abort)
        sink = services.RunSink(run.id, uuid.UUID(token), relatorio)

        assert sink.cancelled() is False
        CrosscheckRun.objects.filter(pk=run.pk).update(cancel_requested_at=timezone.now())
        sink._last_cancel_check = 0.0
        assert sink.cancelled() is True

        CrosscheckRun.objects.filter(pk=run.pk).update(lease_token=None)
        sink._cancel = False
        sink._last_cancel_check = 0.0
        with self.assertRaises(services.LeaseLost):
            sink.cancelled()
        with self.assertRaises(services.LeaseLost):
            sink.progress("Comparando", 1, 10)

    def test_run_cancelled_do_motor_vira_cancelada_e_apaga_o_parcial(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)

        with mock.patch.object(services, "run_tool", side_effect=RunCancelled):
            resultado = services.process_run(str(run.id))

        run.refresh_from_db()
        assert resultado == "canceled"
        assert run.state == CrosscheckRun.State.CANCELED
        assert run.lease_token is None
        assert AuditEvent.objects.filter(action="crosscheck.run.canceled").exists()

    def test_lease_vencido_e_retomado_e_lease_ativo_fica_ocupado(self) -> None:
        run = self.ready_run()
        CrosscheckRun.objects.filter(pk=run.pk).update(
            state=CrosscheckRun.State.PROCESSING,
            lease_token="33333333-3333-3333-3333-333333333333",
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        assert services.process_run(str(run.id)) == "busy"

        CrosscheckRun.objects.filter(pk=run.pk).update(
            lease_until=timezone.now() - timedelta(minutes=1)
        )
        assert services.process_run(str(run.id)) == "done"

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.DONE
        assert run.attempts == 1

    def test_reentrega_da_tarefa_depois_de_pronta_nao_refaz(self) -> None:
        run = self._conferir(self.ready_run())
        achados = run.findings.count()

        assert services.process_run(str(run.id)) == "not_queued"
        assert services.process_run("nao-e-uuid") == "invalid_id"
        assert services.process_run("00000000-0000-0000-0000-000000000000") == "missing"

        assert run.findings.count() == achados

    def test_reprocessar_apaga_achados_parciais(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)
        CrosscheckFinding.objects.create(run=run, seq=99, kind="sem_xml", status=DIVERGENT)

        services.process_run(str(run.id))

        run.refresh_from_db()
        assert run.finding_count == 3
        assert run.findings.count() == 3
        assert not run.findings.filter(seq=99).exists()

    def test_tentativas_esgotadas_falham_com_motivo(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)
        CrosscheckRun.objects.filter(pk=run.pk).update(attempts=limits.MAX_ATTEMPTS)

        assert services.process_run(str(run.id)) == "attempts"

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.FAILED
        assert run.error_code == "tentativas"

    def test_acesso_revogado_falha_sem_ler_arquivo(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)
        Membership.objects.filter(user=self.user).update(is_active=False)

        assert services.process_run(str(run.id)) == "access_revoked"

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.FAILED
        assert run.error_code == "access_revoked"
        assert not run.findings.exists()

    def test_motor_recusa_e_a_tela_mostra_o_motivo(self) -> None:
        run = self.draft()
        # Entradas postas direto, sem passar pela validação do envio: SPED de outra empresa.
        from crosscheck_support import OUTRA

        for papel, arquivo in (
            ("sped", sped_upload([doc(1)], cnpj=OUTRA)),
            ("xml", zip_upload(nfe(1))),
        ):
            item = CrosscheckInput(
                organization=self.office,
                run=run,
                role=papel,
                kind="efd" if papel == "sped" else "xml",
                original_name=arquivo.name,
                size_bytes=arquivo.size,
                sha256=papel,
            )
            item.content.save(arquivo.name, arquivo, save=False)
            item.save()
        services.start_run(run, actor=self.user)

        assert services.process_run(str(run.id)) == "rejected"

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.FAILED
        assert run.error_code == "empresa_diferente"
        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))
        self.assertContains(pagina, "Não foi possível conferir")
        self.assertContains(pagina, "não é o da empresa escolhida")
        self.assertContains(pagina, "Corrigir")

    def test_arquivo_apagado_do_armazenamento_falha_com_motivo(self) -> None:
        run = self.ready_run()
        for item in run.inputs.all():
            os.remove(item.content.path)
        services.start_run(run, actor=self.user)

        assert services.process_run(str(run.id)) == "rejected"

        run.refresh_from_db()
        assert run.error_code == "arquivo_ausente"

    def test_erro_inesperado_marca_falha_audita_e_relanca(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)

        with (
            mock.patch.object(services, "run_tool", side_effect=RuntimeError("segredo interno")),
            self.assertRaises(RuntimeError),
        ):
            services.process_run(str(run.id))

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.FAILED
        assert run.error_code == "inesperado"
        assert "segredo interno" not in str(run.problems)
        evento = AuditEvent.objects.get(action="crosscheck.run.failed")
        assert evento.success is False

    def test_estouro_de_tempo_falha_com_motivo(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)

        with mock.patch.object(services, "run_tool", side_effect=SoftTimeLimitExceeded):
            assert services.process_run(str(run.id)) == "timeout"

        run.refresh_from_db()
        assert run.error_code == "tempo_esgotado"

    def test_banco_guarda_so_o_teto_e_a_contagem_continua_certa(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user)

        with mock.patch.object(limits, "MAX_FINDINGS_STORED", 2):
            services.process_run(str(run.id))

        run.refresh_from_db()
        assert run.findings_truncated is True
        assert run.findings.count() == 2
        assert run.finding_count == 3
        assert run.divergent_count == 3
        with run.result_file.open("rb") as arquivo:
            livro = load_workbook(BytesIO(arquivo.read()), read_only=True)
        total = sum(
            len(list(livro[nome].iter_rows(values_only=True))) - 1
            for nome in ("Divergências", "Só no SPED", "Só no XML")
        )
        assert total == 3
        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))
        self.assertContains(pagina, "Limite de 50.000 achados na tela")

    def test_recuperador_reenfileira_lease_vencido_e_fila_esquecida(self) -> None:
        travada = self.ready_run()
        CrosscheckRun.objects.filter(pk=travada.pk).update(
            state=CrosscheckRun.State.PROCESSING,
            lease_token="44444444-4444-4444-4444-444444444444",
            lease_until=timezone.now() - timedelta(minutes=1),
        )
        esquecida = self.ready_run()
        services.start_run(esquecida, actor=self.user)
        CrosscheckRun.objects.filter(pk=esquecida.pk).update(
            queued_at=timezone.now() - limits.QUEUE_RECOVERY_AFTER - timedelta(minutes=1)
        )
        recente = self.ready_run()
        CrosscheckRun.objects.filter(pk=recente.pk).update(
            state=CrosscheckRun.State.QUEUED, queued_at=timezone.now()
        )

        with self.captureOnCommitCallbacks(execute=True):
            total = recover_runs()

        assert total == 2
        travada.refresh_from_db()
        esquecida.refresh_from_db()
        recente.refresh_from_db()
        assert travada.state == CrosscheckRun.State.DONE
        assert esquecida.state == CrosscheckRun.State.DONE
        assert recente.state == CrosscheckRun.State.QUEUED

    def test_painel_conta_so_conferencias_com_divergencia_dos_ultimos_30_dias(self) -> None:
        run = self._conferir(self.ready_run())
        companies = self.office.clientcompany_set.all()

        assert services.runs_needing_attention(self.office, companies) == 1

        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - timedelta(days=31)
        )
        assert services.runs_needing_attention(self.office, companies) == 0

    def test_painel_inicial_mostra_o_bloco_do_modulo(self) -> None:
        self._conferir(self.ready_run())

        pagina = self.client.get(reverse("hub:dashboard"))

        self.assertContains(pagina, "Contraprova")
        self.assertContains(pagina, reverse("crosscheck:index"))


class ResultadoTests(CrosscheckCase):
    def setUp(self) -> None:
        super().setUp()
        self.run = self.ready_run()
        with self.captureOnCommitCallbacks(execute=True):
            services.start_run(self.run, actor=self.user)
        self.run.refresh_from_db()
        self.url = reverse("crosscheck:run-detail", args=[self.run.id])

    def test_tela_traz_totais_abas_com_contagem_e_valores_formatados(self) -> None:
        pagina = self.client.get(self.url)

        assert pagina.status_code == 200
        self.assertContains(pagina, "Divergências")
        self.assertContains(pagina, "Só no SPED")
        self.assertContains(pagina, "Só no XML")
        self.assertContains(pagina, "Valor diferente")
        self.assertContains(pagina, "200,00")
        self.assertContains(pagina, "150,00")
        self.assertContains(pagina, "+50,00")
        self.assertContains(pagina, reverse("crosscheck:run-download", args=[self.run.id, "xlsx"]))

    def test_cada_aba_mostra_so_o_seu_tipo(self) -> None:
        so_sped = self.client.get(self.url, {"aba": "so_sped"})
        so_xml = self.client.get(self.url, {"aba": "so_xml"})

        self.assertContains(so_sped, "Sem XML")
        self.assertNotContains(so_sped, "Valor diferente")
        self.assertContains(so_xml, "XML sem escrituração")
        self.assertNotContains(so_xml, "Valor diferente")

    def test_aba_desconhecida_cai_na_primeira(self) -> None:
        pagina = self.client.get(self.url, {"aba": "inexistente"})

        assert pagina.status_code == 200
        self.assertContains(pagina, "Valor diferente")

    def test_busca_por_numero_e_por_chave(self) -> None:
        por_numero = self.client.get(self.url, {"q": "2"})
        sem_resultado = self.client.get(self.url, {"q": "999999"})

        self.assertContains(por_numero, "Valor diferente")
        self.assertContains(sem_resultado, "Nenhum achado com esse filtro")
        self.assertContains(sem_resultado, "Limpar")

    def test_filtro_por_campo_e_operacao(self) -> None:
        com_campo = self.client.get(self.url, {"campo": "vnf"})
        outro_campo = self.client.get(self.url, {"campo": "vicms"})
        saidas = self.client.get(self.url, {"operacao": "S"})

        self.assertContains(com_campo, "Valor diferente")
        self.assertContains(outro_campo, "Nenhum achado com esse filtro")
        self.assertContains(saidas, "Nenhum achado com esse filtro")

    def test_texto_de_achado_e_escapado(self) -> None:
        CrosscheckFinding.objects.filter(run=self.run).update(
            message="<script>alert(1)</script>", field_label="<b>x</b>"
        )

        pagina = self.client.get(self.url)

        self.assertNotContains(pagina, "<script>alert(1)</script>")
        self.assertContains(pagina, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_achado_ignorado_aparece_so_na_aba_de_ignoradas_com_rotulo(self) -> None:
        achado = CrosscheckFinding.objects.get(run=self.run, kind="valor_divergente")
        CrosscheckFinding.objects.filter(pk=achado.pk).update(status=IGNORED)
        CrosscheckRun.objects.filter(pk=self.run.pk).update(
            summary={**self.run.summary, "by_kind": {"valor_divergente:ignored": 1}}
        )

        divergencias = self.client.get(self.url)
        ignoradas = self.client.get(self.url, {"aba": "ignoradas"})

        self.assertNotContains(divergencias, "Ignorada por regra")
        self.assertContains(ignoradas, "Ignorada por regra")
        self.assertContains(ignoradas, "Valor diferente")

    def test_paginacao_dos_achados(self) -> None:
        for numero in range(60):
            CrosscheckFinding.objects.create(
                run=self.run,
                seq=1000 + numero,
                kind="sem_xml",
                status=DIVERGENT,
                number=str(numero),
                doc_key=f"{numero:044d}",
            )

        pagina = self.client.get(self.url, {"aba": "so_sped"})

        self.assertContains(pagina, "Página 1 de 2")
        self.assertContains(
            self.client.get(self.url, {"aba": "so_sped", "pagina": 2}), "Página 2 de 2"
        )

    def test_status_json_nao_e_guardado_em_cache(self) -> None:
        resposta = self.client.get(reverse("crosscheck:run-status", args=[self.run.id]))

        corpo = resposta.json()
        assert corpo["state"] == "done"
        assert corpo["terminal"] is True
        assert "no-store" in resposta["Cache-Control"]

    def test_resultado_expirado_mostra_estado_com_saida(self) -> None:
        CrosscheckRun.objects.filter(pk=self.run.pk).update(
            state=CrosscheckRun.State.EXPIRED, result_file=""
        )

        pagina = self.client.get(self.url)

        self.assertContains(pagina, "Resultado apagado")
        self.assertContains(pagina, "Nova conferência")

    # -- downloads ---------------------------------------------------------------------
    def _baixar(self, formato: str, **query: str) -> tuple[object, bytes]:
        resposta = self.client.get(
            reverse("crosscheck:run-download", args=[self.run.id, formato]), query
        )
        corpo = (
            b"".join(resposta.streaming_content)
            if getattr(resposta, "streaming", False)
            else resposta.content
        )
        return resposta, corpo

    def test_download_xlsx_e_anexo_sem_cache_e_sem_adivinhar_tipo(self) -> None:
        resposta, corpo = self._baixar("xlsx")

        assert resposta.status_code == 200  # type: ignore[attr-defined]
        assert "attachment" in resposta["Content-Disposition"]  # type: ignore[index]
        assert ".xlsx" in resposta["Content-Disposition"]  # type: ignore[index]
        assert resposta["X-Content-Type-Options"] == "nosniff"  # type: ignore[index]
        assert "no-store" in resposta["Cache-Control"]  # type: ignore[index]
        assert corpo[:2] == b"PK"
        assert load_workbook(BytesIO(corpo), read_only=True).sheetnames

    def test_download_csv_da_aba_tem_bom_cabecalho_e_linhas(self) -> None:
        resposta, corpo = self._baixar("csv", aba="divergencias")

        assert resposta.status_code == 200  # type: ignore[attr-defined]
        texto = corpo.decode("utf-8")
        assert texto.startswith("﻿Chave;")
        linhas = texto.strip().split("\r\n")
        assert len(linhas) == 2
        assert ";200.00;150.00;50.00;" in linhas[1]

    def test_csv_neutraliza_formula(self) -> None:
        CrosscheckFinding.objects.filter(run=self.run, kind="valor_divergente").update(
            number='=HYPERLINK("http://x")', message="+cmd|' /C calc'!A0"
        )

        _, corpo = self._baixar("csv", aba="divergencias")

        texto = corpo.decode("utf-8")
        assert ";=HYPERLINK" not in texto
        assert ";+cmd" not in texto
        assert "'=HYPERLINK" in texto

    def test_download_txt_da_aba(self) -> None:
        resposta, corpo = self._baixar("txt", aba="so_sped")

        assert resposta.status_code == 200  # type: ignore[attr-defined]
        assert resposta["Content-Type"].startswith("text/plain")  # type: ignore[index]
        assert "Número: 3" in corpo.decode("utf-8")

    def test_formato_desconhecido_e_resultado_inexistente_sao_404(self) -> None:
        assert self._baixar("pdf")[0].status_code == 404  # type: ignore[attr-defined]
        CrosscheckRun.objects.filter(pk=self.run.pk).update(result_file="")
        assert self._baixar("xlsx")[0].status_code == 404  # type: ignore[attr-defined]

    def test_download_gera_auditoria(self) -> None:
        self._baixar("xlsx")

        evento = AuditEvent.objects.get(action="crosscheck.run.downloaded")
        assert evento.metadata["format"] == "xlsx"

    def test_download_de_outro_escritorio_e_404(self) -> None:
        from apps.organizations.models import Organization

        outro = Organization.objects.create(name="Vizinho", slug="vizinho")
        vizinho = self.member(Membership.Role.OWNER, "viz@example.com", office=outro)
        from apps.hub.models import ProductModule

        ProductModule.objects.create(
            organization=outro, code=ProductModule.Code.CROSSCHECK, enabled=True
        )

        resposta = self.login(vizinho, outro).get(
            reverse("crosscheck:run-download", args=[self.run.id, "xlsx"])
        )

        assert resposta.status_code == 404

    def test_repetir_cria_rascunho_com_os_mesmos_arquivos_e_outra_tolerancia(self) -> None:
        resposta = self.client.post(
            reverse("crosscheck:run-repeat", args=[self.run.id]), {"tolerance_cents": "50"}
        )

        novo = CrosscheckRun.objects.exclude(pk=self.run.pk).get()
        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[novo.id]))
        assert novo.state == CrosscheckRun.State.DRAFT
        assert novo.rules_snapshot["tolerance_cents"] == 50
        assert novo.inputs.count() == self.run.inputs.count()
        assert {i.sha256 for i in novo.inputs.all()} == {i.sha256 for i in self.run.inputs.all()}
        assert services.inputs_fingerprint(novo) != self.run.inputs_fingerprint


class RetencaoTests(CrosscheckCase):
    def _concluida(self) -> CrosscheckRun:
        run = self.ready_run()
        with self.captureOnCommitCallbacks(execute=True):
            services.start_run(run, actor=self.user)
        run.refresh_from_db()
        return run

    def _caminhos(self, run: CrosscheckRun) -> list[str]:
        return [item.content.path for item in run.inputs.all() if item.content.name]

    def test_entradas_somem_24h_depois_do_fim_e_antes_disso_ficam(self) -> None:
        run = self._concluida()
        caminhos = self._caminhos(run)
        assert caminhos and all(os.path.exists(c) for c in caminhos)
        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - limits.INPUT_RETENTION + timedelta(minutes=5)
        )

        assert retention.purge_inputs()["runs"] == 0
        assert all(os.path.exists(c) for c in caminhos)

        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - limits.INPUT_RETENTION - timedelta(minutes=5)
        )
        resultado = retention.purge_inputs()

        assert resultado == {"runs": 1, "files": 2, "drafts_expired": 0}
        assert not any(os.path.exists(c) for c in caminhos)
        run.refresh_from_db()
        assert run.inputs_purged_at is not None
        assert run.inputs_available is False
        for item in run.inputs.all():
            assert item.purged_at is not None
            assert not item.content.name
            assert len(item.sha256) == 64
        assert retention.purge_inputs()["runs"] == 0

    def test_resultado_e_achados_somem_em_90_dias_e_o_cabecalho_fica(self) -> None:
        run = self._concluida()
        arquivo = run.result_file.path
        CrosscheckRun.objects.filter(pk=run.pk).update(
            results_expire_at=timezone.now() - timedelta(minutes=1)
        )

        resultado = retention.expire_results()

        assert resultado == {"runs": 1}
        assert not os.path.exists(arquivo)
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.EXPIRED
        assert not run.result_file
        assert not run.findings.exists()
        assert run.divergent_count == 3
        assert run.result_sha256
        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))
        self.assertContains(pagina, "Resultado apagado")

    def test_rascunho_parado_expira_em_72h_e_apaga_os_arquivos(self) -> None:
        run = self.ready_run()
        caminhos = self._caminhos(run)
        CrosscheckRun.objects.filter(pk=run.pk).update(
            updated_at=timezone.now() - limits.DRAFT_RETENTION - timedelta(minutes=1)
        )

        resultado = retention.purge_inputs()

        assert resultado["drafts_expired"] == 1
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.EXPIRED
        assert not any(os.path.exists(c) for c in caminhos)

    def test_arquivo_compartilhado_so_e_apagado_quando_o_ultimo_usuario_sai(self) -> None:
        original = self._concluida()
        copia = services.repeat_run(original, options=None, actor=self.user)
        caminhos = self._caminhos(original)
        assert caminhos == self._caminhos(copia) or set(caminhos) == set(self._caminhos(copia))
        CrosscheckRun.objects.filter(pk=original.pk).update(
            finished_at=timezone.now() - timedelta(days=2)
        )

        retention.purge_inputs()

        assert all(os.path.exists(c) for c in caminhos)
        CrosscheckRun.objects.filter(pk=copia.pk).update(
            updated_at=timezone.now() - timedelta(days=5)
        )
        retention.purge_inputs()
        assert not any(os.path.exists(c) for c in caminhos)

    def test_repetir_depois_da_purga_pede_novo_envio(self) -> None:
        run = self._concluida()
        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - timedelta(days=2)
        )
        retention.purge_inputs()
        run.refresh_from_db()

        with self.assertRaises(services.CrosscheckError) as erro:
            services.repeat_run(run, options=None, actor=self.user)
        assert erro.exception.code == "purged"
        resposta = self.client.post(reverse("crosscheck:run-repeat", args=[run.id]))
        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[run.id]))

    def test_tarefa_diaria_e_o_recuperador_estao_no_beat(self) -> None:
        from django.conf import settings

        tarefas = {item["task"] for item in settings.CELERY_BEAT_SCHEDULE.values()}

        assert {"crosscheck.purge_expired", "crosscheck.recover_runs"} <= tarefas
        assert purge_expired_task() == {
            "runs_inputs": 0,
            "files": 0,
            "drafts_expired": 0,
            "runs_results": 0,
        }

    def test_purga_audita_sem_dado_pessoal(self) -> None:
        run = self._concluida()
        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - timedelta(days=2)
        )

        retention.purge_inputs()

        evento = AuditEvent.objects.get(action="crosscheck.run.inputs_purged")
        assert evento.metadata == {"run_id": str(run.id), "tool": SPED_XML, "file_count": 2}

    def test_falha_ao_apagar_objeto_nao_marca_a_entrada_como_purgada(self) -> None:
        run = self._concluida()
        CrosscheckRun.objects.filter(pk=run.pk).update(
            finished_at=timezone.now() - timedelta(days=2)
        )

        with mock.patch.object(retention, "_delete_object", side_effect=OSError("indisponível")):
            retention.purge_inputs()

        run.refresh_from_db()
        assert run.inputs_purged_at is None
        assert run.inputs.filter(purged_at__isnull=True).count() == 2
        assert CrosscheckInput.objects.filter(run=run).count() == 2
