"""O domínio portado, conferido no banco.

Interessa aqui o que a portabilidade podia ter quebrado sem aparecer: o escopo por
escritório, os índices cegos que sustentam o casamento com o ERP, e as travas que
na origem estavam no banco e não no código.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.common.encryption import blind_index
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.profitability.models import (
    Colaborador,
    CompanyErpProfile,
    Competencia,
    Mensalidade,
    ProfitabilityConfig,
    RegistroHoras,
    SalarioColaborador,
    Segmento,
    SistemaOrigem,
    UsuarioErp,
)
from apps.profitability.normalize import strip_accents_upper

D = Decimal


class ProfitabilityDomainTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.other = Organization.objects.create(name="Vizinho", slug="vizinho")
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria São Tomé", dominio_code="25"
        )

    def _profile(self, **kwargs: object) -> CompanyErpProfile:
        defaults: dict[str, object] = {
            "organization": self.office,
            "empresa": self.company,
            "codi_emp": 25,
            "documento": "12.345.678/0001-99",
        }
        defaults.update(kwargs)
        return CompanyErpProfile.objects.create(**defaults)  # type: ignore[arg-type]

    def test_perfil_indexa_documento_raiz_e_razao_sem_guardar_texto_pesquisavel(self) -> None:
        perfil = self._profile()

        assert perfil.documento_tipo == "cnpj"
        assert perfil.documento_bi == blind_index(
            "12345678000199", namespace="profitability.empresa.documento"
        )
        assert perfil.documento_raiz_bi == blind_index(
            "12345678", namespace="profitability.empresa.raiz"
        )
        assert perfil.razao_normalizada_bi == blind_index(
            strip_accents_upper("Padaria São Tomé"), namespace="profitability.empresa.razao"
        )
        # O documento em claro não fica pesquisável no banco.
        assert CompanyErpProfile.objects.filter(documento="12.345.678/0001-99").count() == 0

    def test_matriz_e_filial_compartilham_a_raiz_e_diferem_no_documento(self) -> None:
        """A dobra de grupo econômico depende disso, e é por isso que a raiz é coluna."""

        filial_company = ClientCompany.objects.create(
            organization=self.office, name="Padaria São Tomé Filial", dominio_code="26"
        )
        matriz = self._profile()
        filial = self._profile(empresa=filial_company, codi_emp=26, documento="12.345.678/0002-70")

        assert matriz.documento_raiz_bi == filial.documento_raiz_bi
        assert matriz.documento_bi != filial.documento_bi

    def test_documento_vazio_nao_gera_indice(self) -> None:
        perfil = self._profile(documento="", origem=CompanyErpProfile.Origem.MANUAL, codi_emp=None)

        assert perfil.documento_tipo == ""
        assert perfil.documento_bi == ""
        assert perfil.documento_raiz_bi == ""

    def test_mesmo_codi_emp_em_erps_diferentes_convive(self) -> None:
        """A empresa 25 do Domínio não tem relação com a 25 do Siescon."""

        outra = ClientCompany.objects.create(
            organization=self.office, name="Outra", dominio_code="25-siescon"
        )
        self._profile()
        self._profile(empresa=outra, sistema_origem=SistemaOrigem.SIESCON, codi_emp=25)

        assert CompanyErpProfile.objects.filter(codi_emp=25).count() == 2

    def test_codi_emp_repetido_no_mesmo_erp_e_recusado_pelo_banco(self) -> None:
        outra = ClientCompany.objects.create(
            organization=self.office, name="Outra", dominio_code="99"
        )
        self._profile()

        with pytest.raises(IntegrityError), transaction.atomic():
            self._profile(empresa=outra, codi_emp=25)

    def test_empresa_importada_do_erp_exige_codi_emp(self) -> None:
        perfil = CompanyErpProfile(
            organization=self.office, empresa=self.company, codi_emp=None, documento=""
        )

        with pytest.raises(ValidationError) as erro:
            perfil.clean()
        assert "codi_emp" in erro.value.message_dict

    def test_papel_fora_do_catalogo_e_recusado(self) -> None:
        """Os papéis liberam ler folha e honorários de outra empresa; nada vem marcado."""

        perfil = CompanyErpProfile(
            organization=self.office,
            empresa=self.company,
            codi_emp=25,
            papel=["cliente", "dono_do_mundo"],
        )

        with pytest.raises(ValidationError) as erro:
            perfil.clean()
        assert "papel" in erro.value.message_dict

        assert self._profile().papel == []

    def test_relacao_com_empresa_de_outro_escritorio_e_recusada(self) -> None:
        alheia = ClientCompany.objects.create(
            organization=self.other, name="Alheia", dominio_code="1"
        )
        perfil = CompanyErpProfile(
            organization=self.office, empresa=alheia, codi_emp=1, documento=""
        )

        with pytest.raises(ValidationError) as erro:
            perfil.clean()
        assert "empresa" in erro.value.message_dict

    def test_colaborador_cifra_o_nome_e_mantem_indice_cego(self) -> None:
        colaborador = Colaborador.objects.create(
            organization=self.office, codigo="C-001", nome="Ana Woltmann"
        )

        assert colaborador.nome_bi == blind_index(
            "Ana Woltmann", namespace="profitability.colaborador.nome"
        )
        assert Colaborador.objects.filter(nome="Ana Woltmann").count() == 0
        assert Colaborador.objects.get(nome_bi=colaborador.nome_bi).nome == "Ana Woltmann"

    def test_usuario_do_erp_guarda_login_como_texto(self) -> None:
        """`i_usuario` é varchar. Tratá-lo como inteiro rejeitava toda linha de horas."""

        usuario = UsuarioErp.objects.create(
            organization=self.office, i_usuario="ANA.W", nome="Ana Woltmann"
        )

        assert usuario.i_usuario == "ANA.W"
        assert usuario.vinculo_manual is False
        assert usuario.colaborador_id is None

    def test_o_mesmo_login_em_erps_diferentes_convive(self) -> None:
        UsuarioErp.objects.create(organization=self.office, i_usuario="ANA.W", nome="Ana")
        UsuarioErp.objects.create(
            organization=self.office,
            i_usuario="ANA.W",
            sistema_origem=SistemaOrigem.SIESCON,
            nome="Ana",
        )

        assert UsuarioErp.objects.filter(i_usuario="ANA.W").count() == 2

    def test_login_repetido_no_mesmo_erp_e_recusado(self) -> None:
        UsuarioErp.objects.create(organization=self.office, i_usuario="ANA.W", nome="Ana")

        with pytest.raises(IntegrityError), transaction.atomic():
            UsuarioErp.objects.create(organization=self.office, i_usuario="ANA.W", nome="Ana")

    def test_uma_so_competencia_corrente_por_escritorio(self) -> None:
        """A trava é do banco, não de quem lembrar de limpar a anterior."""

        Competencia.objects.create(
            organization=self.office,
            competencia="2026-08",
            inicio="2026-08-01",
            fim="2026-08-31",
            is_atual=True,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            Competencia.objects.create(
                organization=self.office,
                competencia="2026-09",
                inicio="2026-09-01",
                fim="2026-09-30",
                is_atual=True,
            )

        # O escritório vizinho tem a sua, sem conflito.
        Competencia.objects.create(
            organization=self.other,
            competencia="2026-09",
            inicio="2026-09-01",
            fim="2026-09-30",
            is_atual=True,
        )

    def test_horas_iguais_convivem_pelo_ordinal_e_repeticao_e_recusada(self) -> None:
        """Linhas de origem iguais são legítimas; o ordinal preserva a multiplicidade."""

        comum = {
            "organization": self.office,
            "empresa": self.company,
            "competencia": "2026-09",
            "data": "2026-09-10",
            "origem": "automatica",
            "duracao_minutos": 90,
            "source_content_hash": "a" * 64,
        }
        RegistroHoras.objects.create(**comum, occurrence_index=0)  # type: ignore[arg-type]
        RegistroHoras.objects.create(**comum, occurrence_index=1)  # type: ignore[arg-type]

        assert RegistroHoras.objects.count() == 2

        with pytest.raises(IntegrityError), transaction.atomic():
            RegistroHoras.objects.create(**comum, occurrence_index=1)  # type: ignore[arg-type]

    def test_horas_nao_podem_apagar_a_empresa_por_baixo(self) -> None:
        """`PROTECT`: apagar a carteira levaria junto o fato que sustenta o custo."""

        RegistroHoras.objects.create(
            organization=self.office,
            empresa=self.company,
            competencia="2026-09",
            data="2026-09-10",
            origem="automatica",
            duracao_minutos=90,
            source_content_hash="b" * 64,
        )

        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError), transaction.atomic():
            self.company.delete()

    def test_mensalidade_manual_vence_a_derivada(self) -> None:
        """O operador corrige um casamento ruim sem o ciclo seguinte reverter calado."""

        mensalidade = Mensalidade.objects.create(
            organization=self.office,
            empresa=self.company,
            competencia="2026-09",
            valor=D("1200.00"),
            fonte=Colaborador.Origem.DOMINIO,
        )
        assert mensalidade.valor_efetivo == D("1200.00")

        mensalidade.manual_override = D("1500.00")
        mensalidade.save()
        assert mensalidade.valor_efetivo == D("1500.00")

        # Zero é uma correção legítima e não pode ser lido como "sem correção".
        mensalidade.manual_override = D("0.00")
        mensalidade.save()
        assert mensalidade.valor_efetivo == D("0.00")

    def test_salario_e_unico_por_colaborador_e_competencia(self) -> None:
        colaborador = Colaborador.objects.create(
            organization=self.office, codigo="C-001", nome="Ana"
        )
        SalarioColaborador.objects.create(
            organization=self.office,
            colaborador=colaborador,
            competencia="2026-09",
            salario=D("3000"),
            fonte=Colaborador.Origem.MANUAL,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            SalarioColaborador.objects.create(
                organization=self.office,
                colaborador=colaborador,
                competencia="2026-09",
                salario=D("4000"),
                fonte=Colaborador.Origem.MANUAL,
            )

    def test_segmento_repetido_no_mesmo_escritorio_e_recusado(self) -> None:
        Segmento.objects.create(organization=self.office, nome="Comércio")
        Segmento.objects.create(organization=self.other, nome="Comércio")

        with pytest.raises(IntegrityError), transaction.atomic():
            Segmento.objects.create(organization=self.office, nome="Comércio")

    def test_configuracao_nasce_com_os_parametros_da_conta_vigente(self) -> None:
        config = ProfitabilityConfig.objects.create(organization=self.office)

        assert config.encargos_percentual == D("0.3500")
        assert config.dias_uteis_ano == 250
        assert config.feriados_dias_ano == 10
        assert config.horas_dia == D("8.00")
        assert config.indice_produtividade == D("0.8000")
        assert config.margem_atencao == D("0.1500")
        assert config.minutos_minimos_custo == 10
        # Q-39 está aberta: sem fonte escolhida, nenhum contrato de receita roda.
        assert config.fonte_receita == ""
        assert config.evento_mensalidade is None
        # As duas colunas aposentadas pela auditoria não vieram.
        assert not hasattr(config, "horas_mes_referencia")
        assert not hasattr(config, "fator_encargos")
