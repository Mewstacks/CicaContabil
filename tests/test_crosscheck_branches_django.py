"""Ramos de recusa e de erro do Contraprova que os fluxos felizes não alcançam.

Cada teste aqui prova uma recusa com motivo (nunca um 500) ou uma proteção de borda: limite de
tamanho, duplicata, arquivo que mente sobre o tipo, perda de arrendamento, papel só de leitura,
módulo desligado em cada rota, falha ao apagar objeto, payload inválido do agente.
"""

from __future__ import annotations

import io
import uuid
from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from apps.crosscheck import agent, limits, retention, services
from apps.crosscheck.engine.tools import UF_DOMINIO
from apps.crosscheck.forms import NewRunForm
from apps.crosscheck.models import (
    CrosscheckAgentJob,
    CrosscheckDominioRow,
    CrosscheckFinding,
    CrosscheckInput,
    CrosscheckRun,
)
from apps.crosscheck.synthetic import build_nfe_xml, build_zip
from apps.crosscheck.templatetags import crosscheck_extras as extras
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership, Organization
from crosscheck_support import (
    EMPRESA,
    AgentCase,
    CrosscheckCase,
    doc,
    nfe,
    sped_upload,
    xml_upload,
    zip_upload,
)


class ModelosTests(CrosscheckCase):
    def test_representacoes_propriedades_e_problemas(self) -> None:
        run = self.draft()
        self.attach(run, "sped", sped_upload([doc(1)]))
        item = run.inputs.get()
        achado = CrosscheckFinding(
            run=run, seq=1, kind="sem_xml", status="divergent", doc_key="1" * 44
        )
        run.problems = [{"severity": "error", "message": "x"}, "lixo", {"severity": "warning"}]

        assert str(run) == "sped_xml 2026-09 draft"
        assert run.tool_def.code == "sped_xml"
        assert run.is_active is False
        assert str(item) == "sped:sped.txt"
        assert str(achado) == "sem_xml 111111111111"
        assert achado.delta_cents is None
        assert len(run.problem_messages()) == 2
        assert run.problem_messages("error") == [{"severity": "error", "message": "x"}]

    def test_clean_recusa_empresa_alheia_competencia_quebrada_e_arquivo_alheio(self) -> None:
        outro = Organization.objects.create(name="Outro", slug="outro-modelos")
        alheia = ClientCompany.objects.create(organization=outro, name="Alheia")
        run = self.draft()
        run.company = alheia
        with self.assertRaises(ValidationError):
            run.clean()
        run.company = self.company
        run.competence = date(2026, 9, 15)
        with self.assertRaises(ValidationError):
            run.clean()
        run.competence = date(2026, 9, 1)
        item = CrosscheckInput(organization=outro, run=run, role="sped", kind="efd")
        with self.assertRaises(ValidationError):
            item.clean()

    def test_job_e_linha_do_agente(self) -> None:
        run = self.draft()
        job = CrosscheckAgentJob(
            organization=self.office, run=run, dataset_code="fiscal_counterparts", state="queued"
        )
        linha = CrosscheckDominioRow(run=run, chave="1" * 44, direcao="E", uf="SP")

        assert str(job) == "fiscal_counterparts queued"
        assert job.is_active is True
        assert str(linha) == "E 111111111111 SP"


class CriacaoDeRascunhoTests(CrosscheckCase):
    def _criar(self, **mudancas: object) -> CrosscheckRun:
        dados: dict[str, object] = {
            "organization": self.office,
            "company": self.company,
            "tool": "sped_xml",
            "competence": date(2026, 9, 1),
            "options": {},
            "actor": self.user,
        }
        dados.update(mudancas)
        return services.create_draft(**dados)  # type: ignore[arg-type]

    def test_recusas(self) -> None:
        outro = Organization.objects.create(name="Outro", slug="outro-rascunho")
        alheia = ClientCompany.objects.create(organization=outro, name="Alheia")
        for mudanca in (
            {"tool": "inventada"},
            {"company": alheia},
            {"competence": date(1999, 1, 1)},
            {"options": {"tolerance_cents": "abc"}},
            {"options": {"dominio_source": "nuvem"}},
        ):
            with self.assertRaises(services.CrosscheckError):
                self._criar(**mudanca)
        assert not CrosscheckRun.objects.exists()

    def test_cnpj_invalido_no_cadastro_vira_vazio(self) -> None:
        ClientCompany.objects.filter(pk=self.company.pk).update(cnpj_masked="123")

        assert services.company_document(ClientCompany.objects.get(pk=self.company.pk)) == ""

    def test_quem_pediu_sumiu_nao_esta_autorizado(self) -> None:
        run = self.draft()
        run.created_by = None

        assert services.requester_still_authorized(run) is False

    def test_competencia_vazia_no_formulario(self) -> None:
        form = NewRunForm(
            {"tool": "sped_xml", "company": str(self.company.id), "competence": ""},
            companies=ClientCompany.objects.all(),
        )

        assert not form.is_valid()
        assert "competence" in form.errors


class ValidacaoDeArquivosTests(CrosscheckCase):
    def setUp(self) -> None:
        super().setUp()
        self.run = self.draft()
        self.uf = self.draft(UF_DOMINIO)

    def _enviar(self, role: str, *arquivos: SimpleUploadedFile, run: CrosscheckRun | None = None):
        return services.attach_files(run or self.run, role, list(arquivos), actor=self.user)

    def test_sem_arquivo_e_papel_inexistente(self) -> None:
        with self.assertRaises(services.CrosscheckError):
            self._enviar("sped")
        with self.assertRaises(services.CrosscheckError):
            self._enviar("nao-existe", sped_upload([doc(1)]))

    def test_sped_sem_9999_entra_com_aviso(self) -> None:
        resultado = self._enviar("sped", sped_upload([doc(1)], omit_trailer=True))

        assert any("9999" in aviso for aviso in resultado.stored[0].detected["avisos"])
        assert any(item.severity == "warning" for item in services.readiness(self.run))

    def test_tetos_de_tamanho_e_de_conjunto(self) -> None:
        with mock.patch.object(limits, "MAX_SPED_BYTES", 10):
            assert self._enviar("sped", sped_upload([doc(1)])).errors
        with mock.patch.object(limits, "MAX_RUN_BYTES", 10):
            assert self._enviar("sped", sped_upload([doc(1)])).errors
        with mock.patch.object(limits, "MAX_ZIP_BYTES", 10):
            assert self._enviar("xml", zip_upload(nfe(1))).errors
        assert self._enviar("xml", SimpleUploadedFile("vazio.zip", b"")).errors
        assert not CrosscheckInput.objects.exists()

    def test_zip_que_mente_e_zip_so_com_texto(self) -> None:
        corrompido = SimpleUploadedFile("c.zip", b"PK\x03\x04" + b"lixo" * 20)
        misto = SimpleUploadedFile(
            "m.zip", build_zip({"a.xml": build_nfe_xml(nfe(1)), "leia.txt": b"oi"})
        )

        assert self._enviar("xml", corrompido).errors
        resultado = self._enviar("xml", misto)

        assert resultado.stored and "não são XML" in resultado.stored[0].detected["avisos"][0]

    def test_zip_repetido_e_acima_do_limite_de_xml(self) -> None:
        conteudo = zip_upload(nfe(1), nfe(2)).read()
        assert self._enviar("xml", SimpleUploadedFile("a.zip", conteudo)).stored
        assert (
            "já foi enviado" in self._enviar("xml", SimpleUploadedFile("b.zip", conteudo)).errors[0]
        )
        with mock.patch.object(limits, "MAX_XML_PER_RUN", 2):
            assert self._enviar("xml", zip_upload(nfe(7), name="c.zip")).errors

    def test_xml_soltos_limites_e_repeticao(self) -> None:
        with mock.patch.object(limits, "MAX_LOOSE_XML_PER_REQUEST", 1):
            assert self._enviar("xml", xml_upload(nfe(1)), xml_upload(nfe(2))).errors
        with mock.patch.object(limits, "MAX_XML_BYTES", 10):
            assert self._enviar("xml", xml_upload(nfe(1))).errors
        with mock.patch.object(limits, "MAX_LOOSE_XML_BYTES_PER_REQUEST", 100):
            assert self._enviar("xml", xml_upload(nfe(1)), xml_upload(nfe(2))).errors
        with mock.patch.object(limits, "MAX_XML_PER_RUN", 1):
            assert self._enviar("xml", xml_upload(nfe(1)), xml_upload(nfe(2))).errors
        with mock.patch("zipfile.time.localtime", return_value=(2026, 9, 1, 0, 0, 0, 0, 0, 0)):
            assert self._enviar("xml", xml_upload(nfe(3))).stored
            repetida = self._enviar("xml", xml_upload(nfe(3)))
        assert "já foi enviada" in repetida.errors[0]

    def test_papel_dominio_aceita_csv_e_xlsx_e_recusa_o_resto(self) -> None:
        planilha = io.BytesIO()
        livro = Workbook()
        livro.active.append(["chave", "uf"])
        livro.save(planilha)
        sem_workbook = build_zip({"a.txt": b"x"})
        invalidos = [
            SimpleUploadedFile("d.pdf", b"%PDF"),
            SimpleUploadedFile("d.xlsx", b"nao sou zip"),
            SimpleUploadedFile("d.xlsx", b"PK\x03\x04" + b"lixo" * 10),
            SimpleUploadedFile("d.xlsx", sem_workbook),
            SimpleUploadedFile("d.csv", b"chave;uf\x00\n"),
            SimpleUploadedFile("d2.csv", sem_workbook),
        ]

        for arquivo in invalidos:
            assert self._enviar("dominio", arquivo, run=self.uf).errors, arquivo.name
        csv = self._enviar("dominio", SimpleUploadedFile("ok.csv", b"chave;uf\n"), run=self.uf)
        assert csv.stored[0].detected == {"formato": "csv"}
        self.uf.inputs.all().delete()
        xlsx = self._enviar(
            "dominio", SimpleUploadedFile("ok.xlsx", planilha.getvalue()), run=self.uf
        )
        assert xlsx.stored[0].detected == {"formato": "xlsx"}

    def test_readiness_do_limite_de_xml_e_remocao_com_recusas(self) -> None:
        self._enviar("xml", zip_upload(nfe(1), nfe(2)))
        with mock.patch.object(limits, "MAX_XML_PER_RUN", 1):
            assert any(
                i.severity == "error" and "XML na conferência" in i.message
                for i in services.readiness(self.run)
            )
        with self.assertRaises(services.CrosscheckError) as erro:
            services.remove_input(self.run, uuid.uuid4(), actor=self.user)
        assert erro.exception.code == "not_found"
        CrosscheckRun.objects.filter(pk=self.run.pk).update(state=CrosscheckRun.State.QUEUED)
        with self.assertRaises(services.CrosscheckError):
            services.remove_input(self.run, uuid.uuid4(), actor=self.user)
        with self.assertRaises(services.CrosscheckError):
            services.start_run(self.run, actor=self.user)

    def test_remover_entrada_sem_objeto_nao_quebra(self) -> None:
        item = CrosscheckInput.objects.create(
            organization=self.office,
            run=self.run,
            role="sped",
            kind="efd",
            original_name="x.txt",
            size_bytes=1,
            sha256="a" * 64,
        )

        services.remove_input(self.run, item.id, actor=self.user)

        assert not CrosscheckInput.objects.exists()


class RepetirEExecucaoTests(CrosscheckCase):
    def test_repetir_exige_conferencia_terminada_e_arquivos_com_objeto(self) -> None:
        run = self.ready_run()
        CrosscheckRun.objects.filter(pk=run.pk).update(state=CrosscheckRun.State.PROCESSING)
        run.refresh_from_db()
        with self.assertRaises(services.CrosscheckError):
            services.repeat_run(run, options=None, actor=self.user)

        CrosscheckRun.objects.filter(pk=run.pk).update(state=CrosscheckRun.State.FAILED)
        CrosscheckInput.objects.filter(run=run).update(content="")
        run.refresh_from_db()
        with self.assertRaises(services.CrosscheckError) as erro:
            services.repeat_run(run, options=None, actor=self.user)
        assert erro.exception.code == "purged"
        assert CrosscheckRun.objects.count() == 1

    def test_sink_grava_em_lotes_e_respeita_a_cadencia(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user, dispatch=False)
        with mock.patch.object(services, "_FLUSH_EVERY", 1):
            services.process_run(str(run.id))
        run.refresh_from_db()
        assert run.findings.count() == 3

        sink = services.RunSink(run.id, uuid.uuid4(), mock.Mock())
        sink._stage = "Lendo XML"
        sink._last_progress = 10**12
        assert sink.progress("Lendo XML", 2, 2) is None
        sink._cancel = True
        assert sink.cancelled() is True
        sink._cancel = False
        sink._last_cancel_check = 10**12
        assert sink.cancelled() is False

    def test_trabalho_assumido_por_outro_sai_sem_mexer(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user, dispatch=False)

        with mock.patch.object(services, "_execute", side_effect=services.LeaseLost):
            assert services.process_run(str(run.id)) == "superseded"

    def test_arquivo_ja_purgado_recusa_com_motivo(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user, dispatch=False)
        CrosscheckInput.objects.filter(run=run).update(purged_at=timezone.now())

        assert services.process_run(str(run.id)) == "rejected"

        run.refresh_from_db()
        assert run.error_code == "arquivo_ausente"

    def test_perder_o_arrendamento_no_fim_apaga_o_relatorio_orfao(self) -> None:
        run = self.ready_run()
        services.start_run(run, actor=self.user, dispatch=False)
        real = services.run_tool

        def perde(*args: object, **kwargs: object):
            saida = real(*args, **kwargs)
            CrosscheckRun.objects.filter(pk=run.pk).update(lease_token=None)
            return saida

        with mock.patch.object(services, "run_tool", perde):
            assert services.process_run(str(run.id)) == "superseded"

        run.refresh_from_db()
        assert not run.result_file
        assert run.state == CrosscheckRun.State.PROCESSING


class TelasEmCadaRotaTests(CrosscheckCase):
    def _todas(self, run: CrosscheckRun) -> list[tuple[str, str]]:
        arg = [run.id]
        return [
            ("get", reverse("crosscheck:index")),
            ("get", reverse("crosscheck:new-run")),
            ("get", reverse("crosscheck:dominio-template")),
            ("get", reverse("crosscheck:run-detail", args=arg)),
            ("get", reverse("crosscheck:run-status", args=arg)),
            ("get", reverse("crosscheck:run-download", args=[run.id, "xlsx"])),
            ("post", reverse("crosscheck:run-attach", args=arg)),
            ("post", reverse("crosscheck:run-remove", args=[run.id, uuid.uuid4()])),
            ("post", reverse("crosscheck:run-start", args=arg)),
            ("post", reverse("crosscheck:run-cancel", args=arg)),
            ("post", reverse("crosscheck:run-repeat", args=arg)),
            ("post", reverse("crosscheck:run-agent-request", args=arg)),
            ("post", reverse("crosscheck:run-agent-file", args=arg)),
        ]

    def test_modulo_desligado_recusa_toda_rota(self) -> None:
        run = self.draft()
        ProductModule.objects.filter(code=ProductModule.Code.CROSSCHECK).update(enabled=False)

        for metodo, url in self._todas(run):
            assert getattr(self.client, metodo)(url).status_code == 403, url

    def test_papel_so_de_leitura_nao_escreve_em_nenhuma_rota(self) -> None:
        run = self.draft()
        auditor = self.member(Membership.Role.AUDITOR, "aud-rotas@example.com")
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=Membership.objects.get(user=auditor),
            company=self.company,
            modules=["crosscheck"],
            capabilities=["read"],
        )
        cliente = self.login(auditor)

        for metodo, url in self._todas(run):
            if metodo == "post":
                assert getattr(cliente, metodo)(url).status_code == 403, url

    def test_modelo_do_dominio_e_filtros_da_lista(self) -> None:
        self.draft()
        CrosscheckRun.objects.update(state=CrosscheckRun.State.DONE, divergent_count=2)

        modelo = self.client.get(reverse("crosscheck:dominio-template"))
        with_div = self.client.get(reverse("crosscheck:index"), {"situacao": "divergencia"})
        andamento = self.client.get(reverse("crosscheck:index"), {"situacao": "andamento"})

        assert modelo.content.decode("utf-8").startswith(chr(0xFEFF) + "chave;uf;direcao")
        assert "attachment" in modelo["Content-Disposition"]
        self.assertContains(with_div, "Padaria Central")
        self.assertContains(andamento, "Nenhuma conferência encontrada")

    def test_erros_de_servico_viram_mensagem_e_redirecionam(self) -> None:
        run = self.draft()
        feita = self.ready_run()
        CrosscheckRun.objects.filter(pk=feita.pk).update(state=CrosscheckRun.State.DONE)
        casos = [
            ("crosscheck:run-remove", [run.id, uuid.uuid4()], {}),
            ("crosscheck:run-start", [run.id], {}),
            ("crosscheck:run-cancel", [feita.id], {}),
            ("crosscheck:run-repeat", [run.id], {"operation": "A", "tolerance_cents": "2"}),
            ("crosscheck:run-agent-request", [run.id], {}),
            ("crosscheck:run-agent-file", [feita.id], {}),
        ]

        for nome, args, dados in casos:
            resposta = self.client.post(reverse(nome, args=args), dados)
            assert resposta.status_code == 302, nome

    def test_nova_conferencia_com_erro_de_servico_volta_com_o_motivo(self) -> None:
        dados = {
            "tool": "sped_xml",
            "company": str(self.company.id),
            "competence": "2026-09",
            "fields_xml": ["vnf"],
        }
        with mock.patch(
            "apps.crosscheck.services.create_draft",
            side_effect=services.CrosscheckError("Motivo do serviço"),
        ):
            resposta = self.client.post(reverse("crosscheck:new-run"), dados)

        self.assertContains(resposta, "Motivo do serviço")

    def test_txt_corta_em_cinco_mil_e_avisa(self) -> None:
        run = self.ready_run()
        with self.captureOnCommitCallbacks(execute=True):
            services.start_run(run, actor=self.user)
        run.refresh_from_db()
        CrosscheckFinding.objects.bulk_create(
            [
                CrosscheckFinding(
                    run=run,
                    seq=1000 + n,
                    kind="valor_divergente",
                    status="divergent",
                    number=str(n),
                    doc_key=f"{n:044d}",
                )
                for n in range(5001)
            ]
        )

        corpo = self.client.get(
            reverse("crosscheck:run-download", args=[run.id, "txt"]), {"aba": "divergencias"}
        ).content.decode("utf-8")

        assert "Mostrando 5000 de" in corpo

    def test_filtro_por_cfop_na_consulta(self) -> None:
        run = self.ready_run()
        with self.captureOnCommitCallbacks(execute=True):
            services.start_run(run, actor=self.user)

        pagina = self.client.get(reverse("crosscheck:run-detail", args=[run.id]), {"cfop": "9999"})

        self.assertContains(pagina, "Nenhum achado com esse filtro")


class FiltrosDeExibicaoTests(CrosscheckCase):
    def test_valores_e_rotulos(self) -> None:
        assert extras.cents(None) == "" and extras.cents(12345) == "123,45"
        assert extras.signed_cents(None) == "" and extras.signed_cents(5) == "+0,05"
        assert extras.signed_cents(-5) == "-0,05"
        assert extras.kind_label("sem_xml") == "Sem XML" and extras.kind_label("x") == "x"
        assert extras.status_label("ignored") == "Ignorada por regra"
        assert extras.bytes_label(2 * 1024 * 1024) == "2,0 MiB" and extras.bytes_label(0) == "1 KiB"
        assert extras.short_key("1234567890") == "1234 5678 90"
        assert extras.cnpj_mask(EMPRESA).count(".") == 2 and extras.cnpj_mask("1") == "1"

    def test_detalhe_organiza_fatos_c190_e_icms_por_cfop(self) -> None:
        visao = extras.detail_view(
            {
                "source": "n.xml",
                "arquivo": 2,
                "vezes": 3,
                "reason": "cfop_sem_credito",
                "sped_vazio": True,
                "cred_sn": 150,
                "emit_doc": "123",
                "emit_uf": "SP",
                "c190": [
                    {
                        "cst": "000",
                        "cfop": "1102",
                        "aliq": 180000,
                        "vl_opr": 100,
                        "vl_bc_icms": 100,
                        "vl_icms": 18,
                        "vl_ipi": 0,
                    },
                    "lixo",
                ],
                "icms_por_cfop": {"2102": 5, "1102": 18},
            }
        )

        rotulos = dict(visao["facts"])
        assert rotulos["Arquivo"] == "SPED 2" and rotulos["Motivo"] == "CFOP sem direito a crédito"
        assert rotulos["Crédito do Simples"] == "1,50" and rotulos["Emitente"] == "123 · SP"
        assert visao["c190"][0]["aliq"] == "18,00"
        assert [c for c, _ in visao["by_cfop"]] == ["1102", "2102"]
        assert extras.detail_view(None) == {"facts": [], "c190": [], "by_cfop": []}


class RetencaoRamosTests(CrosscheckCase):
    def test_apagar_sem_nome_nao_faz_nada_e_falha_ao_expirar_e_tolerada(self) -> None:
        retention._delete_object("")
        run = self.ready_run()
        with self.captureOnCommitCallbacks(execute=True):
            services.start_run(run, actor=self.user)
        CrosscheckRun.objects.filter(pk=run.pk).update(
            results_expire_at=timezone.now() - limits.INPUT_RETENTION
        )

        with mock.patch.object(retention, "crosscheck_storage") as storage:
            storage.return_value.delete.side_effect = OSError("indisponível")
            assert retention.expire_results() == {"runs": 0}

        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.DONE


class AgentePayloadsInvalidosTests(AgentCase):
    def raw(self, name: str, corpo: bytes, *args: object) -> object:
        import hashlib
        import hmac

        timestamp = str(int(timezone.now().timestamp()))
        assinatura = hmac.new(
            self.secret.encode(), timestamp.encode() + b"." + corpo, hashlib.sha256
        ).hexdigest()
        return self.agent_client.post(
            reverse(name, args=args),
            data=corpo,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": str(self.agent_id),
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": assinatura,
            },
        )

    @override_settings(CONTRAPROVA_AGENT_ENABLED=True)
    def test_corpo_que_nao_e_objeto_json_e_recusado_em_toda_rota(self) -> None:
        _run, job = self.requested()
        self.next()
        for nome, args in (
            ("agent-v2-crosscheck-next", ()),
            ("agent-v2-crosscheck-batch", (job.id,)),
            ("agent-v2-crosscheck-complete", (job.id,)),
            ("agent-v2-crosscheck-failure", (job.id,)),
        ):
            assert self.raw(nome, b"[1]", *args).status_code == 400, nome  # type: ignore[attr-defined]
        assert (
            self.raw(
                "agent-v2-crosscheck-complete", b'{"row_count": "x", "pages": 1}', job.id
            ).status_code
            == 400
        )  # type: ignore[attr-defined]

    @override_settings(CONTRAPROVA_AGENT_ENABLED=True)
    def test_trabalho_alheio_fechado_ou_repetido(self) -> None:
        _run, job = self.requested()
        desconhecido = uuid.uuid4()

        assert self.batch(desconhecido, 0, []).status_code == 404
        assert self.complete(desconhecido, 0, 0).status_code == 404
        assert self.post("agent-v2-crosscheck-failure", {}, desconhecido).status_code == 404

        self.next()
        self.post("agent-v2-crosscheck-failure", {"error_code": "odbc_error"}, job.id)
        assert self.batch(job.id, 0, [self.row(1)]).status_code == 409
        assert self.complete(job.id, 0, 0).status_code == 409
        assert self.post("agent-v2-crosscheck-failure", {}, job.id).json() == {
            "status": "duplicate"
        }

    @override_settings(CONTRAPROVA_AGENT_ENABLED=True)
    def test_agente_que_volta_a_pedir_no_meio_da_entrega_recomeca(self) -> None:
        _run, job = self.requested()
        self.next()
        self.batch(job.id, 0, [self.row(1)])

        self.next()

        job.refresh_from_db()
        assert (job.next_sequence, job.rows_received, job.state) == (0, 0, "claimed")
        assert not CrosscheckDominioRow.objects.exists()

    @override_settings(CONTRAPROVA_AGENT_ENABLED=True)
    def test_regras_do_pedido(self) -> None:
        comum = self.draft()
        with self.assertRaises(services.CrosscheckError):
            agent.request_agent_job(comum, actor=self.user)
        run, _ = self.requested()
        CrosscheckRun.objects.filter(pk=run.pk).update(state=CrosscheckRun.State.CANCELED)
        run.refresh_from_db()
        with self.assertRaises(services.CrosscheckError):
            agent.request_agent_job(run, actor=self.user)
        with self.assertRaises(services.CrosscheckError):
            agent.switch_to_file(run, actor=self.user)


class ComandoDeDemonstracaoTests(CrosscheckCase):
    @override_settings(DEBUG=True)
    def test_cria_conferencias_em_todos_os_estados_e_nao_repete(self) -> None:
        ClientCompany.objects.create(organization=self.office, name="Segunda", dominio_code="26")
        ClientCompany.objects.create(organization=self.office, name="Terceira", dominio_code="27")

        call_command(
            "seed_crosscheck", organization=self.office.slug, user=self.user.email, verbosity=0
        )

        estados = set(CrosscheckRun.objects.values_list("state", flat=True))
        assert {"done", "failed", "draft", "queued", "processing", "canceled"} <= estados
        assert CrosscheckRun.objects.count() == 10
        assert CrosscheckRun.objects.filter(state="done", divergent_count=0).exists()
        total = CrosscheckRun.objects.count()
        call_command(
            "seed_crosscheck", organization=self.office.slug, user=self.user.email, verbosity=0
        )
        assert CrosscheckRun.objects.count() == total

    @override_settings(DEBUG=True)
    def test_recusas(self) -> None:
        with self.assertRaises(CommandError):
            call_command("seed_crosscheck", organization="nao-existe", user=self.user.email)
        vazio = Organization.objects.create(name="Vazio", slug="vazio-seed")
        with self.assertRaises(CommandError):
            call_command("seed_crosscheck", organization=vazio.slug, user=self.user.email)

    @override_settings(DEBUG=False)
    def test_nao_roda_sem_debug(self) -> None:
        with self.assertRaises(CommandError):
            call_command("seed_crosscheck", organization=self.office.slug, user=self.user.email)
