"""O módulo Contraprova nas telas: registro, portões, nova conferência e envio de arquivos.

Prova que a tela obedece às mesmas recusas dos outros módulos (módulo desligado, colaborador
sem o módulo, carteira restrita, escritório vizinho, papel só de leitura) e que o envio recusa
o que não presta antes de gravar: empresa trocada, arquivo que não é EFD, duplicata, ZIP sem
XML, XML solto que não é XML.
"""

from __future__ import annotations

import importlib
from datetime import timedelta

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.crosscheck.engine.tools import ICMS51, SPED_SPED, SPED_XML, UF_DOMINIO
from apps.crosscheck.models import CrosscheckInput, CrosscheckRun
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.hub.module_catalog import (
    MODULES,
    NOT_SELF_SERVICE_MODULE_CODES,
    OFFERED_MODULE_CODES,
    definition,
    self_service_module_codes,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import SupportSession
from crosscheck_support import (
    EMPRESA,
    OUTRA,
    CrosscheckCase,
    doc,
    mask,
    nfe,
    sped_upload,
    xml_upload,
    zip_upload,
)

URL = "/app/contraprova/"


class CatalogoTests(TestCase):
    def test_modulo_no_catalogo_e_fora_do_cadastro_automatico(self) -> None:
        modulo = definition(ProductModule.Code.CROSSCHECK)

        assert modulo.label == "Contraprova"
        assert ProductModule.Code.CROSSCHECK in MODULES
        assert ProductModule.Code.CROSSCHECK in OFFERED_MODULE_CODES
        assert ProductModule.Code.CROSSCHECK in NOT_SELF_SERVICE_MODULE_CODES
        assert ProductModule.Code.CROSSCHECK not in self_service_module_codes()

    def test_rota_do_catalogo_resolve(self) -> None:
        assert reverse(definition(ProductModule.Code.CROSSCHECK).route_name) == URL

    def test_demonstracao_nao_abre_o_modulo(self) -> None:
        from apps.hub.seeding import ensure_office

        office = ensure_office(name="Demo", slug="demo-contraprova", enable_modules=True)

        assert not ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.CROSSCHECK
        ).exists()


class MigracaoDeDadosTests(TestCase):
    """O código novo precisa de linha desabilitada: sem ela o escritório só-NFS-e deixa de sê-lo."""

    def test_escritorio_com_linhas_ganha_a_nova_desabilitada_e_o_sem_linhas_nao(self) -> None:
        modulo = importlib.import_module("apps.hub.migrations.0077_crosscheck_module_rows")
        configurado = Organization.objects.create(name="Configurado", slug="configurado")
        legado = Organization.objects.create(name="Legado", slug="legado")
        ProductModule.objects.create(
            organization=configurado, code=ProductModule.Code.NFSE, enabled=True
        )

        modulo.add_disabled_rows(django_apps, None)
        modulo.add_disabled_rows(django_apps, None)

        novo = ProductModule.objects.filter(organization=configurado, code="crosscheck")
        assert novo.count() == 1
        assert novo.get().enabled is False
        assert not ProductModule.objects.filter(organization=legado).exists()

    def test_escritorio_so_nfse_continua_so_nfse(self) -> None:
        from apps.hub.views import workspace_context

        office = Organization.objects.create(name="Só NFS-e", slug="so-nfse")
        for code in OFFERED_MODULE_CODES:
            if code != ProductModule.Code.CROSSCHECK:
                ProductModule.objects.create(
                    organization=office, code=code, enabled=code == ProductModule.Code.NFSE
                )
        importlib.import_module(
            "apps.hub.migrations.0077_crosscheck_module_rows"
        ).add_disabled_rows(django_apps, None)
        user = Membership.objects.create(
            organization=office,
            user=__import__("apps.accounts.models", fromlist=["User"]).User.objects.create_user(
                email="n@example.com", password="uma-senha-longa"
            ),
            role=Membership.Role.OWNER,
        ).user
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = user
        request.session = {"hub_organization_id": str(office.id)}

        assert workspace_context(request)["is_nfse_only_subscription"] is True


class PortaoTests(CrosscheckCase):
    def test_anonimo_vai_para_o_login(self) -> None:
        resposta = self.client_class().get(URL)

        assert resposta.status_code == 302
        assert resposta["Location"].startswith(reverse("hub:login"))

    def test_modulo_desligado_recusa_a_tela(self) -> None:
        ProductModule.objects.filter(code=ProductModule.Code.CROSSCHECK).update(enabled=False)

        resposta = self.client.get(URL)

        assert resposta.status_code == 403
        self.assertTemplateUsed(resposta, "hub/module_unavailable.html")

    def test_modulo_ligado_abre_a_lista_vazia_com_as_quatro_ferramentas(self) -> None:
        resposta = self.client.get(URL)

        assert resposta.status_code == 200
        self.assertTemplateUsed(resposta, "crosscheck/index.html")
        for rotulo in ("SPED x XML", "SPED x SPED", "ICMS 51", "UF x Domínio"):
            self.assertContains(resposta, rotulo)
        self.assertContains(resposta, "Nenhuma conferência")

    def test_colaborador_sem_o_modulo_no_escopo_e_recusado(self) -> None:
        colaborador = self.member(Membership.Role.OPERATOR, "op@example.com")
        vinculo = Membership.objects.get(user=colaborador)
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=vinculo,
            company=self.company,
            modules=["nfse"],
            capabilities=["read"],
        )

        resposta = self.login(colaborador).get(URL)

        assert resposta.status_code == 403

    def test_conferencia_de_outro_escritorio_e_404(self) -> None:
        outro = Organization.objects.create(name="Outro", slug="outro")
        empresa = ClientCompany.objects.create(
            organization=outro, name="Alheia", cnpj_masked=mask(OUTRA)
        )
        run = CrosscheckRun.objects.create(
            organization=outro,
            company=empresa,
            tool=SPED_XML,
            competence="2026-09-01",
            created_by=self.user,
        )

        assert self.client.get(reverse("crosscheck:run-detail", args=[run.id])).status_code == 404
        assert self.client.get(reverse("crosscheck:run-status", args=[run.id])).status_code == 404

    def test_carteira_restrita_so_enxerga_as_empresas_do_colaborador(self) -> None:
        outra = ClientCompany.objects.create(
            organization=self.office, name="Fora da carteira", cnpj_masked=mask(OUTRA)
        )
        run_fora = self.draft(company=outra)
        run_dentro = self.draft()
        colaborador = self.member(Membership.Role.OPERATOR, "carteira@example.com")
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=Membership.objects.get(user=colaborador),
            company=self.company,
            modules=["crosscheck"],
            capabilities=["read", "write"],
        )
        cliente = self.login(colaborador)

        lista = cliente.get(URL)

        self.assertContains(lista, "Padaria Central")
        self.assertNotContains(lista, "Fora da carteira")
        assert (
            cliente.get(reverse("crosscheck:run-detail", args=[run_dentro.id])).status_code == 200
        )
        assert cliente.get(reverse("crosscheck:run-detail", args=[run_fora.id])).status_code == 404

    def test_auditor_le_mas_nao_escreve(self) -> None:
        run = self.draft()
        auditor = self.member(Membership.Role.AUDITOR, "auditor@example.com")
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=Membership.objects.get(user=auditor),
            company=self.company,
            modules=["crosscheck"],
            capabilities=["read"],
        )
        cliente = self.login(auditor)

        assert cliente.get(URL).status_code == 200
        assert cliente.get(reverse("crosscheck:run-detail", args=[run.id])).status_code == 200
        assert cliente.get(reverse("crosscheck:new-run")).status_code == 403
        enviar = cliente.post(
            reverse("crosscheck:run-attach", args=[run.id]),
            {"role": "sped", "files": sped_upload([doc(1)])},
            HTTP_ACCEPT="application/json",
        )
        assert enviar.status_code == 403
        assert cliente.post(reverse("crosscheck:run-start", args=[run.id])).status_code == 403
        assert cliente.post(reverse("crosscheck:run-cancel", args=[run.id])).status_code == 403
        assert not CrosscheckInput.objects.exists()
        self.assertNotContains(cliente.get(URL), "Conferir arquivos")

    def test_post_sem_csrf_e_recusado(self) -> None:
        from django.test import Client

        run = self.draft()
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        session = cliente.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

        resposta = cliente.post(reverse("crosscheck:run-cancel", args=[run.id]))

        assert resposta.status_code == 403
        run.refresh_from_db()
        assert run.state == CrosscheckRun.State.DRAFT

    def test_suporte_somente_leitura_ve_a_tela_mas_nao_baixa_nem_escreve(self) -> None:
        suporte = self.member(
            Membership.Role.OWNER,
            "suporte@example.com",
            office=Organization.objects.create(name="Casa", slug="casa"),
        )
        sessao = SupportSession.objects.create(
            organization=self.office,
            support_user=suporte,
            justification="Verificação autorizada do módulo.",
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        cliente = self.login(suporte)
        session = cliente.session
        session["hub_support_session_id"] = str(sessao.id)
        session.save()
        run = self.draft()

        assert cliente.get(URL).status_code == 200
        assert cliente.get(reverse("crosscheck:run-detail", args=[run.id])).status_code == 200
        assert cliente.get(reverse("crosscheck:new-run")).status_code == 403
        assert cliente.post(reverse("crosscheck:run-cancel", args=[run.id])).status_code == 403
        assert (
            cliente.get(reverse("crosscheck:run-download", args=[run.id, "xlsx"])).status_code
            == 403
        )

    def test_navegacao_mostra_contraprova_no_grupo_fiscal(self) -> None:
        resposta = self.client.get(URL)

        self.assertContains(resposta, f'href="{URL}"')
        self.assertContains(resposta, "Contraprova")


class NovaConferenciaTests(CrosscheckCase):
    def _post(self, **campos: object) -> HttpResponse:
        dados = {
            "tool": SPED_XML,
            "company": str(self.company.id),
            "competence": "2026-09",
            "tolerance_cents": "1",
            "operation": "E",
            "fields_xml": ["vnf", "vicms", "vipi"],
            "no_credit_cfops": "1551, 1556",
        }
        dados.update(campos)
        return self.client.post(reverse("crosscheck:new-run"), dados)

    def test_tela_traz_as_ferramentas_e_o_formulario(self) -> None:
        resposta = self.client.get(reverse("crosscheck:new-run"))

        assert resposta.status_code == 200
        for rotulo in ("SPED x XML", "SPED x SPED", "ICMS 51", "UF x Domínio", "Tolerância"):
            self.assertContains(resposta, rotulo)
        self.assertContains(resposta, "Padaria Central")
        self.assertContains(resposta, 'type="month"')

    def test_ferramenta_pedida_na_url_vem_marcada(self) -> None:
        resposta = self.client.get(reverse("crosscheck:new-run"), {"ferramenta": ICMS51})

        self.assertContains(resposta, f'value="{ICMS51}" data-tool-input checked')

    def test_cria_rascunho_e_vai_para_a_conferencia(self) -> None:
        resposta = self._post()

        run = CrosscheckRun.objects.get()
        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[run.id]))
        assert run.state == CrosscheckRun.State.DRAFT
        assert run.competence.isoformat() == "2026-09-01"
        assert run.rules_snapshot["tolerance_cents"] == 1
        assert run.rules_snapshot["operation"] == "E"
        assert run.created_by == self.user

    def test_regras_invalidas_voltam_com_erro_e_sem_criar(self) -> None:
        resposta = self._post(tolerance_cents="5000", no_credit_cfops="15x1")

        assert resposta.status_code == 200
        self.assertContains(resposta, "Confira os campos indicados")
        assert not CrosscheckRun.objects.exists()

    def test_nenhum_campo_marcado_e_erro(self) -> None:
        resposta = self._post(fields_xml=[])

        self.assertContains(resposta, "Escolha ao menos um campo")
        assert not CrosscheckRun.objects.exists()

    def test_competencia_invalida_e_erro(self) -> None:
        resposta = self._post(competence="09/2026")

        self.assertContains(resposta, "competência")
        assert not CrosscheckRun.objects.exists()

    def test_empresa_de_outro_escritorio_nao_e_aceita(self) -> None:
        outro = Organization.objects.create(name="Outro", slug="outro-2")
        alheia = ClientCompany.objects.create(organization=outro, name="Alheia")

        resposta = self._post(company=str(alheia.id))

        assert resposta.status_code == 200
        assert not CrosscheckRun.objects.exists()

    def test_ferramenta_desconhecida_e_erro(self) -> None:
        resposta = self._post(tool="inventada")

        assert resposta.status_code == 200
        assert not CrosscheckRun.objects.exists()

    def test_cada_ferramenta_grava_so_as_regras_que_usa(self) -> None:
        self._post(tool=SPED_SPED, fields_sped=["vl_doc", "num_doc"], include_analytic="on")
        self._post(tool=ICMS51, icms51_cfops="1551, 2551")
        self._post(tool=UF_DOMINIO)

        sped, icms, uf = (
            CrosscheckRun.objects.get(tool=tool).rules_snapshot
            for tool in (SPED_SPED, ICMS51, UF_DOMINIO)
        )
        assert sped["fields"] == ["vl_doc", "num_doc"]
        assert sped["include_analytic"] is True
        assert icms["icms51_cfops"] == ["1551", "2551"]
        assert uf["tolerance_cents"] == 1

    def test_fonte_agente_so_existe_com_o_sinalizador(self) -> None:
        resposta = self.client.get(reverse("crosscheck:new-run"))
        self.assertNotContains(resposta, 'value="agente"')

        with self.settings(CONTRAPROVA_AGENT_ENABLED=True):
            com = self.client.get(reverse("crosscheck:new-run"))
        self.assertContains(com, 'value="agente"')


class EnvioDeArquivosTests(CrosscheckCase):
    def setUp(self) -> None:
        super().setUp()
        self.run = self.draft()
        self.url = reverse("crosscheck:run-attach", args=[self.run.id])

    def _enviar(self, role: str, *arquivos: SimpleUploadedFile) -> HttpResponse:
        return self.client.post(
            self.url, {"role": role, "files": list(arquivos)}, HTTP_ACCEPT="application/json"
        )

    def test_sped_valido_vira_recibo_com_o_que_o_servidor_leu(self) -> None:
        resposta = self._enviar("sped", sped_upload([doc(1)]))

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["errors"] == []
        item = CrosscheckInput.objects.get()
        assert item.kind == "efd"
        assert item.detected["cnpj"] == EMPRESA
        assert item.detected["competencia"] == "2026-09"
        assert len(item.sha256) == 64
        assert item.content.name.startswith(f"private/crosscheck/{self.office.id}/{self.run.id}/")
        assert "sped" not in item.content.name.split("/")[-1].split(".")[0]

    def test_sped_de_outra_empresa_e_recusado(self) -> None:
        resposta = self._enviar("sped", sped_upload([doc(1)], cnpj=OUTRA))

        assert resposta.status_code == 422
        assert "não é o da empresa" in resposta.json()["errors"][0]
        assert not CrosscheckInput.objects.exists()

    def test_sped_de_outro_estabelecimento_da_mesma_raiz_entra_com_aviso(self) -> None:
        from crosscheck_support import make_cnpj

        filial = make_cnpj("12345678", "0002")
        resposta = self._enviar("sped", sped_upload([doc(1)], cnpj=filial))

        assert resposta.status_code == 200
        assert "mesma empresa" in CrosscheckInput.objects.get().detected["avisos"][0]

    def test_competencia_diferente_entra_com_aviso(self) -> None:
        resposta = self._enviar("sped", sped_upload([doc(1)], dt_ini="01082026", dt_fin="31082026"))

        assert resposta.status_code == 200
        assert any(
            "Competência" in aviso for aviso in CrosscheckInput.objects.get().detected["avisos"]
        )

    def test_arquivo_que_nao_e_efd_e_recusado(self) -> None:
        falso = SimpleUploadedFile("sped.txt", b"isto nao e um sped\n", "text/plain")

        resposta = self._enviar("sped", falso)

        assert resposta.status_code == 422
        assert not CrosscheckInput.objects.exists()

    def test_extensao_errada_e_arquivo_vazio_sao_recusados(self) -> None:
        pdf = SimpleUploadedFile("sped.pdf", b"%PDF-1.4", "application/pdf")
        vazio = SimpleUploadedFile("vazio.txt", b"", "text/plain")

        assert self._enviar("sped", pdf).status_code == 422
        assert self._enviar("sped", vazio).status_code == 422

    def test_mesmo_arquivo_duas_vezes_e_recusado(self) -> None:
        conteudo = sped_upload([doc(1)]).read()
        primeiro = SimpleUploadedFile("a.txt", conteudo)
        segundo = SimpleUploadedFile("b.txt", conteudo)

        assert self._enviar("sped", primeiro).status_code == 200
        repetido = self._enviar("sped", segundo)

        assert repetido.status_code == 422
        assert "já foi enviado" in repetido.json()["errors"][0]
        assert CrosscheckInput.objects.count() == 1

    def test_limite_de_sped_por_conferencia(self) -> None:
        for numero in (1, 2, 3):
            assert (
                self._enviar("sped", sped_upload([doc(numero)], name=f"{numero}.txt")).status_code
                == 200
            )

        quarto = self._enviar("sped", sped_upload([doc(4)], name="4.txt"))

        assert quarto.status_code == 422
        assert CrosscheckInput.objects.filter(role="sped").count() == 3

    def test_zip_de_xml_conta_os_xml(self) -> None:
        resposta = self._enviar("xml", zip_upload(nfe(1), nfe(2)))

        assert resposta.status_code == 200
        item = CrosscheckInput.objects.get()
        assert item.kind == "xml"
        assert item.xml_count == 2

    def test_zip_sem_xml_e_recusado(self) -> None:
        from apps.crosscheck.synthetic import build_zip

        vazio = SimpleUploadedFile("so-texto.zip", build_zip({"leia.txt": b"oi"}))

        resposta = self._enviar("xml", vazio)

        assert resposta.status_code == 422
        assert "nenhum arquivo XML" in resposta.json()["errors"][0]

    def test_arquivo_chamado_zip_que_nao_e_zip_e_recusado(self) -> None:
        falso = SimpleUploadedFile("falso.zip", b"<xml/>")

        assert self._enviar("xml", falso).status_code == 422

    def test_xml_soltos_viram_um_zip_so(self) -> None:
        resposta = self._enviar("xml", xml_upload(nfe(1)), xml_upload(nfe(2)), xml_upload(nfe(3)))

        assert resposta.status_code == 200
        item = CrosscheckInput.objects.get()
        assert item.xml_count == 3
        assert item.original_name.endswith("soltos.zip")
        assert item.detected["soltos"] is True

    def test_xml_solto_que_nao_e_xml_recusa_a_remessa_inteira(self) -> None:
        lixo = SimpleUploadedFile("lixo.xml", b"isto nao e xml")

        resposta = self._enviar("xml", xml_upload(nfe(1)), lixo)

        assert resposta.status_code == 422
        assert not CrosscheckInput.objects.exists()

    def test_extensao_estranha_no_papel_xml_e_recusada(self) -> None:
        exe = SimpleUploadedFile("programa.exe", b"MZ")

        resposta = self._enviar("xml", exe)

        assert resposta.status_code == 422
        assert "envie XML ou ZIP" in resposta.json()["errors"][0]

    def test_papel_inexistente_na_ferramenta(self) -> None:
        resposta = self._enviar("dominio", sped_upload([doc(1)]))

        assert resposta.status_code == 422
        assert not CrosscheckInput.objects.exists()

    def test_remessa_parcial_guarda_o_bom_e_relata_o_ruim(self) -> None:
        resposta = self._enviar(
            "xml", zip_upload(nfe(1)), SimpleUploadedFile("falso.zip", b"nao sou zip")
        )

        corpo = resposta.json()
        assert resposta.status_code == 200
        assert len(corpo["stored"]) == 1
        assert len(corpo["errors"]) == 1

    def test_depois_de_enviada_a_conferencia_nao_aceita_arquivo(self) -> None:
        CrosscheckRun.objects.filter(pk=self.run.pk).update(state=CrosscheckRun.State.QUEUED)

        resposta = self._enviar("sped", sped_upload([doc(1)]))

        assert resposta.status_code == 422
        assert not CrosscheckInput.objects.exists()

    def test_remover_apaga_o_registro_e_o_objeto(self) -> None:
        self._enviar("sped", sped_upload([doc(1)]))
        item = CrosscheckInput.objects.get()
        caminho = item.content.path

        resposta = self.client.post(reverse("crosscheck:run-remove", args=[self.run.id, item.id]))

        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[self.run.id]))
        assert not CrosscheckInput.objects.exists()
        import os

        assert not os.path.exists(caminho)

    def test_nome_do_arquivo_com_html_aparece_escapado(self) -> None:
        malicioso = "<img src=x onerror=alert(1)>.txt"
        conteudo = sped_upload([doc(1)]).read()
        self._enviar("sped", SimpleUploadedFile(malicioso, conteudo))

        resposta = self.client.get(reverse("crosscheck:run-detail", args=[self.run.id]))

        self.assertNotContains(resposta, "<img src=x")
        self.assertContains(resposta, "&lt;img src=x onerror=alert(1)&gt;.txt")

    def test_envio_sem_json_volta_para_a_tela_com_mensagem(self) -> None:
        resposta = self.client.post(
            self.url, {"role": "sped", "files": SimpleUploadedFile("x.txt", b"nada")}
        )

        self.assertRedirects(resposta, reverse("crosscheck:run-detail", args=[self.run.id]))
        mensagens = [str(m) for m in resposta.wsgi_request._messages]
        assert mensagens

    def test_envio_gera_auditoria_sem_dado_pessoal(self) -> None:
        from apps.audit.models import AuditEvent

        self._enviar("sped", sped_upload([doc(1)]))

        evento = AuditEvent.objects.get(action="crosscheck.input.added")
        assert evento.metadata["role"] == "sped"
        texto = str(evento.metadata)
        assert EMPRESA not in texto
        assert "Padaria" not in texto
        assert "sped.txt" not in texto


class TelaDoRascunhoTests(CrosscheckCase):
    def test_sem_arquivos_o_botao_conferir_nasce_desabilitado_com_as_pendencias(self) -> None:
        run = self.draft()

        resposta = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))

        assert resposta.status_code == 200
        self.assertContains(resposta, "Falta o arquivo: SPED")
        self.assertContains(resposta, "Falta o arquivo: XML")
        self.assertContains(resposta, "disabled>Conferir")

    def test_com_arquivos_o_botao_conferir_habilita(self) -> None:
        run = self.ready_run()

        resposta = self.client.get(reverse("crosscheck:run-detail", args=[run.id]))

        self.assertNotContains(resposta, "Falta o arquivo")
        self.assertNotContains(resposta, "disabled>Conferir")
        self.assertContains(resposta, "sped.txt")
        self.assertContains(resposta, "3 XML")

    def test_lista_mostra_a_conferencia_e_filtra(self) -> None:
        self.draft()

        todas = self.client.get(URL)
        filtrada = self.client.get(URL, {"ferramenta": ICMS51})
        busca = self.client.get(URL, {"q": "padaria"})
        sem_resultado = self.client.get(URL, {"q": "zzzz"})

        self.assertContains(todas, "Padaria Central")
        self.assertNotContains(filtrada, "Padaria Central")
        self.assertContains(busca, "Padaria Central")
        self.assertContains(sem_resultado, "Nenhuma conferência encontrada")
        self.assertContains(sem_resultado, "Ver todas")

    def test_filtros_invalidos_na_url_sao_ignorados(self) -> None:
        self.draft()

        resposta = self.client.get(URL, {"ferramenta": "x", "situacao": "y", "pagina": "999"})

        assert resposta.status_code == 200
        self.assertContains(resposta, "Padaria Central")

    def test_paginacao_preserva_os_filtros(self) -> None:
        for _ in range(27):
            self.draft()

        pagina = self.client.get(URL, {"ferramenta": SPED_XML})

        self.assertContains(pagina, "Página 1 de 2")
        self.assertContains(pagina, "ferramenta=sped_xml")
        self.assertContains(self.client.get(URL, {"pagina": 2}), "Página 2 de 2")
