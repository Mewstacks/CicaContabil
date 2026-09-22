"""As telas do módulo: colaboradores, vínculos, horas, análises e configuração.

Cada teste ancora uma afirmação que a tela faz. As que mais importam são as de
recusa — quem pode decidir um vínculo, quem pode mudar um parâmetro de custo — e
as de honestidade: falta de dado tem de aparecer como falta de dado, e não como
um número que parece resposta.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.profitability.models import (
    Colaborador,
    ColaboradorCompetenciaMetrics,
    CompanyErpProfile,
    Competencia,
    OrigemHoras,
    ProfitabilityConfig,
    RegistroHoras,
    SalarioColaborador,
    UsuarioErp,
)
from apps.profitability.services import recompute_competencia

D = Decimal
COMPETENCIA = "2026-09"


class ScreenTestCase(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.owner = User.objects.create_user(email="dono@example.com", password="uma-senha-longa")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.PROFITABILITY, enabled=True
        )
        Competencia.objects.create(
            organization=self.office,
            competencia=COMPETENCIA,
            inicio="2026-09-01",
            fim="2026-09-30",
            is_atual=True,
        )
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria Central", dominio_code="25"
        )
        CompanyErpProfile.objects.create(
            organization=self.office,
            empresa=self.company,
            codi_emp=25,
            documento="12.345.678/0001-99",
            papel=["cliente"],
        )
        self.client = self._logar(self.owner)

    def _logar(self, user: User) -> Client:
        cliente = Client()
        cliente.force_login(user)
        sessao = cliente.session
        sessao["hub_organization_id"] = str(self.office.id)
        sessao.save()
        return cliente

    def _operador(self) -> tuple[User, Client]:
        pessoa = User.objects.create_user(
            email="operador@example.com", password="outra-senha-longa"
        )
        Membership.objects.create(
            organization=self.office, user=pessoa, role=Membership.Role.OPERATOR
        )
        return pessoa, self._logar(pessoa)

    def _pessoa(self, nome: str = "Ana Paula Velho Wolff", salario: str = "3000") -> Colaborador:
        colaborador = Colaborador.objects.create(
            organization=self.office,
            codigo="C-001",
            nome=nome,
            beneficios_mensais=D("800"),
            vt_mensal=D("300"),
        )
        SalarioColaborador.objects.create(
            organization=self.office,
            colaborador=colaborador,
            competencia=COMPETENCIA,
            salario=D(salario),
            fonte=Colaborador.Origem.MANUAL,
        )
        return colaborador

    def _horas(
        self,
        colaborador: Colaborador | None,
        usuario: UsuarioErp | None,
        minutos: int,
        marca: str = "a",
    ) -> None:
        RegistroHoras.objects.create(
            organization=self.office,
            empresa=self.company,
            colaborador=colaborador,
            usuario_erp=usuario,
            competencia=COMPETENCIA,
            data="2026-09-10",
            origem=OrigemHoras.AUTOMATICA,
            inicio="09:00",
            fim="11:30",
            duracao_minutos=minutos,
            source_content_hash=marca * 64,
        )


class ColaboradoresTests(ScreenTestCase):
    def test_a_lista_mostra_quem_trabalhou_no_mes(self) -> None:
        pessoa = self._pessoa()
        self._horas(pessoa, None, 150)
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("profitability:collaborators"))

        assert resposta.status_code == 200
        self.assertContains(resposta, "Ana Paula Velho Wolff")
        self.assertContains(resposta, "2h30")

    def test_custo_aparece_so_para_administrador(self) -> None:
        """O salário da equipe não é dado operacional."""

        pessoa = self._pessoa()
        self._horas(pessoa, None, 150)
        recompute_competencia(self.office, COMPETENCIA)
        _, operador = self._operador()

        do_dono = self.client.get(reverse("profitability:collaborators"))
        do_operador = operador.get(reverse("profitability:collaborators"))

        self.assertContains(do_dono, "Custo estimado")
        self.assertNotContains(do_operador, "Custo estimado")

    def test_login_sem_vinculo_aparece_com_as_horas_que_deixa_sem_custo(self) -> None:
        """É a maior causa isolada de margem irreal, então lidera a lista."""

        usuario = UsuarioErp.objects.create(
            organization=self.office, i_usuario="GERENTE", nome="Gerente"
        )
        self._horas(None, usuario, 240)
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("profitability:collaborators"))

        self.assertContains(resposta, "GERENTE")
        self.assertContains(resposta, "4h00")
        self.assertContains(resposta, "Sem vínculo")

    def test_administrador_grava_o_vinculo_e_as_horas_sao_reescritas(self) -> None:
        """Consertar o vínculo não conserta sozinho as horas já gravadas."""

        pessoa = self._pessoa()
        usuario = UsuarioErp.objects.create(
            organization=self.office, i_usuario="GERENTE", nome="Gerente"
        )
        self._horas(None, usuario, 240)
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.post(
            reverse("profitability:collaborators"),
            {"usuario": str(usuario.id), "colaborador": str(pessoa.id)},
        )

        assert resposta.status_code == 302
        usuario.refresh_from_db()
        assert usuario.colaborador_id == pessoa.id
        assert usuario.vinculo_manual is True
        assert RegistroHoras.objects.get(usuario_erp=usuario).colaborador_id == pessoa.id
        metrica = ColaboradorCompetenciaMetrics.objects.get(colaborador=pessoa)
        assert metrica.horas_auto_minutos == 240

    def test_operador_nao_decide_vinculo(self) -> None:
        pessoa = self._pessoa()
        usuario = UsuarioErp.objects.create(
            organization=self.office, i_usuario="GERENTE", nome="Gerente"
        )
        _, operador = self._operador()

        resposta = operador.post(
            reverse("profitability:collaborators"),
            {"usuario": str(usuario.id), "colaborador": str(pessoa.id)},
        )

        assert resposta.status_code == 403
        usuario.refresh_from_db()
        assert usuario.colaborador_id is None

    def test_o_vinculo_nao_atravessa_escritorios(self) -> None:
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        alheio = UsuarioErp.objects.create(organization=vizinho, i_usuario="ALHEIO", nome="Alheio")
        pessoa = self._pessoa()

        resposta = self.client.post(
            reverse("profitability:collaborators"),
            {"usuario": str(alheio.id), "colaborador": str(pessoa.id)},
        )

        assert resposta.status_code == 404
        alheio.refresh_from_db()
        assert alheio.colaborador_id is None


class FichaDoColaboradorTests(ScreenTestCase):
    def test_o_custo_anual_bate_com_o_vetor_do_contrato(self) -> None:
        """O valor-hora desta ficha é o mesmo que precifica a carteira inteira."""

        pessoa = self._pessoa()
        self._horas(pessoa, None, 150)
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("profitability:collaborator-detail", args=[pessoa.id]))

        assert resposta.status_code == 200
        self.assertContains(resposta, "64.690,00")
        self.assertContains(resposta, "37,09")
        self.assertContains(resposta, "46,37")
        self.assertContains(resposta, "35,0%")

    def test_pj_nao_tem_custo_anual_composto(self) -> None:
        pessoa = self._pessoa()
        pessoa.contratacao = Colaborador.Contratacao.PJ
        pessoa.save(update_fields=["contratacao"])

        resposta = self.client.get(reverse("profitability:collaborator-detail", args=[pessoa.id]))

        self.assertContains(resposta, "não tem custo anual composto")
        self.assertNotContains(resposta, "64.690,00")

    def test_operador_nao_ve_o_custo(self) -> None:
        pessoa = self._pessoa()
        _, operador = self._operador()

        resposta = operador.get(reverse("profitability:collaborator-detail", args=[pessoa.id]))

        assert resposta.status_code == 200
        self.assertNotContains(resposta, "Custo anual e valor-hora")

    def test_pessoa_sem_login_do_erp_recebe_o_aviso(self) -> None:
        """A hora dela existe e não gera custo — a mesma pendência, vista do outro lado."""

        pessoa = self._pessoa()

        resposta = self.client.get(reverse("profitability:collaborator-detail", args=[pessoa.id]))

        self.assertContains(resposta, "Nenhum login do ERP aponta para esta pessoa")


class HorasTests(ScreenTestCase):
    def test_a_tela_separa_automaticas_de_f9(self) -> None:
        pessoa = self._pessoa()
        self._horas(pessoa, None, 150, marca="a")
        RegistroHoras.objects.create(
            organization=self.office,
            empresa=self.company,
            colaborador=pessoa,
            competencia=COMPETENCIA,
            data="2026-09-10",
            origem=OrigemHoras.F9,
            duracao_minutos=120,
            source_content_hash="b" * 64,
        )

        resposta = self.client.get(reverse("profitability:hours"))

        self.assertContains(resposta, "2h30")
        self.assertContains(resposta, "2h00")
        assert resposta.context["minutos_diferenca"] == 30

    def test_o_filtro_recorta_os_registros(self) -> None:
        pessoa = self._pessoa()
        self._horas(pessoa, None, 150, marca="a")

        f9 = self.client.get(reverse("profitability:hours"), {"filtro": "f9"})

        assert f9.context["linhas"].paginator.count == 0

    def test_hora_de_login_sem_dono_e_marcada_na_lista(self) -> None:
        usuario = UsuarioErp.objects.create(
            organization=self.office, i_usuario="GERENTE", nome="Gerente"
        )
        self._horas(None, usuario, 240)

        resposta = self.client.get(reverse("profitability:hours"))

        self.assertContains(resposta, "sem vínculo")

    def test_a_tela_respeita_a_carteira_do_colaborador(self) -> None:
        from apps.hub.models import CompanyAccessGrant

        pessoa = self._pessoa()
        self._horas(pessoa, None, 150, marca="a")
        outra = ClientCompany.objects.create(
            organization=self.office, name="Mercado Vizinho", dominio_code="26"
        )
        RegistroHoras.objects.create(
            organization=self.office,
            empresa=outra,
            colaborador=pessoa,
            competencia=COMPETENCIA,
            data="2026-09-11",
            origem=OrigemHoras.AUTOMATICA,
            duracao_minutos=60,
            source_content_hash="c" * 64,
        )
        operador, cliente = self._operador()
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=Membership.objects.get(user=operador),
            company=self.company,
            modules=["profitability"],
        )

        resposta = cliente.get(reverse("profitability:hours"))

        self.assertContains(resposta, "Padaria Central")
        self.assertNotContains(resposta, "Mercado Vizinho")


class AnalisesTests(ScreenTestCase):
    def test_a_margem_do_grupo_e_resultado_sobre_receita(self) -> None:
        """Média de margens pesaria igual um cliente de mil e um de cem mil."""

        from apps.profitability.models import Mensalidade

        pessoa = self._pessoa()
        self._horas(pessoa, None, 600)
        Mensalidade.objects.create(
            organization=self.office,
            empresa=self.company,
            competencia="2026-08",
            valor=D("1500.00"),
            fonte=Colaborador.Origem.DOMINIO,
        )
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("profitability:analyses"))

        assert resposta.status_code == 200
        grupos = resposta.context["grupos"]
        assert len(grupos) == 1
        assert grupos[0].mensalidade == D("1500.00")

    def test_a_evolucao_devolve_doze_meses_inclusive_os_vazios(self) -> None:
        """Omitir um mês vazio faria a linha saltar como se ele não tivesse existido."""

        resposta = self.client.get(reverse("profitability:analyses"))

        evolucao = resposta.context["evolucao"]
        assert len(evolucao) == 12
        assert evolucao[-1]["competencia"] == COMPETENCIA
        assert evolucao[0]["competencia"] == "2025-10"

    def test_o_grafico_recebe_a_serie_pela_pagina_e_nao_por_outra_requisicao(self) -> None:
        """Buscar o dado de novo abriria uma segunda fonte de verdade para o mesmo número."""

        import json as _json

        resposta = self.client.get(reverse("profitability:analyses"))
        corpo = resposta.content.decode()

        assert 'data-chart="evolucao"' in corpo
        serie = _json.loads(resposta.context["evolucao_json"])
        assert len(serie) == 12
        assert set(serie[0]) == {"competencia", "mensalidade", "custo", "margem"}
        # A mesma série também sai como tabela: é ela que leitor de tela percorre
        # e que sobrevive à impressão.
        assert "profitability-chart-data" in corpo

    def test_o_agrupamento_muda_com_o_recorte(self) -> None:
        for valor in ("segmento", "regime", "responsavel"):
            resposta = self.client.get(reverse("profitability:analyses"), {"por": valor})
            assert resposta.context["por"] == valor

        invalido = self.client.get(reverse("profitability:analyses"), {"por": "qualquer"})
        assert invalido.context["por"] == "segmento"


class ConfiguracaoTests(ScreenTestCase):
    def test_gravar_um_parametro_reprojeta_as_competencias(self) -> None:
        """Sem isso, esta tela e a ficha do cliente se contradizem até a próxima importação."""

        pessoa = self._pessoa()
        self._horas(pessoa, None, 600)
        recompute_competencia(self.office, COMPETENCIA)
        antes = ColaboradorCompetenciaMetrics.objects.get(colaborador=pessoa).custo_hora

        resposta = self.client.post(
            reverse("profitability:settings"),
            {
                "margem_alvo_padrao": "0.2000",
                "margem_atencao": "0.1500",
                "minutos_minimos_custo": "10",
                "encargos_percentual": "0.5000",
                "indice_produtividade": "0.8000",
                "dias_uteis_ano": "250",
                "feriados_dias_ano": "10",
                "horas_dia": "8.00",
                "limiar_divergencia_horas": "2",
                "limiar_divergencia_colaborador": "10",
            },
        )

        assert resposta.status_code == 302
        depois = ColaboradorCompetenciaMetrics.objects.get(colaborador=pessoa).custo_hora
        assert depois > antes
        assert ProfitabilityConfig.objects.get(organization=self.office).encargos_percentual == D(
            "0.5000"
        )

    def test_operador_ve_mas_nao_altera(self) -> None:
        _, operador = self._operador()

        leitura = operador.get(reverse("profitability:settings"))
        escrita = operador.post(reverse("profitability:settings"), {"dias_uteis_ano": "200"})

        assert leitura.status_code == 200
        self.assertContains(leitura, "Só um administrador altera")
        assert escrita.status_code == 403

    def test_feriados_nao_podem_consumir_o_ano(self) -> None:
        """Sem dia útil não há hora para dividir o custo, e o custo/hora de todos zeraria."""

        resposta = self.client.post(
            reverse("profitability:settings"),
            {
                "margem_alvo_padrao": "0.2000",
                "margem_atencao": "0.1500",
                "minutos_minimos_custo": "10",
                "encargos_percentual": "0.3500",
                "indice_produtividade": "0.8000",
                "dias_uteis_ano": "250",
                "feriados_dias_ano": "250",
                "horas_dia": "8.00",
                "limiar_divergencia_horas": "2",
                "limiar_divergencia_colaborador": "10",
            },
        )

        assert resposta.status_code == 200
        self.assertContains(resposta, "não podem consumir o ano inteiro")

    def test_indice_de_produtividade_zero_e_recusado(self) -> None:
        resposta = self.client.post(
            reverse("profitability:settings"),
            {
                "margem_alvo_padrao": "0.2000",
                "margem_atencao": "0.1500",
                "minutos_minimos_custo": "10",
                "encargos_percentual": "0.3500",
                "indice_produtividade": "0",
                "dias_uteis_ano": "250",
                "feriados_dias_ano": "10",
                "horas_dia": "8.00",
                "limiar_divergencia_horas": "2",
                "limiar_divergencia_colaborador": "10",
            },
        )

        self.assertContains(resposta, "maior que zero")


class FichaDaEmpresaTests(ScreenTestCase):
    def test_a_ficha_do_cliente_mostra_o_resultado(self) -> None:
        from apps.profitability.models import Mensalidade

        pessoa = self._pessoa()
        self._horas(pessoa, None, 600)
        Mensalidade.objects.create(
            organization=self.office,
            empresa=self.company,
            competencia="2026-08",
            valor=D("1500.00"),
            fonte=Colaborador.Origem.DOMINIO,
        )
        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        assert resposta.status_code == 200
        self.assertContains(resposta, "Rentabilidade")
        self.assertContains(resposta, "Honorário sugerido")

    def test_sem_horas_a_ficha_nao_sugere_honorario(self) -> None:
        """Inventar número aqui é pior que não ter."""

        recompute_competencia(self.office, COMPETENCIA)

        resposta = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertContains(resposta, "Sem horas suficientes na competência")
        assert resposta.context["profitability_sugerida"] is None

    def test_modulo_desligado_nao_acrescenta_secao_na_ficha(self) -> None:
        ProductModule.objects.filter(
            organization=self.office, code=ProductModule.Code.PROFITABILITY
        ).update(enabled=False)

        resposta = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        assert resposta.status_code == 200
        assert resposta.context.get("profitability_enabled") is None
