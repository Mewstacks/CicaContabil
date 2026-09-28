"""Aplica ao cadastro as linhas que o agente leu do ERP do escritório.

Portado do Lucrums por D-108, com duas diferenças estruturais.

A primeira é D-109: onde a origem criava uma `Empresa` própria, aqui a linha do
ERP é resolvida contra a carteira do hub. A ordem de busca é código do ERP,
depois índice cego do documento, depois o `dominio_code` que a carteira já possa
ter — porque a empresa pode já estar cadastrada pela NFS-e ou pela conciliação, e
criar uma segunda seria exatamente a duplicação que a decisão evitou. Só quando
nada disso encontra é que nasce uma `ClientCompany`.

A segunda é D-114: o transporte é o do agente da CICA, mTLS com assinatura do
corpo, então as páginas chegam em claro pelo canal autenticado e ficam cifradas em
repouso pelo campo da própria CICA, sem um segundo sistema de chaves.

O resto é o da origem, inclusive as três regras que sustentam a confiabilidade do
ciclo: a identidade da linha é o hash do conteúdo com um ordinal para linhas
repetidas legítimas; nada é apagado, só marcado como removido pela reconciliação
da janela; e uma linha que não casa com o cadastro é pulada dentro de um orçamento
de rejeição, mas um ciclo que rejeitou tudo falha — foi assim que um `users` de 44
linhas reportou sucesso sem gravar ninguém.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.common.encryption import blind_index
from apps.hub.models import ClientCompany, OfficeProfile
from apps.organizations.models import Organization
from apps.profitability.catalog import DatasetDefinition, load_catalog
from apps.profitability.matching import vincular_usuarios_pendentes
from apps.profitability.models import (
    Colaborador,
    CompanyErpProfile,
    Competencia,
    EventoFaturamento,
    IngestBatch,
    IngestRun,
    Mensalidade,
    OrigemHoras,
    RegistroHoras,
    SalarioColaborador,
    ServicoFaturado,
    SistemaOrigem,
    StatusCorrespondencia,
    UsuarioErp,
)
from apps.profitability.normalize import only_digits, strip_accents_upper
from apps.profitability.services import competencia_seguinte, recompute_competencia

REGIMES_TRIBUTARIOS = {
    1: "Lucro Real",
    2: "Microempresa",
    4: "Empresa de Pequeno Porte (EPP)",
    5: "Lucro Presumido",
    6: "Regime Especial de Tributação",
    8: "Imune do IRPJ",
    9: "Isenta do IRPJ",
}

# Linhas de origem que não casam com o cadastro são puladas, não fatais: o ERP
# sempre tem sobras — empresas fora do cadastro principal, sessões truncadas — e
# derrubar um ciclo de centenas de milhares de linhas por causa de uma delas
# deixaria a carteira permanentemente desatualizada. Acima destes limites a
# hipótese muda: não é sobra, é contrato errado, e o ciclo falha.
REJECTION_ABSOLUTE_LIMIT = 100
REJECTION_RATE_LIMIT = 0.01
REJECTION_SAMPLE_SIZE = 20

# Tamanho do lote dos upserts de horas. Alto o bastante para o custo por linha
# sumir, baixo o bastante para a lista de objetos pendentes não pesar na memória
# do worker num ciclo de 500 mil linhas.
HOURS_FLUSH_SIZE = 1000


def _content_hash(dataset_code: str, row: dict[str, Any]) -> str:
    canonical = json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(dataset_code.encode() + b"\0" + canonical).hexdigest()


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Campo {field_name} inválido.")
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo {field_name} inválido.") from exc


def _as_decimal(value: object, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"Campo {field_name} inválido.") from exc


def _as_login(value: object, field_name: str) -> str:
    """O identificador de usuário do ERP é texto, não número.

    Tratá-lo como inteiro rejeitava toda linha de horas — e, porque as rejeições
    cabiam no orçamento do conjunto pequeno de usuários, o ciclo reportava
    sucesso sem gravar ninguém.
    """

    if value is None:
        raise ValueError(f"Campo {field_name} inválido.")
    login = str(value).strip()
    if not login or len(login) > 64:
        raise ValueError(f"Campo {field_name} inválido.")
    return login


def _as_date(value: object, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo {field_name} inválido.") from exc


def _as_time(value: object, field_name: str) -> time:
    if isinstance(value, time):
        return value
    try:
        return time.fromisoformat(str(value)[:8])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo {field_name} inválido.") from exc


def _competencia(value: object) -> str:
    texto = str(value)[:7]
    try:
        ano, mes = (int(parte) for parte in texto.split("-"))
    except ValueError as exc:
        raise ValueError("Competência inválida.") from exc
    if not 1 <= mes <= 12 or not 1900 <= ano <= 2999:
        raise ValueError("Competência inválida.")
    return f"{ano:04d}-{mes:02d}"


def _parameter_map(run: IngestRun) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in run.parameters:
        if not isinstance(item, dict) or set(item) != {"name", "value"}:
            raise ValueError("Parâmetros da execução inválidos.")
        result[str(item["name"])] = item["value"]
    return result


def _window_competencias(run: IngestRun) -> set[str]:
    """Competências cobertas pela janela de datas, mesmo sem linha nenhuma.

    Um ciclo completo que reconcilia uma janela que ficou vazia na fonte precisa
    recomputar essas competências; sem isso, métricas e mensalidades antigas
    continuariam na tela depois de o dado sumir.
    """

    parameters = _parameter_map(run)
    if "start_date" not in parameters or "end_date" not in parameters:
        return set()
    start = _as_date(parameters["start_date"], "start_date")
    end = _as_date(parameters["end_date"], "end_date")
    result: set[str] = set()
    ano, mes = start.year, start.month
    while (ano, mes) <= (end.year, end.month):
        result.add(f"{ano:04d}-{mes:02d}")
        if len(result) > 36:
            raise ValueError("Janela da execução excede 36 competências.")
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1
    return result


@dataclass
class _RunContext:
    """Dados de referência da execução, carregados uma vez em vez de por linha.

    Sem isto, cada linha de origem custava quatro consultas — empresa, usuário,
    competência e o upsert. Com um teto de 500 mil linhas para as horas, nenhum
    ciclo real cabia no limite de tempo da tarefa. O cadastro que uma linha
    consulta é pequeno e limitado por escritório, então vive aqui pelo tempo do
    ciclo.
    """

    run: IngestRun
    perfis_por_codi: dict[int, CompanyErpProfile] = field(default_factory=dict)
    perfis_por_documento: dict[str, list[CompanyErpProfile]] = field(default_factory=dict)
    perfis_por_razao: dict[str, list[CompanyErpProfile]] = field(default_factory=dict)
    usuarios: dict[str, UsuarioErp] = field(default_factory=dict)
    competencias: set[str] = field(default_factory=set)
    horas_pendentes: list[RegistroHoras] = field(default_factory=list)
    exige_dominio_code: bool = False

    @property
    def organization(self) -> Organization:
        return self.run.organization

    def remember_company(self, perfil: CompanyErpProfile) -> None:
        if perfil.codi_emp is not None:
            self.perfis_por_codi[perfil.codi_emp] = perfil
        if perfil.documento_bi:
            perfis = self.perfis_por_documento.setdefault(perfil.documento_bi, [])
            if all(existente.pk != perfil.pk for existente in perfis):
                perfis.append(perfil)
        if perfil.razao_normalizada_bi:
            perfis = self.perfis_por_razao.setdefault(perfil.razao_normalizada_bi, [])
            if all(existente.pk != perfil.pk for existente in perfis):
                perfis.append(perfil)

    def company_by_codi(
        self, codi_emp: int, *, active_only: bool = False
    ) -> CompanyErpProfile | None:
        perfil = self.perfis_por_codi.get(codi_emp)
        if perfil is not None and active_only and perfil.deleted_at is not None:
            return None
        return perfil

    def user(self, i_usuario: str) -> UsuarioErp | None:
        return self.usuarios.get(i_usuario)

    def remember_user(self, user: UsuarioErp) -> None:
        self.usuarios[user.i_usuario] = user

    def ensure_competencia(self, value: str) -> None:
        if value in self.competencias:
            return
        ano, mes = (int(parte) for parte in value.split("-"))
        Competencia.objects.get_or_create(
            organization=self.organization,
            competencia=value,
            defaults={
                "inicio": date(ano, mes, 1),
                "fim": date(ano, mes, calendar.monthrange(ano, mes)[1]),
            },
        )
        self.competencias.add(value)

    def queue_hours(self, registro: RegistroHoras) -> None:
        self.horas_pendentes.append(registro)
        if len(self.horas_pendentes) >= HOURS_FLUSH_SIZE:
            self.flush_hours()

    def flush_hours(self) -> None:
        """Grava as horas pendentes num único comando de inserção com atualização.

        A chave natural é `(organization, source_content_hash, occurrence_index)`,
        a mesma que o upsert linha a linha usava, então repetir um ciclo continua
        convergindo em vez de duplicar.
        """

        if not self.horas_pendentes:
            return
        RegistroHoras.objects.bulk_create(
            self.horas_pendentes,
            update_conflicts=True,
            unique_fields=("organization", "source_content_hash", "occurrence_index"),
            update_fields=(
                "empresa",
                "colaborador",
                "usuario_erp",
                "competencia",
                "data",
                "origem",
                "inicio",
                "fim",
                "data_fim",
                "duracao_minutos",
                "descricao",
                "last_seen_run",
                "deleted_at",
                "updated_at",
            ),
        )
        self.horas_pendentes.clear()


def _build_context(run: IngestRun) -> _RunContext:
    """Carrega o cadastro que esta execução pode tocar — o do ERP que ela lê.

    O recorte por sistema de origem é o que mantém os dois ERPs independentes:
    `codi_emp` e o login só são únicos dentro de um sistema, então um ciclo do
    Siescon que enxergasse o cadastro do Domínio casaria a empresa 25 de um com a
    25 do outro e sobrescreveria razão social, documento e regime.
    """

    context = _RunContext(run=run)
    for perfil in CompanyErpProfile.objects.select_related("empresa").filter(
        organization=run.organization, sistema_origem=run.source_system
    ):
        context.remember_company(perfil)
    for user in UsuarioErp.objects.filter(
        organization=run.organization, sistema_origem=run.source_system
    ).select_related("colaborador"):
        context.remember_user(user)
    context.competencias = set(
        Competencia.objects.filter(organization=run.organization).values_list(
            "competencia", flat=True
        )
    )
    context.exige_dominio_code = OfficeProfile.objects.filter(
        organization=run.organization, require_dominio_code=True
    ).exists()
    return context


def _resolver_carteira(
    context: _RunContext, *, codi_emp: int, documento_bi: str, name: str
) -> ClientCompany:
    """Acha na carteira do hub a empresa desta linha, ou cria uma.

    É aqui que D-109 deixa de ser desenho e vira comportamento. A empresa pode já
    estar cadastrada pela NFS-e, pela conciliação ou à mão, e criar uma segunda
    seria a duplicação que a decisão existe para evitar. A ordem de busca vai do
    identificador mais forte ao mais fraco: o código do Domínio, que a carteira já
    guarda em `dominio_code` e sobre o qual há constraint única; depois o índice
    cego do documento, através de um perfil de ERP que já o tenha.

    Só o Domínio escreve `dominio_code`. O Siescon numera o seu próprio cadastro,
    e gravar esse número no campo que NFS-e, conciliação e DTE usam para casar
    empresa faria uma delas achar a empresa errada.
    """

    do_dominio = context.run.source_system == SistemaOrigem.DOMINIO
    codigo = str(codi_emp)

    if do_dominio:
        existente = ClientCompany.objects.filter(
            organization=context.organization, dominio_code=codigo
        ).first()
        if existente is not None:
            return existente

    if documento_bi:
        # Documento não é uma chave única do cadastro do ERP: matriz e filial
        # podem vir com o mesmo valor. Só um perfil ainda sem código pode ser
        # associado a uma linha nova por esse identificador.
        sem_codigo = [
            perfil
            for perfil in context.perfis_por_documento.get(documento_bi, [])
            if perfil.codi_emp is None
        ]
        if len(sem_codigo) == 1:
            return sem_codigo[0].empresa
        if len(sem_codigo) > 1:
            raise ValueError("Documento pertence a mais de uma empresa sem código ERP.")
        # O contexto do ciclo só carrega o ERP que ele lê, porque `codi_emp` e
        # login só são únicos dentro de um sistema. A gêmea do outro ERP, porém,
        # é justamente o que se procura aqui: os dois cadastram o mesmo cliente,
        # e o documento é o que os une. Sem esta consulta a empresa entraria duas
        # vezes na carteira e a deduplicação teria de esconder uma depois.
        gemeas = list(
            CompanyErpProfile.objects.filter(
                organization=context.organization, documento_bi=documento_bi
            )
            .exclude(sistema_origem=context.run.source_system)
            .select_related("empresa")
        )
        if gemeas:
            empresas_ocupadas = set(
                CompanyErpProfile.objects.filter(
                    organization=context.organization,
                    sistema_origem=context.run.source_system,
                    empresa_id__in=[gemea.empresa_id for gemea in gemeas],
                ).values_list("empresa_id", flat=True)
            )
            elegiveis = [g for g in gemeas if g.empresa_id not in empresas_ocupadas]
            nome_normalizado = strip_accents_upper(name)
            por_nome = [
                gemea
                for gemea in elegiveis
                if strip_accents_upper(gemea.empresa.name) == nome_normalizado
            ]
            if len(por_nome) == 1:
                return por_nome[0].empresa
            if len(elegiveis) == 1:
                return elegiveis[0].empresa
            if len(elegiveis) > 1:
                raise ValueError(
                    "Documento compartilhado por várias empresas sem gêmea inequívoca."
                )

    if not do_dominio and context.exige_dominio_code:
        # O escritório exige código Domínio em toda empresa da carteira. Criar
        # uma sem ele por um caminho que o formulário não atravessa furaria a
        # regra dele pelas costas; a linha é rejeitada e entra no orçamento.
        raise ValueError("O escritório exige código Domínio e esta empresa não tem gêmea.")

    return ClientCompany.objects.create(
        organization=context.organization,
        name=name or codigo,
        dominio_code=codigo if do_dominio else "",
    )


def _upsert_company(context: _RunContext, row: dict[str, Any]) -> CompanyErpProfile:
    run = context.run
    codi_emp = _as_int(row["codi_emp"], "codi_emp")
    document = str(row.get("cgce_emp") or "")
    name = str(row.get("razao_emp") or "").strip()
    document_digits = only_digits(document)
    document_bi = (
        blind_index(document_digits, namespace="profitability.empresa.documento")
        if document_digits
        else ""
    )
    perfil = context.company_by_codi(codi_emp)
    if perfil is None and document_bi:
        sem_codigo = [
            candidato
            for candidato in context.perfis_por_documento.get(document_bi, [])
            if candidato.codi_emp is None
        ]
        if len(sem_codigo) == 1:
            perfil = sem_codigo[0]
        elif len(sem_codigo) > 1:
            raise ValueError("Documento pertence a mais de um perfil sem código ERP.")

    if perfil is None:
        empresa = _resolver_carteira(
            context, codi_emp=codi_emp, documento_bi=document_bi, name=name
        )
        perfil = CompanyErpProfile(
            organization=run.organization,
            empresa=empresa,
            codi_emp=codi_emp,
            origem=CompanyErpProfile.Origem.DOMINIO,
            sistema_origem=run.source_system,
            documento=document,
            papel=["cliente"],
        )
    elif perfil.origem == CompanyErpProfile.Origem.DOMINIO:
        perfil.documento = document

    empresa = perfil.empresa
    # A situação vem como coluna, não como filtro na consulta, e isso é
    # deliberado: filtrando na origem a empresa inativa some do ciclo e a
    # reconciliação a marca como removida — se a semântica do código estiver
    # errada, some cadastro. Trazendo o valor, ela continua registrada e apenas
    # sai da carteira, porque a reconstrução das métricas já só olha ativas.
    #
    # Vazio conta como ativa: a ausência do dado não é prova de baixa, e o erro
    # de deixar uma inativa na lista é menor que o de esvaziar a carteira.
    situacao = str(row.get("situacao") or "").strip().upper()
    ativo = situacao in ("", "A")
    mudou: list[str] = []
    if name and perfil.origem == CompanyErpProfile.Origem.DOMINIO and empresa.name != name:
        empresa.name = name
        mudou.append("name")
    if empresa.active != ativo:
        empresa.active = ativo
        mudou.append("active")
    if mudou:
        empresa.save(update_fields=[*mudou, "updated_at"])

    perfil.codi_emp = codi_emp
    perfil.last_seen_run = run
    perfil.deleted_at = None
    perfil.save()
    context.remember_company(perfil)
    return perfil


def _upsert_taxation(context: _RunContext, row: dict[str, Any]) -> None:
    """Aplica o regime tributário vigente que a consulta escolheu para a empresa.

    A consulta já devolve uma linha por empresa — a vigência mais recente que não
    seja futura — então aqui não há o que desempatar: a linha do ciclo é a
    verdade. Uma guarda de monotonia impediria que uma correção retroativa feita
    no ERP chegasse ao sistema.
    """

    perfil = context.company_by_codi(_as_int(row["codi_emp"], "codi_emp"))
    if perfil is None:
        # O cadastro de vigências tem empresas que o cadastro principal não tem.
        raise ValueError("Empresa da tributação não está no cadastro.")
    if perfil.origem != CompanyErpProfile.Origem.DOMINIO:
        # Empresa mantida à mão: o regime é do operador, não da importação.
        return
    perfil.regime_codigo = _as_int(row["rfed_par"], "rfed_par")
    perfil.regime_vigencia = _as_date(row["vigencia_par"], "vigencia_par")
    perfil.regime = REGIMES_TRIBUTARIOS.get(
        perfil.regime_codigo, f"Código tributário {perfil.regime_codigo}"
    )
    perfil.save(update_fields=("regime", "regime_codigo", "regime_vigencia", "updated_at"))


def _upsert_user(context: _RunContext, row: dict[str, Any]) -> None:
    """Grava o usuário, e **não** resolve o colaborador dele.

    O vínculo saiu daqui de propósito. Resolvido neste ponto, ele tinha três
    defeitos: sobrescrevia a escolha manual do operador a cada ciclo; dependia de
    a folha já ter rodado, o que a ordem do ciclo garante que não aconteceu, já
    que os usuários vêm antes; e custava uma consulta por linha. Agora é uma
    passada só, no fim — `vincular_usuarios_pendentes`.
    """

    run = context.run
    user, _ = UsuarioErp.objects.update_or_create(
        organization=run.organization,
        sistema_origem=run.source_system,
        i_usuario=_as_login(row["i_usuario"], "i_usuario"),
        defaults={
            "nome": str(row["nome"]).strip(),
            "situacao": _as_int(row["situacao"], "situacao"),
            "ativo": True,
            "last_seen_run": run,
        },
    )
    context.remember_user(user)


def _duration(
    start_date: date, start_value: object, end_date: date | None, end_value: object
) -> tuple[time, time, date, int]:
    start_time = _as_time(start_value, "inicio")
    end_time = _as_time(end_value, "fim")
    resolved_end_date = end_date or start_date
    start = datetime.combine(start_date, start_time)
    end = datetime.combine(resolved_end_date, end_time)
    if end < start and end_date is None:
        end += timedelta(days=1)
        resolved_end_date = end.date()
    minutes = int((end - start).total_seconds() // 60)
    if minutes < 0 or minutes > 7 * 24 * 60:
        raise ValueError("Duração de sessão inválida.")
    return start_time, end_time, resolved_end_date, minutes


def _upsert_hours(
    context: _RunContext, row: dict[str, Any], occurrence_index: int, content_hash: str
) -> str:
    run = context.run
    perfil = context.company_by_codi(_as_int(row["codi_emp"], "codi_emp"), active_only=True)
    if perfil is None and "razao_emp" in row:
        perfil = _upsert_company(context, row)
    if perfil is None:
        raise ValueError("Empresa das horas não está no cadastro.")

    automatic = run.dataset_code == "automatic_hours"
    user_field = "usua_log" if automatic else "codi_usu"
    user = context.user(_as_login(row[user_field], user_field))
    source_date = _as_date(row["data_log" if automatic else "data_atv"], "data")
    if automatic:
        end_date = _as_date(row["dfim_log"], "dfim_log") if row.get("dfim_log") else None
        start_time, end_time, resolved_end, minutes = _duration(
            source_date, row["tini_log"], end_date, row["tfim_log"]
        )
        description = ""
        origin = OrigemHoras.AUTOMATICA
    else:
        start_time, end_time, resolved_end, minutes = _duration(
            source_date, row["hori_atv"], None, row["horf_atv"]
        )
        description = str(row.get("desc_atv") or "")
        origin = OrigemHoras.F9
    competence = source_date.strftime("%Y-%m")
    context.ensure_competencia(competence)
    context.queue_hours(
        RegistroHoras(
            organization=run.organization,
            source_content_hash=content_hash,
            occurrence_index=occurrence_index,
            empresa=perfil.empresa,
            colaborador=user.colaborador if user else None,
            usuario_erp=user,
            competencia=competence,
            data=source_date,
            origem=origin,
            inicio=start_time,
            fim=end_time,
            data_fim=resolved_end,
            duracao_minutos=minutes,
            descricao=description,
            last_seen_run=run,
            deleted_at=None,
        )
    )
    return competence


def _upsert_salary(context: _RunContext, row: dict[str, Any]) -> str:
    run = context.run
    perfil = context.company_by_codi(_as_int(row["codi_emp"], "codi_emp"))
    if perfil is None or "payroll_source" not in perfil.papel:
        raise ValueError("Fonte de folha não armada.")
    name = str(row["nome"]).strip()
    employee_id = _as_int(row["i_empregados"], "i_empregados")
    collaborator, _ = Colaborador.objects.update_or_create(
        organization=run.organization,
        empresa_folha=perfil.empresa,
        i_empregados=employee_id,
        defaults={
            "nome": name,
            "cargo": "",
            "origem": Colaborador.Origem.DOMINIO,
            "ativo": True,
            "last_seen_run": run,
        },
    )
    competence = _competencia(row["ultima_competencia"])
    context.ensure_competencia(competence)
    SalarioColaborador.objects.update_or_create(
        organization=run.organization,
        colaborador=collaborator,
        competencia=competence,
        defaults={
            "salario": _as_decimal(row["salario_mais_recente"], "salario_mais_recente"),
            "fonte": Colaborador.Origem.DOMINIO,
            "last_seen_run": run,
        },
    )
    return competence


def _upsert_billing_event(context: _RunContext, row: dict[str, Any]) -> None:
    """Descoberta: quanto cada evento de faturamento movimentou na competência.

    Exige a fonte de honorários armada, como os demais contratos de receita. Não
    devolve competência ao chamador de propósito: nada aqui entra nas métricas, e
    disparar o recálculo por causa de uma medição reescreveria a carteira inteira
    sem mudar número nenhum.
    """

    run = context.run
    source_code = _as_int(row["codi_emp_origem"], "codi_emp_origem")
    source = context.company_by_codi(source_code)
    if source is None or "billing_source" not in source.papel:
        raise ValueError("Fonte de honorários não armada.")
    ano = _as_int(row["ano_servico"], "ano_servico")
    mes = _as_int(row["mes_servico"], "mes_servico")
    EventoFaturamento.objects.update_or_create(
        organization=run.organization,
        codi_emp_origem=source_code,
        i_evento=_as_int(row["i_evento"], "i_evento"),
        competencia=_competencia(f"{ano:04d}-{mes:02d}"),
        defaults={
            "lancamentos": _as_int(row["lancamentos"], "lancamentos"),
            "total": _as_decimal(row["total"], "total"),
            "last_seen_run": run,
        },
    )


def _upsert_billing(context: _RunContext, row: dict[str, Any]) -> str:
    run = context.run
    source_code = _as_int(row["codi_emp_origem"], "codi_emp_origem")
    source = context.company_by_codi(source_code)
    if source is None or "billing_source" not in source.papel:
        raise ValueError("Fonte de honorários não armada.")
    ano = _as_int(row["ano_servico"], "ano_servico")
    mes = _as_int(row["mes_servico"], "mes_servico")
    competence = _competencia(f"{ano:04d}-{mes:02d}")
    context.ensure_competencia(competence)

    document = str(row.get("documento_cli") or "")
    document_digits = only_digits(document)
    empresa: ClientCompany | None = None
    correspondence = StatusCorrespondencia.NAO_ENCONTRADO
    if document_digits:
        perfis = (
            context.perfis_por_documento.get(
                blind_index(document_digits, namespace="profitability.empresa.documento")
            )
            or []
        )
        empresas = {perfil.empresa_id: perfil.empresa for perfil in perfis}
        if len(empresas) == 1:
            empresa = next(iter(empresas.values()))
            correspondence = StatusCorrespondencia.CPF_CNPJ
        elif len(empresas) > 1 and row.get("nome_cli"):
            nome_normalizado = strip_accents_upper(str(row["nome_cli"]))
            por_nome = [
                candidata
                for candidata in empresas.values()
                if strip_accents_upper(candidata.name) == nome_normalizado
            ]
            if len(por_nome) == 1:
                empresa = por_nome[0]
                correspondence = StatusCorrespondencia.CPF_CNPJ
    name = str(row.get("nome_cli") or "")
    if empresa is None and name:
        perfis = (
            context.perfis_por_razao.get(
                blind_index(strip_accents_upper(name), namespace="profitability.empresa.razao")
            )
            or []
        )
        empresas = {perfil.empresa_id: perfil.empresa for perfil in perfis}
        if len(empresas) == 1:
            empresa = next(iter(empresas.values()))
            correspondence = StatusCorrespondencia.RAZAO_SOCIAL

    identity = {
        "codi_emp_origem": source_code,
        "codi_cli": _as_int(row["codi_cli"], "codi_cli"),
        "ano_servico": ano,
        "mes_servico": mes,
    }
    # O namespace carrega o contrato: as duas fontes de receita não podem colidir
    # em `source_id`, senão a linha de uma sobrescreveria a da outra.
    source_id = _content_hash(f"{run.dataset_code}:aggregate", identity)
    ServicoFaturado.objects.update_or_create(
        organization=run.organization,
        source_id=source_id,
        defaults={
            "empresa": empresa,
            "codi_emp_origem": source_code,
            "codi_cli": identity["codi_cli"],
            "nome_cli": name,
            "documento_cli": document,
            "documento_cli_bi": (
                blind_index(document_digits, namespace="profitability.servico.documento")
                if document_digits
                else ""
            ),
            "valor": _as_decimal(row["valor"], "valor"),
            "data_servico": date(ano, mes, 1),
            "competencia": competence,
            "forma_localizacao": correspondence,
            "last_seen_run": run,
            "deleted_at": None,
        },
    )
    return competence


def _validate_columns(definition: DatasetDefinition, row: dict[str, Any]) -> None:
    expected = {column["name"] for column in definition.columns}
    if set(row) != expected:
        raise ValueError("Colunas da página divergem do contrato.")


def _armed_source(run: IngestRun, role: str) -> CompanyErpProfile | None:
    """A empresa armada com este papel, no ERP desta execução.

    Varre em Python porque a busca dentro de um campo JSON exige suporte do banco
    que o SQLite dos testes não tem; a cardinalidade é de empresas por escritório.
    """

    if not role:
        return None
    for perfil in CompanyErpProfile.objects.filter(
        organization=run.organization,
        sistema_origem=run.source_system,
        codi_emp__isnull=False,
        deleted_at__isnull=True,
    ).order_by("codi_emp"):
        if role in perfil.papel:
            return perfil
    return None


def _context_values(run: IngestRun, definition: DatasetDefinition) -> dict[str, Any]:
    """Preenche as colunas que a fonte não carrega na linha.

    São coordenadas que o sistema já conhece e a origem não repete em cada
    registro: a empresa, quando a fonte guarda uma pasta por empresa, e a
    competência, quando a fonte guarda apenas o valor vigente. Derivar aqui é o
    que dispensa pedir esses valores ao operador a cada execução.
    """

    if not definition.context_columns:
        return {}
    values: dict[str, Any] = {}
    if "codi_emp" in definition.context_columns:
        perfil = _armed_source(run, definition.requires_source_role)
        if perfil is None or perfil.codi_emp is None:
            raise ValueError(
                f"Nenhuma empresa marcada como {definition.requires_source_role} "
                f"em {run.source_system}."
            )
        values["codi_emp"] = perfil.codi_emp
    if "ultima_competencia" in definition.context_columns:
        # A fonte guarda o salário vigente, sem histórico: a competência é a da
        # execução. Reexecutar no mesmo mês converge no mesmo registro; no mês
        # seguinte nasce a leitura daquele mês, e o histórico se forma por
        # acumulação em vez de vir pronto da origem.
        reference = timezone.localtime(run.created_at).date()
        values["ultima_competencia"] = f"{reference.year:04d}-{reference.month:02d}"
    return values


def _reconcile(run: IngestRun) -> None:
    """Marca como removido o que a fonte deixou de trazer dentro da janela.

    Horas e serviços reconciliam por **competência**, não pelas datas cruas do
    parâmetro. Um serviço é gravado no dia 1 do seu mês, então uma janela que
    comece no dia 15 nunca varria o próprio mês de início: serviços apagados no
    ERP sobreviviam ao ciclo completo e seguiam inflando a mensalidade.

    A varredura é sempre do sistema de origem desta execução. Sem o recorte, uma
    reconciliação do Siescon marcaria como removido todo o cadastro do Domínio —
    ele não veio neste ciclo, afinal — e a próxima do Domínio devolveria o favor.
    """

    now = timezone.now()
    if run.dataset_code == "companies":
        CompanyErpProfile.objects.filter(
            organization=run.organization,
            origem=CompanyErpProfile.Origem.DOMINIO,
            sistema_origem=run.source_system,
            deleted_at__isnull=True,
        ).exclude(last_seen_run=run).update(deleted_at=now)
    elif run.dataset_code == "users":
        UsuarioErp.objects.filter(
            organization=run.organization, sistema_origem=run.source_system, ativo=True
        ).exclude(last_seen_run=run).update(ativo=False)
    elif run.dataset_code in {"automatic_hours", "f9_hours"}:
        origin = OrigemHoras.AUTOMATICA if run.dataset_code == "automatic_hours" else OrigemHoras.F9
        RegistroHoras.objects.filter(
            organization=run.organization,
            origem=origin,
            competencia__in=_window_competencias(run),
            deleted_at__isnull=True,
        ).exclude(last_seen_run=run).update(deleted_at=now)
    elif run.dataset_code in {"billing_services", "billing_honorarios"}:
        # A varredura não distingue os dois contratos de receita de propósito:
        # eles são exclusivos por escritório, então um ciclo completo do contrato
        # vigente tem de levar embora o que a fonte anterior deixou na janela.
        # Sem isso a troca de módulo contaria a mesma mensalidade duas vezes.
        ServicoFaturado.objects.filter(
            organization=run.organization,
            competencia__in=_window_competencias(run),
            deleted_at__isnull=True,
        ).exclude(last_seen_run=run).update(deleted_at=now)


def _colapsar_matriculas_repetidas(run: IngestRun) -> None:
    """Uma pessoa, uma linha — mesmo com duas matrículas na folha.

    O arquivo de folha traz a mesma pessoa mais de uma vez quando ela foi
    recontratada: a matrícula antiga continua no arquivo, e o contrato não tem
    como distingui-las porque não lê situação de vínculo.

    Duas linhas para a mesma pessoa não são só ruído na lista: elas dividem as
    horas dela em dois, e cada metade é precificada por um salário diferente.

    Fica a matrícula que tem horas lançadas; entre as que não têm, a mais recente,
    que é a numeração maior. É idempotente: o upsert reativa todas as linhas, e
    este passo torna a desligar as repetidas.
    """

    colaboradores = list(
        Colaborador.objects.filter(
            organization=run.organization, empresa_folha__isnull=False, ativo=True
        )
    )
    if not colaboradores:
        return

    horas = {
        str(row["colaborador_id"]): row["total"]
        for row in RegistroHoras.objects.filter(
            organization=run.organization, colaborador__isnull=False, deleted_at__isnull=True
        )
        .values("colaborador_id")
        .annotate(total=Count("id"))
    }

    por_pessoa: dict[tuple[Any, str], list[Colaborador]] = defaultdict(list)
    for colaborador in colaboradores:
        chave = (colaborador.empresa_folha_id, strip_accents_upper(colaborador.nome or ""))
        por_pessoa[chave].append(colaborador)

    repetidas: list[Any] = []
    for (_, nome), linhas in por_pessoa.items():
        if not nome or len(linhas) < 2:
            continue
        linhas.sort(key=lambda c: (horas.get(str(c.id), 0), c.i_empregados or 0), reverse=True)
        repetidas.extend(linha.id for linha in linhas[1:])

    if repetidas:
        Colaborador.objects.filter(id__in=repetidas).update(ativo=False)


def _rebuild_mensalidades(run: IngestRun, competencies: set[str]) -> None:
    """Reprojeta a mensalidade de cada empresa x competência tocada.

    `manual_override` fica de fora do upsert de propósito: a correção que um
    operador fez à mão não pode ser revertida pela próxima sincronização.
    """

    for competence in competencies:
        company_ids = set(
            ServicoFaturado.objects.filter(
                organization=run.organization, competencia=competence, empresa__isnull=False
            ).values_list("empresa_id", flat=True)
        )
        if not company_ids:
            continue
        totals = {
            str(row["empresa_id"]): row["total"] or Decimal(0)
            for row in ServicoFaturado.objects.filter(
                organization=run.organization,
                competencia=competence,
                empresa__isnull=False,
                deleted_at__isnull=True,
            )
            .values("empresa_id")
            .annotate(total=Sum("valor"))
        }
        Mensalidade.objects.bulk_create(
            [
                Mensalidade(
                    organization=run.organization,
                    empresa_id=company_id,
                    competencia=competence,
                    valor=totals.get(str(company_id), Decimal(0)),
                    fonte=Colaborador.Origem.DOMINIO,
                )
                for company_id in company_ids
            ],
            update_conflicts=True,
            unique_fields=("empresa", "competencia"),
            update_fields=("valor", "fonte", "updated_at"),
        )


def _batch_rows(batch: IngestBatch) -> list[dict[str, Any]]:
    """Lê a página guardada, conferindo a soma de verificação do que o agente enviou.

    A página fica cifrada em repouso pelo campo da CICA, mas a soma é do conteúdo
    em claro: se o que voltou não for o que foi enviado, a página não é aplicada
    em vez de aplicar linha corrompida em silêncio.
    """

    raw = batch.payload
    if hashlib.sha256(raw.encode()).hexdigest() != batch.checksum_sha256:
        raise ValueError(f"Página {batch.sequence} não confere com a soma enviada.")
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Página {batch.sequence} ilegível.") from exc
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Página {batch.sequence} não contém linhas.")
    return rows


def _dispatch_row(
    context: _RunContext, row: dict[str, Any], occurrence_index: int, content_hash: str
) -> str | None:
    """Aplica uma linha e devolve a competência tocada, se houver."""

    dataset_code = context.run.dataset_code
    if dataset_code == "companies":
        _upsert_company(context, row)
    elif dataset_code == "taxation":
        _upsert_taxation(context, row)
    elif dataset_code == "users":
        _upsert_user(context, row)
    elif dataset_code in {"automatic_hours", "f9_hours"}:
        return _upsert_hours(context, row, occurrence_index, content_hash)
    elif dataset_code == "salaries":
        return _upsert_salary(context, row)
    elif dataset_code in {"billing_services", "billing_honorarios"}:
        return _upsert_billing(context, row)
    elif dataset_code == "billing_events":
        _upsert_billing_event(context, row)
    else:
        raise ValueError("Processador de contrato ausente.")
    return None


def _rejection_budget(row_count: int) -> int:
    return max(REJECTION_ABSOLUTE_LIMIT, int(row_count * REJECTION_RATE_LIMIT))


def _process_rows(run: IngestRun) -> set[str]:
    definition = load_catalog().get_dispatchable(
        run.source_system, run.dataset_code, run.schema_version
    )
    if definition.query_sha256 != run.query_sha256:
        # O contrato mudou entre o despacho e o processamento. Aplicar linhas
        # produzidas por um SQL e atribuí-las a outro é exatamente o que fixar o
        # hash existe para impedir.
        raise ValueError("A consulta que produziu estas linhas não é a do contrato vigente.")

    context = _build_context(run)
    occurrences: dict[str, int] = defaultdict(int)
    competencies: set[str] = set()
    rejections: list[dict[str, Any]] = []
    budget = _rejection_budget(run.row_count)
    rejected = 0
    processed = 0
    ultima_rejeicao = ""
    # Resolvido uma vez por ciclo: as coordenadas de contexto valem para todas as
    # linhas, e a consulta ao cadastro não pode acontecer por linha.
    context_values = _context_values(run, definition)
    for batch in run.batches.order_by("sequence"):
        for index, raw_row in enumerate(_batch_rows(batch)):
            row = {**raw_row, **context_values}
            # Divergência de colunas é do contrato, não da linha: falha o ciclo.
            _validate_columns(definition, row)
            content_hash = _content_hash(run.dataset_code, row)
            occurrence_index = occurrences[content_hash]
            occurrences[content_hash] += 1
            processed += 1
            try:
                competence = _dispatch_row(context, row, occurrence_index, content_hash)
            except ValueError as exc:
                rejected += 1
                ultima_rejeicao = str(exc)
                if rejected > budget:
                    raise ValueError(
                        f"{run.dataset_code}: {rejected} linhas rejeitadas, "
                        f"acima do limite de {budget}. Última: {exc}"
                    ) from exc
                if len(rejections) < REJECTION_SAMPLE_SIZE:
                    # Só coordenadas e motivo — nunca o valor de origem.
                    rejections.append(
                        {"pagina": batch.sequence, "linha": index, "motivo": str(exc)}
                    )
                continue
            if competence is not None:
                competencies.add(competence)
    context.flush_hours()

    if processed != run.row_count:
        raise ValueError("Contagem processada diverge do que o agente declarou.")
    # Um ciclo que rejeitou TUDO não concluiu com sucesso, por menor que seja o
    # volume. O orçamento absoluto existe para tolerar sobras da origem, e ele já
    # engoliu um conjunto inteiro: os usuários vieram com 44 linhas, as 44 foram
    # rejeitadas porque o identificador era login e o código esperava inteiro, e o
    # ciclo reportou sucesso sem gravar ninguém. O sintoma só apareceu horas
    # depois, nas horas que não achavam usuário.
    if processed > 0 and rejected == processed:
        raise ValueError(
            f"{run.dataset_code}: todas as {processed} linhas foram rejeitadas. "
            f"Última: {ultima_rejeicao}"
        )

    if run.run_kind == IngestRun.RunKind.FULL:
        _reconcile(run)
        competencies |= _window_competencias(run)
    if run.dataset_code == "salaries":
        _colapsar_matriculas_repetidas(run)
    if run.dataset_code in {"billing_services", "billing_honorarios"}:
        _rebuild_mensalidades(run, competencies)
        # A carteira de um mês lê a mensalidade do mês anterior, então gravar o
        # honorário de agosto muda a tela de setembro. Sem reprojetar o mês
        # seguinte, o valor entra no banco e a tela que o exibe não sabe.
        competencies |= {competencia_seguinte(c) for c in set(competencies)}

    run.rejected_count = rejected
    run.rejection_sample = rejections
    return competencies


@transaction.atomic
def process_run(run_id: str | UUID) -> None:
    """Aplica uma execução inteira e reprojeta as competências que ela tocou."""

    run = (
        IngestRun.objects.select_for_update(of=("self",))
        .select_related("organization", "connector")
        .get(pk=run_id)
    )
    if run.status != IngestRun.Status.PROCESSING:
        raise ValueError("A execução não está pronta para processamento.")

    competencies = _process_rows(run)

    run.status = IngestRun.Status.SUCCEEDED
    run.completed_at = timezone.now()
    # Limpa o erro da tentativa anterior. Sem isto uma execução reprocessada com
    # sucesso continua exibindo o código de erro da falha antiga, e a tela mostra
    # "Concluída" ao lado da mensagem de exceção.
    run.error_code = ""
    run.save(
        update_fields=(
            "status",
            "completed_at",
            "error_code",
            "rejected_count",
            "rejection_sample",
            "updated_at",
        )
    )
    # Depois de gravar tudo, tentar ligar quem ficou sem colaborador. Roda em todo
    # ciclo, e não só no de usuários, porque o que destrava um vínculo tanto pode
    # ser um usuário novo quanto um colaborador novo vindo da folha — e a folha
    # chega num ciclo separado, às vezes de outro ERP.
    competencies |= vincular_usuarios_pendentes(run.organization)
    for competence in competencies:
        recompute_competencia(run.organization, competence)
