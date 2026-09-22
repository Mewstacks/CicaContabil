"""Declarative catalogue of the guided first-use orientation.

Keeping the tours here, instead of spreading copy and selectors through templates,
means one place decides what each area teaches, which roles see it and when a flow
changed enough to show it again. Only the identifier, the version, the role and the
completion state ever reach the browser; no fiscal content lives in this file.

A tour is anchored to a URL name so the orientation only opens on the main screen of
an area — never on a detail page, a confirmation or a form someone already started.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.organizations.models import Membership


@dataclass(frozen=True)
class TourStep:
    title: str
    body: str


@dataclass(frozen=True)
class Tour:
    identifier: str
    version: int
    label: str
    title: str
    steps: tuple[TourStep, ...]
    url_names: frozenset[str]
    roles: frozenset[str] | None = None

    def visible_for(self, role: str | None) -> bool:
        if self.roles is None:
            return True
        return role is not None and role in self.roles


WELCOME = Tour(
    identifier="welcome",
    version=1,
    label="Como usar a CICA",
    title="Bem-vindo à CICA",
    steps=(
        TourStep(
            "A pauta do dia",
            "A Visão geral abre com o que exige atenção: pendências por área, com empresa, "
            "causa e há quanto tempo estão paradas.",
        ),
        TourStep(
            "Navegação",
            "O menu superior agrupa Cadastros, Fiscal, Contábil, Documentos e Configurações. "
            "O escritório em foco fica sempre no topo, ao lado do seu nome.",
        ),
        TourStep(
            "Ajuda quando precisar",
            "O botão “Como usar” repete esta orientação em qualquer área. Nenhuma ação é "
            "executada por ele.",
        ),
    ),
    url_names=frozenset({"dashboard"}),
)

MODULE_TOURS: tuple[Tour, ...] = (
    Tour(
        identifier="nfse",
        version=1,
        label="Como usar as NFS-e",
        title="NFS-e Inteligente",
        steps=(
            TourStep(
                "O que esta área faz",
                "Reúne as notas disponibilizadas à CICA, a fila de revisão e a coleta "
                "automática por empresa.",
            ),
            TourStep(
                "Onde está o trabalho",
                "A aba Revisões lista o que espera decisão. A situação de cada linha separa "
                "sugestão da CICA de decisão tomada por pessoa.",
            ),
            TourStep(
                "Como concluir",
                "Abra “Conferir e decidir”, escolha o acumulador do catálogo da empresa e "
                "registre a decisão. Ela passa a valer como decisão humana.",
            ),
        ),
        url_names=frozenset({"nfse-center", "reviews"}),
    ),
    Tour(
        identifier="guides",
        version=1,
        label="Como usar Guias e DCTFWeb",
        title="Guias e DCTFWeb",
        steps=(
            TourStep(
                "O que esta área faz",
                "Separa a apuração vinda do Domínio, a declaração DCTFWeb conferida na fonte "
                "oficial e a guia emitida.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Os filtros de situação e vencimento reduzem a carteira. Cada linha mostra "
                "empresa, competência e valor.",
            ),
            TourStep(
                "Como concluir",
                "A emissão só é liberada depois da declaração e do recibo conferidos, e a "
                "confirmação mostra o consumo antes de enviar.",
            ),
        ),
        url_names=frozenset({"guides"}),
    ),
    Tour(
        identifier="dte",
        version=1,
        label="Como usar a Caixa DTE",
        title="Caixa Postal DTE",
        steps=(
            TourStep(
                "O que esta área faz",
                "Mostra as mensagens da Caixa Postal por empresa, com a idade de cada uma.",
            ),
            TourStep(
                "Onde está o trabalho",
                "O filtro de situação separa sem leitura, abertura pendente e resultado incerto.",
            ),
            TourStep(
                "Antes de abrir",
                "Abrir o teor de uma intimação pode registrar ciência e iniciar prazo. A CICA "
                "pede confirmação explícita antes disso.",
            ),
        ),
        url_names=frozenset({"dte-center"}),
    ),
    Tour(
        identifier="parcelamentos",
        version=1,
        label="Como usar Parcelamentos",
        title="Parcelamentos",
        steps=(
            TourStep(
                "O que esta área faz",
                "Acompanha pedidos, consolidação, parcelas e DAS do Simples Nacional.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Selecione as empresas da carteira; as ações em lote aparecem depois da "
                "seleção, com o consumo estimado.",
            ),
            TourStep(
                "Como concluir",
                "Um resultado incerto bloqueia nova emissão até conferência humana, e o PDF "
                "já emitido é reaproveitado.",
            ),
        ),
        url_names=frozenset({"parcelamentos"}),
    ),
    Tour(
        identifier="reconciliation",
        version=1,
        label="Como usar a Conciliação",
        title="Conciliação OFX x Domínio",
        steps=(
            TourStep(
                "O que esta área faz",
                "Segue a ordem fonte, prévia, processamento, revisão e exportação, com os dois "
                "lados sempre visíveis.",
            ),
            TourStep(
                "Onde está o trabalho",
                "A fila de movimentos começa pelas ambiguidades e pelos lançamentos sem "
                "correspondência.",
            ),
            TourStep(
                "Como concluir",
                "Confirmar, rejeitar ou agrupar registra autoria e horário na auditoria; a "
                "exportação mostra totais e exceções restantes.",
            ),
        ),
        url_names=frozenset({"reconciliation"}),
    ),
    Tour(
        identifier="triage",
        version=1,
        label="Como usar a Triagem",
        title="Triagem de arquivos",
        steps=(
            TourStep(
                "O que esta área faz",
                "Recebe anexos das caixas conectadas e leva cada um de recebido a arquivado.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Quarentena e falha de identificação vêm primeiro: arquivo sem verificação de "
                "segurança não é baixado nem arquivado.",
            ),
            TourStep(
                "Como concluir",
                "Na revisão, confirme empresa, tipo e período. O destino Windows mostra a "
                "saúde do agente e a prova da gravação.",
            ),
        ),
        url_names=frozenset({"triage"}),
    ),
    Tour(
        identifier="reform",
        version=1,
        label="Como usar o Radar",
        title="Radar da Reforma",
        steps=(
            TourStep(
                "O que esta área faz",
                "Lista publicações coletadas das fontes oficiais, com data de publicação e de "
                "coleta.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Filtre por termo, fonte, tema e período. A saúde das fontes mostra a última "
                "coleta de cada uma.",
            ),
            TourStep(
                "O limite",
                "Tudo aqui é publicação coletada, não interpretação fiscal validada. Abra a "
                "fonte antes de orientar o cliente.",
            ),
        ),
        url_names=frozenset({"reform"}),
    ),
    Tour(
        identifier="copilot",
        version=1,
        label="Como usar o Copiloto",
        title="Copiloto CICA",
        steps=(
            TourStep(
                "O que esta área faz",
                "Responde sobre uma empresa por vez, usando o contexto autorizado do escritório.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Escolha a empresa antes de perguntar; o histórico de conversas fica na lateral.",
            ),
            TourStep(
                "O limite",
                "Toda resposta é rascunho para conferência, com as fontes usadas. A CICA não "
                "altera o Domínio.",
            ),
        ),
        url_names=frozenset({"assistant"}),
    ),
    Tour(
        identifier="companies",
        version=1,
        label="Como usar a carteira",
        title="Empresas",
        steps=(
            TourStep(
                "O que esta área faz",
                "Reúne a carteira do escritório com certificado e revisões abertas por empresa.",
            ),
            TourStep(
                "Onde está o trabalho",
                "Os filtros de certificado e de pendência mostram quem precisa de ação antes "
                "do fechamento.",
            ),
            TourStep(
                "Como concluir",
                "Abrir a empresa reúne documentos, revisões, DTE e histórico em um lugar só.",
            ),
        ),
        url_names=frozenset({"companies"}),
        roles=frozenset(
            {
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
                Membership.Role.OPERATOR,
                Membership.Role.AUDITOR,
            }
        ),
    ),
)

ALL_TOURS: tuple[Tour, ...] = (WELCOME, *MODULE_TOURS)
TOURS_BY_ID = {tour.identifier: tour for tour in ALL_TOURS}


def tour_for_url_name(url_name: str | None) -> Tour | None:
    """Return the orientation anchored to a main screen, or nothing."""

    if not url_name:
        return None
    for tour in ALL_TOURS:
        if url_name in tour.url_names:
            return tour
    return None
