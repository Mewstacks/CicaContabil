"""O módulo declarado: catálogo, navegação e os portões que a CICA já aplica.

O que interessa provar é que a tela de rentabilidade obedece exatamente as mesmas
recusas dos outros módulos — módulo desligado, colaborador fora do escopo, sessão
somente-leitura e inquilino vizinho — porque é ela que expõe honorário e margem
por cliente. Esta é a verificação que fecha D-109 do lado da tela: a carteira
mostrada é a que `CompanyAccessGrant` autoriza, e não a do escritório inteiro.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.hub.module_catalog import MODULES, OFFERED_MODULE_CODES, definition
from apps.hub.navigation import workspace_navigation
from apps.organizations.models import Membership, Organization
from apps.profitability.models import ClienteCompetenciaMetrics, Competencia

D = Decimal
URL = "/app/rentabilidade/"


class CatalogoTests(TestCase):
    def test_o_modulo_esta_no_catalogo_e_na_oferta(self) -> None:
        modulo = definition(ProductModule.Code.PROFITABILITY)

        assert modulo.label == "Rentabilidade por Cliente"
        assert modulo.route_name == "profitability:overview"
        assert modulo.required_capabilities == ("companies",)
        assert ProductModule.Code.PROFITABILITY in OFFERED_MODULE_CODES
        assert ProductModule.Code.PROFITABILITY in MODULES

    def test_a_rota_do_catalogo_resolve(self) -> None:
        """Entrada de catálogo com rota que não reverte quebra a navegação inteira."""

        assert reverse(definition(ProductModule.Code.PROFITABILITY).route_name) == URL


class OfertaTests(TestCase):
    def test_o_modulo_nao_entra_no_que_se_liga_sem_alguem_decidir(self) -> None:
        """Por D-115: sem fonte de honorários e sem preço, não se oferece sozinho."""

        from apps.hub.module_catalog import self_service_module_codes

        automaticos = self_service_module_codes()

        assert ProductModule.Code.PROFITABILITY in OFFERED_MODULE_CODES
        assert ProductModule.Code.PROFITABILITY not in automaticos
        assert ProductModule.Code.NFSE in automaticos

    def test_a_demonstracao_nao_abre_o_modulo(self) -> None:
        """Uma demonstração que abre o módulo já o está anunciando."""

        from apps.hub.seeding import ensure_office

        office = ensure_office(name="Demo", slug="demo-rentabilidade", enable_modules=True)

        assert not ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.PROFITABILITY
        ).exists()
        assert ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.NFSE, enabled=True
        ).exists()


class ModulePageTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.user = User.objects.create_user(email="dono@example.com", password="uma-senha-longa")
        self.membership = Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria Central", dominio_code="25"
        )
        self.client = Client()
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def _ligar(self) -> ProductModule:
        return ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.PROFITABILITY, enabled=True
        )

    def _metrica(self, **kwargs: object) -> ClienteCompetenciaMetrics:
        Competencia.objects.get_or_create(
            organization=self.office,
            competencia="2026-09",
            defaults={"inicio": "2026-09-01", "fim": "2026-09-30", "is_atual": True},
        )
        campos: dict[str, object] = {
            "organization": self.office,
            "empresa": self.company,
            "competencia": "2026-09",
            "horas_auto_minutos": 600,
            "custo": D("800.00"),
            "mensalidade": D("1500.00"),
            "resultado": D("700.00"),
            "margem": D("0.466667"),
            "faixa": "saudavel",
        }
        campos.update(kwargs)
        return ClienteCompetenciaMetrics.objects.create(**campos)  # type: ignore[arg-type]

    def test_modulo_desligado_recusa_a_tela(self) -> None:
        resposta = self.client.get(URL)

        assert resposta.status_code == 403
        self.assertTemplateUsed(resposta, "hub/module_unavailable.html")

    def test_modulo_ligado_abre_a_tela(self) -> None:
        self._ligar()
        self._metrica()

        resposta = self.client.get(URL)

        assert resposta.status_code == 200
        self.assertContains(resposta, "Padaria Central")
        self.assertTemplateUsed(resposta, "profitability/overview.html")

    def test_colaborador_sem_o_modulo_no_escopo_e_recusado(self) -> None:
        self._ligar()
        colaborador = User.objects.create_user(
            email="operador@example.com", password="outra-senha-longa"
        )
        vinculo = Membership.objects.create(
            organization=self.office, user=colaborador, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=vinculo,
            company=self.company,
            modules=["nfse"],
        )
        cliente = Client()
        cliente.force_login(colaborador)
        sessao = cliente.session
        sessao["hub_organization_id"] = str(self.office.id)
        sessao.save()

        resposta = cliente.get(URL)

        assert resposta.status_code == 403

    def test_a_carteira_da_tela_e_a_que_o_colaborador_pode_ver(self) -> None:
        """É isto que D-109 preserva: a margem por cliente não escapa do filtro."""

        self._ligar()
        self._metrica()
        outra = ClientCompany.objects.create(
            organization=self.office, name="Mercado Vizinho", dominio_code="26"
        )
        self._metrica(empresa=outra)

        colaborador = User.objects.create_user(
            email="operador@example.com", password="outra-senha-longa"
        )
        vinculo = Membership.objects.create(
            organization=self.office, user=colaborador, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=vinculo,
            company=self.company,
            modules=["profitability"],
        )
        cliente = Client()
        cliente.force_login(colaborador)
        sessao = cliente.session
        sessao["hub_organization_id"] = str(self.office.id)
        sessao.save()

        resposta = cliente.get(URL)

        assert resposta.status_code == 200
        self.assertContains(resposta, "Padaria Central")
        self.assertNotContains(resposta, "Mercado Vizinho")

    def test_a_tela_nao_esconde_falta_de_dado_atras_de_margem(self) -> None:
        """Sem hora não há custo, e margem sobre custo ausente leria alto sem razão."""

        self._ligar()
        self._metrica(horas_auto_minutos=0, custo=D("0"), resultado=D("1500.00"), faixa="sem_dados")

        resposta = self.client.get(URL)

        self.assertContains(resposta, "Sem horas no mês")
        # A mesma ausência é dita duas vezes de propósito: na linha do cliente e
        # no bloco de confiabilidade, que é onde quem lê o cabeçalho descobre
        # quanto daquele número é apurado.
        self.assertContains(resposta, "Confiabilidade dos dados")
        self.assertContains(resposta, "lê mais alta do que é")

    def test_sem_competencia_a_tela_diz_que_nao_ha_o_que_calcular(self) -> None:
        self._ligar()

        resposta = self.client.get(URL)

        assert resposta.status_code == 200
        self.assertContains(resposta, "Ainda não há competência para calcular")

    def test_inquilino_vizinho_nao_aparece_na_carteira(self) -> None:
        self._ligar()
        self._metrica()
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        alheia = ClientCompany.objects.create(
            organization=vizinho, name="Empresa Alheia", dominio_code="99"
        )
        Competencia.objects.create(
            organization=vizinho,
            competencia="2026-09",
            inicio="2026-09-01",
            fim="2026-09-30",
        )
        ClienteCompetenciaMetrics.objects.create(
            organization=vizinho,
            empresa=alheia,
            competencia="2026-09",
            custo=D("1"),
            mensalidade=D("1"),
            resultado=D("0"),
            margem=D("0"),
            faixa="saudavel",
        )

        resposta = self.client.get(URL)

        self.assertContains(resposta, "Padaria Central")
        self.assertNotContains(resposta, "Empresa Alheia")

    def test_anonimo_vai_para_o_login(self) -> None:
        self._ligar()

        resposta = Client().get(URL)

        assert resposta.status_code == 302
        assert "/entrar" in resposta["Location"] or "login" in resposta["Location"]


class NavegacaoTests(TestCase):
    def _navegacao(self, codes: list[str]) -> list[dict[str, object]]:
        from types import SimpleNamespace

        from django.test import RequestFactory
        from django.urls import resolve

        request = RequestFactory().get(URL)
        request.resolver_match = resolve(URL)
        return workspace_navigation(
            {
                "request": request,
                "enabled_modules": [SimpleNamespace(code=code) for code in codes],
                "membership": None,
            }
        )

    def test_o_grupo_gestao_so_aparece_com_o_modulo_ligado(self) -> None:
        sem = {grupo["key"] for grupo in self._navegacao(["nfse"])}
        com = {grupo["key"] for grupo in self._navegacao(["nfse", "profitability"])}

        assert "management" not in sem
        assert "management" in com

    def test_o_link_aponta_para_a_tela_e_fica_ativo_nela(self) -> None:
        grupos = {grupo["key"]: grupo for grupo in self._navegacao(["profitability"])}
        gestao = grupos["management"]
        link = gestao["links"][0]  # type: ignore[index]

        assert link["url"] == URL
        assert link["active"] is True
        assert gestao["label"] == "Gestão"
