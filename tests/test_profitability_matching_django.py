"""O casamento entre o login do ERP e a pessoa da folha.

Sem esse vínculo a hora existe e não gera custo, e a margem do cliente infla —
foi assim que meia carteira apareceu com margem acima de 90% no projeto de
origem. As regras aqui são as que a correção fixou, e cada teste ancora uma.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.profitability.matching import (
    aplicar_vinculo,
    casar,
    partes_do_nome,
    sugerir,
    vincular_usuarios_pendentes,
)
from apps.profitability.models import Colaborador, OrigemHoras, RegistroHoras, UsuarioErp

D = Decimal


class PartesDoNomeTests(TestCase):
    def test_particulas_e_acentos_nao_distinguem_ninguem(self) -> None:
        assert partes_do_nome("José  da Silva") == ["JOSE", "SILVA"]
        assert partes_do_nome("JORGE DA SILVA") == partes_do_nome("JORGE SILVA")

    def test_apostrofo_une_e_o_resto_da_pontuacao_separa(self) -> None:
        """`D'AVILA` é um sobrenome só; virar `D` + `AVILA` inventaria uma letra."""

        assert partes_do_nome("Maria D'Avila") == ["MARIA", "DAVILA"]
        assert partes_do_nome("Maria D\u2019Avila") == ["MARIA", "DAVILA"]

    def test_lixo_do_cadastro_siescon_nao_vira_sobrenome(self) -> None:
        """A vírgula ocupava a posição de último sobrenome, que é a regra forte."""

        assert partes_do_nome("DENISE MOTA               ,") == ["DENISE", "MOTA"]

    def test_nome_so_de_particulas_nao_da_para_casar(self) -> None:
        assert partes_do_nome("DE DA DOS") == []
        assert partes_do_nome("") == []


class CasarTests(TestCase):
    def test_nome_do_meio_faltando_de_um_lado_ainda_casa(self) -> None:
        candidatos = [("a", partes_do_nome("ANA PAULA VELHO WOLFF"))]

        assert casar(partes_do_nome("ANA PAULA WOLFF"), candidatos) == "a"

    def test_sobrenome_faltando_no_fim_casa_pela_regra_fraca(self) -> None:
        """`CAMILA RODRIGUES` sozinha valia 80 horas sem custo."""

        candidatos = [("a", partes_do_nome("CAMILA RODRIGUES DE ALMEIDA"))]

        assert casar(partes_do_nome("CAMILA RODRIGUES"), candidatos) == "a"

    def test_empate_nao_casa(self) -> None:
        """Chutar aqui atribui o salário de uma pessoa ao cliente de outra."""

        candidatos = [
            ("a", partes_do_nome("ANA PAULA WOLFF")),
            ("b", partes_do_nome("ANA CRISTINA WOLFF")),
        ]

        assert casar(partes_do_nome("ANA WOLFF"), candidatos) is None
        # Mas a tela recebe os dois, que é onde o operador precisa decidir.
        assert set(sugerir(partes_do_nome("ANA WOLFF"), candidatos)) == {"a", "b"}

    def test_regra_forte_vence_a_fraca_sem_consultar_a_segunda(self) -> None:
        candidatos = [
            ("forte", partes_do_nome("ANA PAULA WOLFF")),
            ("fraca", partes_do_nome("ANA PAULA MOTA")),
        ]

        assert casar(partes_do_nome("ANA PAULA WOLFF"), candidatos) == "forte"

    def test_primeiro_nome_solto_nao_casa(self) -> None:
        """`LUIS`, `GERENTE`: casaria com qualquer homônimo, e nem sempre é pessoa."""

        candidatos = [("a", partes_do_nome("LUIS FERNANDO SOUZA"))]

        assert casar(partes_do_nome("LUIS"), candidatos) is None
        assert casar(partes_do_nome("GERENTE"), candidatos) is None

    def test_sem_candidatos_ou_sem_partes_devolve_nada(self) -> None:
        assert casar(partes_do_nome("ANA WOLFF"), []) is None
        assert casar([], [("a", ["ANA", "WOLFF"])]) is None


class VinculoTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Escritório", slug="escritorio")
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria", dominio_code="1"
        )

    def _usuario(self, login: str, nome: str, **kwargs: object) -> UsuarioErp:
        return UsuarioErp.objects.create(
            organization=self.office, i_usuario=login, nome=nome, **kwargs
        )

    def _horas(self, usuario: UsuarioErp, marca: str) -> RegistroHoras:
        return RegistroHoras.objects.create(
            organization=self.office,
            empresa=self.company,
            usuario_erp=usuario,
            colaborador=None,
            competencia="2026-09",
            data="2026-09-10",
            origem=OrigemHoras.AUTOMATICA,
            duracao_minutos=90,
            source_content_hash=marca * 64,
        )

    def test_vincular_corrige_as_horas_ja_gravadas(self) -> None:
        """Consertar o vínculo não conserta sozinho as horas que já estão no banco."""

        pessoa = Colaborador.objects.create(
            organization=self.office, codigo="A", nome="Ana Paula Velho Wolff"
        )
        usuario = self._usuario("ANA.W", "Ana Paula Wolff")
        registro = self._horas(usuario, "a")

        competencias = vincular_usuarios_pendentes(self.office)

        usuario.refresh_from_db()
        registro.refresh_from_db()
        assert usuario.colaborador_id == pessoa.id
        assert registro.colaborador_id == pessoa.id
        assert competencias == {"2026-09"}

    def test_o_que_o_operador_decidiu_sobrevive_ao_ciclo_seguinte(self) -> None:
        """Reescrever o vínculo manual desfaria a correção dele no dia seguinte."""

        certa = Colaborador.objects.create(organization=self.office, codigo="A", nome="Ana Wolff")
        outra = Colaborador.objects.create(organization=self.office, codigo="B", nome="Bia Mota")
        usuario = self._usuario("ANA.W", "Ana Wolff")
        aplicar_vinculo(usuario, outra.id, manual=True)

        vincular_usuarios_pendentes(self.office)

        usuario.refresh_from_db()
        assert usuario.colaborador_id == outra.id
        assert usuario.colaborador_id != certa.id

    def test_desvincular_limpa_tambem_as_horas(self) -> None:
        pessoa = Colaborador.objects.create(organization=self.office, codigo="A", nome="Ana Wolff")
        usuario = self._usuario("ANA.W", "Ana Wolff")
        registro = self._horas(usuario, "a")
        aplicar_vinculo(usuario, pessoa.id, manual=True)

        competencias = aplicar_vinculo(usuario, None, manual=True)

        registro.refresh_from_db()
        assert registro.colaborador_id is None
        assert competencias == {"2026-09"}

    def test_o_casamento_e_auto_corretivo_quando_a_folha_chega_depois(self) -> None:
        """O ciclo lê usuários antes de salários: na primeira carga ninguém existe."""

        usuario = self._usuario("ANA.W", "Ana Paula Wolff")
        assert vincular_usuarios_pendentes(self.office) == set()
        usuario.refresh_from_db()
        assert usuario.colaborador_id is None

        pessoa = Colaborador.objects.create(
            organization=self.office, codigo="A", nome="Ana Paula Velho Wolff"
        )
        vincular_usuarios_pendentes(self.office)

        usuario.refresh_from_db()
        assert usuario.colaborador_id == pessoa.id

    def test_colaborador_inativo_nao_e_candidato(self) -> None:
        Colaborador.objects.create(
            organization=self.office, codigo="A", nome="Ana Paula Wolff", ativo=False
        )
        usuario = self._usuario("ANA.W", "Ana Paula Wolff")

        vincular_usuarios_pendentes(self.office)

        usuario.refresh_from_db()
        assert usuario.colaborador_id is None

    def test_o_casamento_nao_atravessa_escritorios(self) -> None:
        vizinho = Organization.objects.create(name="Vizinho", slug="vizinho")
        Colaborador.objects.create(organization=vizinho, codigo="A", nome="Ana Paula Wolff")
        usuario = self._usuario("ANA.W", "Ana Paula Wolff")

        vincular_usuarios_pendentes(self.office)

        usuario.refresh_from_db()
        assert usuario.colaborador_id is None
