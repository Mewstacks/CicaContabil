"""Casa o login do ERP com a pessoa da folha, por nome aproximado.

A hora chega pelo login do Domínio (`UsuarioErp`); o custo por hora vem da folha
do Siescon (`Colaborador`). Sem o vínculo entre os dois a hora existe e não gera
custo, e a margem do cliente infla — foi assim que meia carteira apareceu com margem
acima de 90%.

O casamento era por nome idêntico, sobre `nome_bi`, que é HMAC: `ANA PAULA WOLFF` e
`ANA PAULA VELHO WOLFF` são a mesma pessoa e digests completamente estranhos. Eram 22
de 95 usuários vinculados.

**Por que em Python e não no banco.** `Colaborador.nome` e `UsuarioErp.nome` são
`EncryptedTextField`: o que está gravado é cifra. Não existe `LIKE`, trigrama ou
similaridade possível do lado do SQL, porque o SQL não enxerga o texto. A
cardinalidade é pequena e limitada por organização — 95 usuários por 49 colaboradores
no maior escritório de hoje — então a varredura em memória é barata, e é a mesma
justificativa que o resto do código já usa para filtrar `papel` fora do banco.

**Por que aqui e não em `normalize.py`.** Aquele módulo proíbe NFKD de propósito: as
funções dele precisam reproduzir, caractere a caractere, uma cadeia de `REPLACE` do
SQL do Domínio, e dobrar mais do que o SQL dobra faria os dois lados do índice cego
discordarem. Nome de pessoa não tem essa amarra — aqui NFKD é exatamente o que se
quer. Os dois módulos existem lado a lado porque resolvem problemas opostos.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Sequence

from apps.organizations.models import Organization
from apps.profitability.models import Colaborador, RegistroHoras, UsuarioErp

# Partículas não distinguem ninguém: `JORGE DA SILVA` e `JORGE SILVA` são a mesma
# pessoa escrita por dois cadastros diferentes.
PARTICULAS = frozenset({"DA", "DE", "DO", "DAS", "DOS", "E"})

_ESPACOS = re.compile(r"\s+")
# O apostrofo some sem separar: `D'AVILA` e um sobrenome so, e virar `D` + `AVILA`
# inventaria um pedaco de uma letra. O resto da pontuacao vira espaco.
_APOSTROFOS = re.compile("['" + chr(0x2019) + "]")
_NAO_ALFANUMERICO = re.compile(r"[^A-Z0-9]+")


def partes_do_nome(nome: str) -> list[str]:
    """Nome em pedaços comparáveis: sem acento, em maiúsculas, sem partículas.

    `José  da Silva` e `JOSE SILVA` devolvem os mesmos pedaços. Um nome que só tenha
    partículas devolve lista vazia, e o chamador trata isso como "não dá para casar".

    A pontuação sai porque o cadastro tem. Os nomes que vêm do Siescon chegam com
    preenchimento e uma vírgula no fim — `"DENISE MOTA               ,"` —, e sem
    limpar isso a vírgula vira um pedaço do nome e ocupa a posição de último
    sobrenome, justamente a que a regra forte compara. O casamento até acontecia,
    mas pela regra fraca e pelo motivo errado.
    """

    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    sem_pontuacao = _NAO_ALFANUMERICO.sub(" ", _APOSTROFOS.sub("", sem_acento.upper()))
    limpo = _ESPACOS.sub(" ", sem_pontuacao.strip())
    return [parte for parte in limpo.split(" ") if parte and parte not in PARTICULAS]


def sugerir[K](partes_usuario: list[str], candidatos: Sequence[tuple[K, list[str]]]) -> list[K]:
    """Todos os candidatos da regra mais forte que alcançou alguém.

    É o que `casar` viu antes de decidir. Existe para a tela: num empate, mostrar os
    dois nomes que disputaram poupa o operador de procurar a pessoa numa lista de 49,
    e é justamente no empate que ele precisa decidir.
    """

    if not partes_usuario:
        return []

    primeiro, ultimo = partes_usuario[0], partes_usuario[-1]
    sobrenomes = set(partes_usuario[1:])

    fortes = [
        chave
        for chave, partes in candidatos
        if partes and partes[0] == primeiro and partes[-1] == ultimo
    ]
    if fortes:
        return fortes
    return [
        chave
        for chave, partes in candidatos
        if partes and partes[0] == primeiro and sobrenomes & set(partes[1:])
    ]


def casar[K](partes_usuario: list[str], candidatos: Sequence[tuple[K, list[str]]]) -> K | None:
    """A chave do único candidato que serve, ou `None`.

    Duas regras, da mais forte para a mais fraca:

    1. **Primeiro nome e último sobrenome iguais.** Pega o nome do meio que falta de
       um lado -- `ANA PAULA WOLFF` contra `ANA PAULA VELHO WOLFF`.
    2. **Primeiro nome igual e algum sobrenome em comum.** Pega o sobrenome que falta
       no fim -- `CAMILA RODRIGUES` contra `CAMILA RODRIGUES DE ALMEIDA`, que sozinha
       valia 80 horas sem custo.

    `None` também quando há mais de um candidato. Empate não é um casamento fraco: é
    a informação de que o nome não basta para decidir, e chutar aqui atribui o salário
    de uma pessoa ao cliente de outra. Esses ficam para a decisão do operador, que os
    recebe como sugestão -- ver `sugerir`.

    Um usuário de um pedaço só (`LUIS`, `GERENTE`) não casa pela regra 2, que exige um
    sobrenome em comum. É de propósito: primeiro nome solto casaria com qualquer
    homônimo da folha, e boa parte desses logins nem é pessoa.
    """

    achados = sugerir(partes_usuario, candidatos)
    return achados[0] if len(achados) == 1 else None


def aplicar_vinculo(
    usuario: UsuarioErp, colaborador_id: uuid.UUID | None, *, manual: bool
) -> set[str]:
    """Liga (ou desliga) o usuário e devolve as competências que precisam ser refeitas.

    O passo fácil de esquecer é o segundo. `RegistroHoras.colaborador` é gravado na
    ingestão, copiado do usuário naquele instante -- consertar o vínculo não conserta
    as horas que já estão no banco, e sem o backfill `recompute_competencia` continua
    vendo `colaborador_id` nulo e a tela não muda. São 6.717 linhas no Fedrizzi.

    Quem chama é que reprojeta: esta função não importa `recompute_competencia` para
    não amarrar o cadastro ao módulo de cálculo, e porque os dois caminhos que a usam
    já têm o seu jeito de reprojetar -- o `process_run` acumula as competências e
    refaz todas de uma vez no fim, a API usa `reprojetar`.
    """

    usuario.colaborador_id = colaborador_id
    usuario.vinculo_manual = manual
    usuario.save(update_fields=("colaborador", "vinculo_manual", "updated_at"))

    linhas = RegistroHoras.objects.filter(
        organization_id=usuario.organization_id, usuario_erp=usuario
    )
    competencias = set(linhas.values_list("competencia", flat=True).distinct())
    if competencias:
        linhas.update(colaborador_id=colaborador_id)
    return competencias


def vincular_usuarios_pendentes(organization: Organization) -> set[str]:
    """Casa quem ainda não tem colaborador e devolve as competências tocadas.

    Roda no fim de todo run de ingestão, e é isso que a torna auto-corretiva. Antes o
    vínculo era resolvido dentro do `_upsert_user`, no instante em que o dataset
    `users` era processado -- e o `SYNC_CYCLE` roda `users` **antes** de `salaries`.
    Na primeira carga de uma organização nenhum colaborador existe ainda, o vínculo
    saía nulo e nada nunca reexecutava o casamento. Era uma segunda causa raiz,
    independente do nome: nem nome idêntico vinculava.

    `vinculo_manual` fica de fora: o que o operador decidiu não é chute de matcher, e
    reescrevê-lo a cada sync desfaria a correção dele no dia seguinte.
    """

    pendentes = list(
        UsuarioErp.objects.filter(
            organization=organization, colaborador__isnull=True, vinculo_manual=False
        )
    )
    if not pendentes:
        return set()

    candidatos = [
        (colaborador.id, partes_do_nome(colaborador.nome))
        for colaborador in Colaborador.objects.filter(organization=organization, ativo=True)
    ]
    if not candidatos:
        return set()

    competencias: set[str] = set()
    for usuario in pendentes:
        escolhido = casar(partes_do_nome(usuario.nome), candidatos)
        if escolhido is not None:
            competencias |= aplicar_vinculo(usuario, escolhido, manual=False)
    return competencias
