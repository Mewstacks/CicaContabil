"""O recálculo de uma competência, do fato de horas até a linha da carteira.

As regras exercitadas aqui são as que a auditoria de setembro de 2026 fixou no
projeto de origem, e cada teste ancora uma delas. São as que, quando quebram,
não quebram alto: a carteira continua respondendo, com o número errado.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.profitability.models import (
    ClienteCompetenciaMetrics,
    Colaborador,
    ColaboradorCompetenciaMetrics,
    CompanyErpProfile,
    Mensalidade,
    OrigemHoras,
    ProfitabilityConfig,
    RegistroHoras,
    SalarioColaborador,
    SistemaOrigem,
)
from apps.profitability.services import (
    codigos_erp,
    competencia_anterior,
    competencia_seguinte,
    custo_hora_do_colaborador,
    get_config,
    grupos_por_raiz_de_cnpj,
    recompute_competencia,
    salario_vigente_map,
    unidades_do_grupo,
)

D = Decimal
COMPETENCIA = "2026-09"
ANTERIOR = "2026-08"


class RecomputeTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.config = get_config(self.office)
        self.company = self._company("Padaria Central", "1", "12.345.678/0001-99", codi_emp=1)

    def _company(
        self, nome: str, code: str, documento: str, *, codi_emp: int, papel: list[str] | None = None
    ) -> ClientCompany:
        company = ClientCompany.objects.create(
            organization=self.office, name=nome, dominio_code=code
        )
        CompanyErpProfile.objects.create(
            organization=self.office,
            empresa=company,
            codi_emp=codi_emp,
            documento=documento,
            papel=papel or ["cliente"],
        )
        return company

    def _pessoa(self, nome: str, salario: str, **kwargs: object) -> Colaborador:
        colaborador = Colaborador.objects.create(
            organization=self.office, codigo=nome[:3].upper(), nome=nome, **kwargs
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
        company: ClientCompany,
        colaborador: Colaborador | None,
        minutos: int,
        *,
        origem: str = OrigemHoras.AUTOMATICA,
        marca: str = "a",
    ) -> None:
        RegistroHoras.objects.create(
            organization=self.office,
            empresa=company,
            colaborador=colaborador,
            competencia=COMPETENCIA,
            data="2026-09-10",
            origem=origem,
            duracao_minutos=minutos,
            source_content_hash=marca * 64,
        )

    def _mensalidade(self, company: ClientCompany, valor: str, competencia: str = ANTERIOR) -> None:
        Mensalidade.objects.create(
            organization=self.office,
            empresa=company,
            competencia=competencia,
            valor=D(valor),
            fonte=Colaborador.Origem.DOMINIO,
        )

    def test_carteira_sai_com_custo_resultado_e_margem(self) -> None:
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 600)
        self._mensalidade(self.company, "1500.00")

        recompute_competencia(self.office, COMPETENCIA)

        linha = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        hora = custo_hora_do_colaborador(pessoa, D("3000"), self.config)
        esperado = (D(600) / 60 * hora).quantize(D("0.01"))
        assert linha.horas_auto_minutos == 600
        assert linha.custo == esperado
        assert linha.mensalidade == D("1500.00")
        assert linha.resultado == D("1500.00") - esperado
        assert linha.custo_completo is True
        assert linha.faixa in {"saudavel", "atencao", "negativa"}

    def test_mensalidade_lida_e_a_do_mes_anterior(self) -> None:
        """O escritório fatura em atraso; sem o deslocamento todo mês abre zerado."""

        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 600)
        self._mensalidade(self.company, "1500.00", competencia=ANTERIOR)
        self._mensalidade(self.company, "9999.00", competencia=COMPETENCIA)

        recompute_competencia(self.office, COMPETENCIA)

        assert ClienteCompetenciaMetrics.objects.get(empresa=self.company).mensalidade == D(
            "1500.00"
        )

    def test_poucos_minutos_nao_viram_margem_cheia(self) -> None:
        """O piso existe porque 70 das 175 linhas saudáveis tinham menos de 10 minutos."""

        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 5)
        self._mensalidade(self.company, "1500.00")

        recompute_competencia(self.office, COMPETENCIA)

        linha = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        assert linha.faixa == "sem_dados"
        assert linha.faixa != "saudavel"

    def test_piso_zero_ainda_exige_um_minuto(self) -> None:
        """Em 0 o comportamento antigo volta, mas quem não tem hora nenhuma não passa."""

        self.config.minutos_minimos_custo = 0
        self.config.save()
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 5)
        self._mensalidade(self.company, "1500.00")

        recompute_competencia(self.office, COMPETENCIA)
        assert ClienteCompetenciaMetrics.objects.get(empresa=self.company).faixa != "sem_dados"

        RegistroHoras.objects.all().delete()
        recompute_competencia(self.office, COMPETENCIA)
        assert ClienteCompetenciaMetrics.objects.get(empresa=self.company).faixa == "sem_dados"

    def test_hora_sem_pessoa_ou_sem_salario_marca_custo_incompleto(self) -> None:
        """Sem isso a hora existe, não gera custo, e o cliente parece rentável."""

        self._horas(self.company, None, 600)
        self._mensalidade(self.company, "1500.00")
        recompute_competencia(self.office, COMPETENCIA)

        linha = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        assert linha.custo_completo is False
        assert linha.faixa == "incompleta"
        assert linha.minutos_sem_custo == 600
        assert "colaborador_nao_mapeado" in linha.motivos_incompletude

        sem_salario = Colaborador.objects.create(
            organization=self.office, codigo="SEM", nome="Sem Salário"
        )
        RegistroHoras.objects.all().delete()
        self._horas(self.company, sem_salario, 600, marca="c")
        recompute_competencia(self.office, COMPETENCIA)

        linha = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        assert "salario_nao_disponivel" in linha.motivos_incompletude

    def test_pj_nao_paga_encargo_nem_decimo_terceiro(self) -> None:
        """Aplicar encargo sobre a nota de um PJ inventa custo que ninguém paga."""

        clt = self._pessoa("Ana Clt", "3000")
        pj = self._pessoa("Bruno Pj", "3000", contratacao=Colaborador.Contratacao.PJ)

        custo_clt = custo_hora_do_colaborador(clt, D("3000"), self.config)
        custo_pj = custo_hora_do_colaborador(pj, D("3000"), self.config)

        assert custo_pj < custo_clt
        # Doze notas contra treze salários mais terço e encargos.
        assert custo_clt / custo_pj > D("1.4")

    def test_salario_vigente_e_o_mais_recente_ate_a_competencia(self) -> None:
        """Recalcular maio não pode precificar maio com o salário de julho."""

        pessoa = Colaborador.objects.create(organization=self.office, codigo="A", nome="Ana")
        for competencia, valor in (("2026-07", "3000"), ("2026-09", "5000"), ("2026-11", "9000")):
            SalarioColaborador.objects.create(
                organization=self.office,
                colaborador=pessoa,
                competencia=competencia,
                salario=D(valor),
                fonte=Colaborador.Origem.MANUAL,
            )

        assert salario_vigente_map(self.office, "2026-08")[str(pessoa.id)] == ("2026-07", D("3000"))
        assert salario_vigente_map(self.office, "2026-09")[str(pessoa.id)] == ("2026-09", D("5000"))
        assert salario_vigente_map(self.office, "2026-10")[str(pessoa.id)] == ("2026-09", D("5000"))

    def test_filial_soma_na_matriz_em_vez_de_abrir_linha_propria(self) -> None:
        """Sem juntar, a filial lê sem receita e a matriz lê rentável demais."""

        filial = self._company("Padaria Filial", "2", "12.345.678/0002-70", codi_emp=2)
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 300, marca="a")
        self._horas(filial, pessoa, 300, marca="b")
        self._mensalidade(self.company, "1500.00")

        assert grupos_por_raiz_de_cnpj(self.office) == {str(filial.id): str(self.company.id)}

        recompute_competencia(self.office, COMPETENCIA)

        assert not ClienteCompetenciaMetrics.objects.filter(empresa=filial).exists()
        matriz = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        assert matriz.horas_auto_minutos == 600

    def test_unidades_do_grupo_abrem_a_linha_somada(self) -> None:
        """A carteira soma para decidir preço; a auditoria precisa de qual unidade veio."""

        filial = self._company("Padaria Filial", "2", "12.345.678/0002-70", codi_emp=2)
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 300, marca="a")
        self._horas(filial, pessoa, 180, marca="b")

        # Chegando pela filial, que nem linha de métrica tem, o grupo abre igual.
        unidades = unidades_do_grupo(self.office, COMPETENCIA, str(filial.id))

        assert [u.eh_matriz for u in unidades] == [True, False]
        assert [u.auto_minutos for u in unidades] == [300, 180]
        assert [u.empresa.name for u in unidades] == ["Padaria Central", "Padaria Filial"]

    def test_o_proprio_escritorio_nao_e_cliente_dele_mesmo(self) -> None:
        """Ele aparecia na carteira com horas internas e margem de -100%."""

        escritorio = self._company(
            "Contabilidade Fedrizzi",
            "9",
            "99.999.999/0001-99",
            codi_emp=9,
            papel=["billing_source"],
        )
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(escritorio, pessoa, 600)

        recompute_competencia(self.office, COMPETENCIA)

        assert not ClienteCompetenciaMetrics.objects.filter(empresa=escritorio).exists()

    def test_empresa_sem_documento_nao_ocupa_linha(self) -> None:
        """Sem documento é registro de estrutura do ERP, e honorário nenhum a acha."""

        modelo = ClientCompany.objects.create(
            organization=self.office, name="EXEMPLO PLANO CONTAS", dominio_code="90"
        )
        CompanyErpProfile.objects.create(
            organization=self.office, empresa=modelo, codi_emp=90, documento=""
        )

        recompute_competencia(self.office, COMPETENCIA)

        assert not ClienteCompetenciaMetrics.objects.filter(empresa=modelo).exists()
        assert ClienteCompetenciaMetrics.objects.filter(empresa=self.company).exists()

    def test_recompute_e_idempotente(self) -> None:
        """Delete-and-insert por competência: repetir depois de falha parcial converge."""

        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 600)
        self._mensalidade(self.company, "1500.00")

        recompute_competencia(self.office, COMPETENCIA)
        primeira = ClienteCompetenciaMetrics.objects.get(empresa=self.company)
        recompute_competencia(self.office, COMPETENCIA)
        segunda = ClienteCompetenciaMetrics.objects.get(empresa=self.company)

        assert ClienteCompetenciaMetrics.objects.count() == 1
        assert (primeira.custo, primeira.margem) == (segunda.custo, segunda.margem)

    def test_metrica_de_colaborador_separa_sem_salario_de_custo_zero(self) -> None:
        """Zero é um número: sem a marca, quem não tem salário parece custar R$ 0,00."""

        sem_salario = Colaborador.objects.create(
            organization=self.office, codigo="SEM", nome="Sem Salário"
        )
        self._horas(self.company, sem_salario, 600)

        recompute_competencia(self.office, COMPETENCIA)

        linha = ColaboradorCompetenciaMetrics.objects.get(colaborador=sem_salario)
        assert linha.sem_salario is True
        assert linha.custo == 0

    def test_quem_nao_trabalhou_no_mes_nao_e_marcado_sem_salario(self) -> None:
        Colaborador.objects.create(organization=self.office, codigo="OCI", nome="Sem Horas")

        recompute_competencia(self.office, COMPETENCIA)

        linha = ColaboradorCompetenciaMetrics.objects.get(colaborador__codigo="OCI")
        assert linha.sem_salario is False
        assert linha.horas_auto_minutos == 0

    def test_codigo_erp_prefere_o_do_dominio_pelo_documento(self) -> None:
        """A linha visível pode ser a do Siescon, e o código útil está na gêmea."""

        codigos = codigos_erp(self.office)
        assert codigos[str(self.company.id)] == ("dominio", 1)

    def test_empresa_com_perfil_nos_dois_erps_ocupa_uma_linha_so(self) -> None:
        """A gêmea do outro ERP não é um segundo cliente: é a mesma empresa vista duas vezes."""

        CompanyErpProfile.objects.create(
            organization=self.office,
            empresa=self.company,
            codi_emp=711,
            sistema_origem=SistemaOrigem.SIESCON,
            documento="12.345.678/0001-99",
            papel=["cliente"],
        )
        pessoa = self._pessoa("Ana Woltmann", "3000")
        self._horas(self.company, pessoa, 600)
        self._mensalidade(self.company, "1500.00")

        recompute_competencia(self.office, COMPETENCIA)

        assert ClienteCompetenciaMetrics.objects.filter(empresa=self.company).count() == 1
        assert self.company.erp_profiles.count() == 2

    def test_documento_em_um_erp_basta_para_a_empresa_entrar_na_carteira(self) -> None:
        """Olhar perfil a perfil esconderia empresa documentada só porque a gêmea veio sem."""

        CompanyErpProfile.objects.create(
            organization=self.office,
            empresa=self.company,
            codi_emp=711,
            sistema_origem=SistemaOrigem.SIESCON,
            documento="",
            papel=["cliente"],
        )

        recompute_competencia(self.office, COMPETENCIA)

        assert ClienteCompetenciaMetrics.objects.filter(empresa=self.company).exists()

    def test_isolamento_entre_escritorios(self) -> None:
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        alheia = ClientCompany.objects.create(organization=vizinho, name="Alheia", dominio_code="1")
        CompanyErpProfile.objects.create(
            organization=vizinho, empresa=alheia, codi_emp=1, documento="11.111.111/0001-11"
        )

        recompute_competencia(self.office, COMPETENCIA)

        assert not ClienteCompetenciaMetrics.objects.filter(empresa=alheia).exists()
        assert ClienteCompetenciaMetrics.objects.filter(organization=vizinho).count() == 0


class CompetenciaAritmeticaTests(TestCase):
    def test_virada_de_ano_nos_dois_sentidos(self) -> None:
        assert competencia_anterior("2026-01") == "2025-12"
        assert competencia_anterior("2026-09") == "2026-08"
        assert competencia_seguinte("2026-12") == "2027-01"
        assert competencia_seguinte("2026-09") == "2026-10"


class ConfigTests(TestCase):
    def test_config_e_criada_sob_demanda_uma_vez_so(self) -> None:
        office = Organization.objects.create(name="Novo", slug="novo")

        primeira = get_config(office)
        segunda = get_config(office)

        assert primeira.pk == segunda.pk
        assert ProfitabilityConfig.objects.filter(organization=office).count() == 1
