"""As quatro ferramentas do Contraprova: arquivos que cada uma pede e abas do resultado.

É dado puro (sem Django) para que o motor, a tela e os relatórios concordem sobre nomes,
papéis de arquivo e em que aba cai cada tipo de achado.
"""

from __future__ import annotations

from dataclasses import dataclass

from .findings import DIVERGENT, IGNORED, INFO, Kind

SPED_XML = "sped_xml"
SPED_SPED = "sped_sped"
ICMS51 = "icms51"
UF_DOMINIO = "uf_dominio"


@dataclass(frozen=True)
class RoleDef:
    code: str
    label: str
    #: efd | xml | dominio
    kind: str
    minimum: int
    maximum: int
    accept: str


@dataclass(frozen=True)
class TabDef:
    code: str
    label: str
    kinds: tuple[str, ...] = ()
    statuses: tuple[str, ...] = (DIVERGENT, INFO)


@dataclass(frozen=True)
class ToolDef:
    code: str
    label: str
    #: Nome curto na lista e no seletor.
    short: str
    roles: tuple[RoleDef, ...]
    tabs: tuple[TabDef, ...]
    left_label: str
    right_label: str
    #: A ferramenta lê SPED, então o CNPJ do arquivo é o da empresa para decidir a direção.
    uses_sped: bool

    def role(self, code: str) -> RoleDef:
        for item in self.roles:
            if item.code == code:
                return item
        raise KeyError(code)

    def tab(self, code: str) -> TabDef:
        for item in self.tabs:
            if item.code == code:
                return item
        return self.tabs[0]


_XML_ROLE = RoleDef("xml", "XML", "xml", 1, 200, ".xml,.zip")

TOOLS: dict[str, ToolDef] = {
    SPED_XML: ToolDef(
        code=SPED_XML,
        label="SPED x XML",
        short="SPED x XML",
        roles=(RoleDef("sped", "SPED", "efd", 1, 3, ".txt"), _XML_ROLE),
        tabs=(
            TabDef(
                "divergencias",
                "Divergências",
                (
                    Kind.VALOR_DIVERGENTE,
                    Kind.SITUACAO_DIVERGENTE,
                    Kind.CHAVE_DUPLICADA,
                    Kind.CHAVE_INVALIDA,
                ),
            ),
            TabDef("so_sped", "Só no SPED", (Kind.SEM_XML,)),
            TabDef("so_xml", "Só no XML", (Kind.XML_NAO_ESCRITURADO,)),
            TabDef("ignoradas", "Ignoradas", (), (IGNORED,)),
        ),
        left_label="SPED",
        right_label="XML",
        uses_sped=True,
    ),
    SPED_SPED: ToolDef(
        code=SPED_SPED,
        label="SPED x SPED",
        short="SPED x SPED",
        roles=(
            RoleDef("sped1", "SPED 1", "efd", 1, 1, ".txt"),
            RoleDef("sped2", "SPED 2", "efd", 1, 1, ".txt"),
        ),
        tabs=(
            TabDef(
                "divergencias",
                "Divergências",
                (
                    Kind.VALOR_DIVERGENTE,
                    Kind.ANALITICO_VALOR,
                    Kind.ANALITICO_SOMENTE_1,
                    Kind.ANALITICO_SOMENTE_2,
                    Kind.CHAVE_DUPLICADA,
                    Kind.CHAVE_INVALIDA,
                ),
            ),
            TabDef("so_1", "Só no SPED 1", (Kind.SOMENTE_1,)),
            TabDef("so_2", "Só no SPED 2", (Kind.SOMENTE_2,)),
        ),
        left_label="SPED 1",
        right_label="SPED 2",
        uses_sped=True,
    ),
    ICMS51: ToolDef(
        code=ICMS51,
        label="ICMS 51",
        short="ICMS 51",
        roles=(RoleDef("sped", "SPED", "efd", 1, 3, ".txt"), _XML_ROLE),
        tabs=(
            TabDef("chaves", "Chaves", (Kind.ICMS51_CHAVE,)),
            TabDef("inconsistencias", "Inconsistências", (Kind.ICMS51_ARITMETICA,)),
            TabDef("sem_xml", "Sem XML", (Kind.SEM_XML,)),
        ),
        left_label="SPED",
        right_label="XML",
        uses_sped=True,
    ),
    UF_DOMINIO: ToolDef(
        code=UF_DOMINIO,
        label="UF x Domínio",
        short="UF x Domínio",
        roles=(_XML_ROLE, RoleDef("dominio", "Domínio", "dominio", 0, 1, ".csv,.xlsx")),
        tabs=(
            TabDef("divergem", "UF diferente", (Kind.UF_DIVERGENTE,)),
            TabDef("sem_dominio", "Sem Domínio", (Kind.AUSENTE_DOMINIO,)),
            TabDef("sem_uf", "Sem UF", (Kind.SEM_UF_XML,)),
        ),
        left_label="XML",
        right_label="Domínio",
        uses_sped=False,
    ),
}


def choices() -> list[tuple[str, str]]:
    return [(item.code, item.label) for item in TOOLS.values()]
