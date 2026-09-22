"""O domínio de rentabilidade: empresas do ERP, pessoas, horas e serviços faturados.

Portado do Lucrums por D-108. Duas convenções carregam a maior parte do peso e
vieram sem mudança:

* `source_content_hash` com `occurrence_index` — nem o log de sessão nem o
  lançamento F9 expõem chave estável no SELECT que temos, então o hash da tupla
  que identifica o evento *é* o mecanismo de idempotência, e o ordinal preserva
  multiplicidade entre repetições.
* `deleted_at` — uma reconciliação completa marca como excluídas as linhas da
  janela que ela não viu; nada é apagado de verdade. Ciclo incremental nunca
  varre, então janela parcial não apaga histórico.

Três diferenças em relação à origem, todas deliberadas:

1. Não existe `Empresa` aqui. A carteira é `hub.ClientCompany`, por D-109, e o
   que o cálculo precisa e ela não tem mora em `CompanyErpProfile`. As chaves
   estrangeiras que na origem apontavam para `Empresa` apontam para a carteira,
   mantendo o nome `empresa` para não divergir do serviço portado.
2. Os nomes de classe seguem a origem, em português, enquanto o resto da CICA
   usa inglês. Renomear tudo atravessaria os serviços e o processamento portados
   — milhares de linhas — e os nomes de campo continuariam em português de
   qualquer forma, então o resultado seria meio traduzido e menos conferível
   contra a origem. Duas exceções: `CompanyErpProfile`, que é ligação escrita
   aqui e não código portado, e `UsuarioDominio`, que virou `UsuarioErp` porque
   carrega `sistema_origem` e vale igualmente para o Siescon — o nome antigo
   afirmava um ERP só.
3. Falta `last_seen_run` em todos os modelos. Na origem é a chave para o ciclo de
   ingestão, que chega na fase 3 desta etapa junto com o modelo de execução.
   As colunas `deleted_at` já estão aqui porque não dependem dele.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.base import ModelBase

from apps.common.encryption import EncryptedTextField, blind_index
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import OrganizationScopedModel

from .normalize import cnpj_raiz, document_kind, only_digits, strip_accents_upper

competencia_validator = RegexValidator(
    regex=r"^\d{4}-(0[1-9]|1[0-2])$",
    message="Use o formato AAAA-MM.",
)


class OrigemHoras(models.TextChoices):
    AUTOMATICA = "automatica", "Automática"
    F9 = "f9", "F9"


class StatusRegistro(models.TextChoices):
    OK = "ok", "Conferido"
    DIVERGENTE = "divergente", "Divergente"
    PENDENTE = "pendente", "Pendente"


class StatusCorrespondencia(models.TextChoices):
    CPF_CNPJ = "cpf_cnpj", "Confirmado"
    RAZAO_SOCIAL = "razao_social", "Revisar correspondência"
    NAO_ENCONTRADO = "nao_encontrado", "Não localizado"


class SistemaOrigem(models.TextChoices):
    """De qual ERP a linha veio.

    O escritório lê dois sistemas, e `codi_emp` só é único dentro de um deles — a
    empresa 25 do Domínio não tem relação com a 25 do Siescon. Sem esta coluna a
    segunda importação sobrescreveria a primeira, e a reconciliação de cada uma
    apagaria o cadastro da outra.
    """

    DOMINIO = "dominio", "Domínio Sistemas"
    SIESCON = "siescon", "Siescon"


class PapelEmpresa(models.TextChoices):
    """Para que a empresa pode ser usada, não o que ela é.

    `billing_source` e `payroll_source` liberam os dois conjuntos de dados
    parametrizados que leem honorários e folha de outra empresa. Nada vem marcado:
    enquanto ninguém armar a empresa explicitamente, esses conjuntos não são
    despachados. Errar para o lado permissivo importaria o salário dos
    funcionários de todo cliente, então o padrão tem de ser o fechado.
    """

    CLIENTE = "cliente", "Cliente"
    ESCRITORIO = "escritorio", "Escritório"
    BILLING_SOURCE = "billing_source", "Fonte de honorários"
    PAYROLL_SOURCE = "payroll_source", "Fonte de folha"


class FonteReceita(models.TextChoices):
    """Os contratos que podem alimentar a mensalidade. São mutuamente exclusivos."""

    HONORARIOS = "billing_honorarios", "Domínio Honorários"
    ESCRITA_FISCAL = "billing_services", "Domínio Escrita Fiscal"


class Segmento(OrganizationScopedModel):
    nome = models.CharField(max_length=80)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "nome"), name="profitability_unique_segmento_nome"
            )
        ]

    def __str__(self) -> str:
        return self.nome


class Competencia(OrganizationScopedModel):
    """Um período contábil mensal. Sustenta o seletor global de competência."""

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        FECHADA = "fechada", "Fechada"

    competencia = models.CharField(max_length=7, validators=[competencia_validator])
    inicio = models.DateField()
    fim = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ABERTA)
    is_atual = models.BooleanField(default=False)

    class Meta:
        ordering = ("-competencia",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "competencia"), name="profitability_unique_competencia"
            ),
            # Exatamente uma competência corrente por escritório, garantida pelo
            # banco e não por quem lembrar de limpar a anterior.
            models.UniqueConstraint(
                fields=("organization",),
                condition=models.Q(is_atual=True),
                name="profitability_unique_competencia_atual",
            ),
        ]

    def __str__(self) -> str:
        return self.competencia


class Colaborador(OrganizationScopedModel):
    class Origem(models.TextChoices):
        DOMINIO = "dominio", "Domínio"
        MANUAL = "manual", "Manual"

    class Contratacao(models.TextChoices):
        CLT = "clt", "CLT"
        PJ = "pj", "PJ"

    codigo = models.CharField(max_length=24, blank=True)
    # CLT tem encargo; PJ não tem. Aplicar encargo sobre a nota de um PJ inventa
    # custo que ninguém paga e derruba a margem dos clientes que ele atende.
    contratacao = models.CharField(
        max_length=3, choices=Contratacao.choices, default=Contratacao.CLT
    )
    nome = EncryptedTextField()
    nome_bi = models.CharField(max_length=64, db_index=True)
    cargo = models.CharField(max_length=80, blank=True)
    ativo = models.BooleanField(default=True)
    origem = models.CharField(max_length=8, choices=Origem.choices, default=Origem.MANUAL)
    # De qual empresa de folha vieram os salários, e o id do empregado dentro
    # dela. Ambos nulos para um colaborador criado à mão.
    empresa_folha = models.ForeignKey(
        "hub.ClientCompany",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profitability_colaboradores_folha",
    )
    i_empregados = models.IntegerField(null=True, blank=True)
    # Parcelas mensais e dias que alimentam `calc.custo_anual_colaborador`.
    beneficios_mensais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vt_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outros_custos_mensais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dias_ferias = models.PositiveSmallIntegerField(default=22)
    folgas_dias = models.PositiveSmallIntegerField(default=0)
    ausencias_dias = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("codigo",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "empresa_folha", "i_empregados"),
                condition=models.Q(i_empregados__isnull=False),
                name="profitability_unique_colaborador_erp",
            )
        ]
        indexes = [models.Index(fields=("organization", "ativo"))]

    def __str__(self) -> str:
        return self.codigo or str(self.pk)

    def clean(self) -> None:
        super().clean()
        empresa_folha = self.empresa_folha if self.empresa_folha_id else None
        if empresa_folha and empresa_folha.organization_id != self.organization_id:
            raise ValidationError(
                {"empresa_folha": "A empresa de folha deve pertencer à organização."}
            )

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.nome_bi = blind_index(self.nome, namespace="profitability.colaborador.nome")
        if update_fields is not None:
            update_fields = {*update_fields, "nome_bi"}
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class CompanyErpProfile(OrganizationScopedModel):
    """O que o ERP sabe de uma empresa da carteira e a carteira do hub não guarda.

    Escrito para esta incorporação, não portado. Por D-109 a carteira continua
    sendo `hub.ClientCompany`, que é onde o controle de acesso por colaborador
    filtra; uma segunda entidade de empresa faria as telas de rentabilidade
    contornarem esse filtro.

    Sobre identidade: `ClientCompany.dominio_code` continua sendo a chave do hub,
    usada por NFS-e, conciliação e DTE. Aqui guarda-se `codi_emp` com o sistema de
    origem ao lado porque o código só é único dentro de um ERP, e `dominio_code`
    não carrega essa qualificação.

    Sobre o nome: a origem movia a razão social para coluna cifrada quando o
    documento era CPF, ou seja pessoa física. Isso não foi portado porque
    `ClientCompany.name` é coluna em claro por desenho anterior da CICA, comum a
    todos os módulos: cifrar aqui deixaria o nome exposto lá do mesmo jeito e a
    proteção seria só aparente. Tratar isso é mudança na carteira do hub, não
    neste módulo.
    """

    class Origem(models.TextChoices):
        DOMINIO = "dominio", "Domínio"
        MANUAL = "manual", "Manual"

    empresa = models.OneToOneField(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="erp_profile"
    )
    codi_emp = models.IntegerField(null=True, blank=True)
    origem = models.CharField(max_length=8, choices=Origem.choices, default=Origem.DOMINIO)
    sistema_origem = models.CharField(
        max_length=16, choices=SistemaOrigem.choices, default=SistemaOrigem.DOMINIO
    )

    documento = EncryptedTextField(blank=True, default="")
    documento_bi = models.CharField(max_length=64, blank=True, db_index=True)
    # Índice cego da RAIZ do CNPJ, que é o que une matriz e filiais. Precisa ser
    # coluna própria porque `documento_bi` é o hash do documento inteiro — dele
    # não se extraem os oito primeiros dígitos, e o texto claro está cifrado.
    documento_raiz_bi = models.CharField(max_length=64, blank=True, db_index=True)
    documento_tipo = models.CharField(max_length=8, blank=True)
    razao_normalizada_bi = models.CharField(max_length=64, blank=True, db_index=True)

    papel = models.JSONField(default=list, blank=True)
    codigo = models.CharField(max_length=24, blank=True)
    regime = models.CharField(max_length=40, blank=True)
    regime_codigo = models.PositiveSmallIntegerField(null=True, blank=True)
    regime_vigencia = models.DateField(null=True, blank=True)
    segmento = models.ForeignKey(
        Segmento, null=True, blank=True, on_delete=models.SET_NULL, related_name="empresas"
    )
    responsavel = models.ForeignKey(
        Colaborador,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="empresas_responsavel",
    )
    margem_alvo = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    correspondencia = models.CharField(
        max_length=16,
        choices=StatusCorrespondencia.choices,
        default=StatusCorrespondencia.NAO_ENCONTRADO,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("codi_emp",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "sistema_origem", "codi_emp"),
                condition=models.Q(codi_emp__isnull=False),
                name="profitability_unique_empresa_codi_emp",
            )
        ]
        indexes = [
            models.Index(fields=("organization", "documento_bi")),
            models.Index(fields=("organization", "documento_raiz_bi")),
            models.Index(fields=("organization", "razao_normalizada_bi")),
        ]

    @property
    def is_pessoa_fisica(self) -> bool:
        return self.documento_tipo == "cpf"

    def __str__(self) -> str:
        return str(self.codi_emp) if self.codi_emp is not None else str(self.pk)

    def clean(self) -> None:
        super().clean()
        self._prepare_private_fields()
        if self.origem == self.Origem.DOMINIO and self.codi_emp is None:
            raise ValidationError({"codi_emp": "Empresas importadas do ERP exigem codi_emp."})
        if self.empresa_id and self.empresa.organization_id != self.organization_id:
            raise ValidationError({"empresa": "A empresa deve pertencer à organização."})
        segmento = self.segmento if self.segmento_id else None
        responsavel = self.responsavel if self.responsavel_id else None
        if segmento and segmento.organization_id != self.organization_id:
            raise ValidationError({"segmento": "O segmento deve pertencer à organização."})
        if responsavel and responsavel.organization_id != self.organization_id:
            raise ValidationError({"responsavel": "O responsável deve pertencer à organização."})
        invalid_roles = set(self.papel) - set(PapelEmpresa.values)
        if invalid_roles:
            raise ValidationError({"papel": f"Papéis inválidos: {sorted(invalid_roles)}"})

    def _prepare_private_fields(self) -> None:
        documento_normalizado = only_digits(self.documento)
        self.documento_tipo = document_kind(documento_normalizado)
        self.documento_bi = (
            blind_index(documento_normalizado, namespace="profitability.empresa.documento")
            if documento_normalizado
            else ""
        )
        # Namespace próprio, para os dois índices seguirem independentes.
        raiz = cnpj_raiz(documento_normalizado)
        self.documento_raiz_bi = (
            blind_index(raiz, namespace="profitability.empresa.raiz") if raiz else ""
        )
        nome = self.empresa.name if self.empresa_id else ""
        self.razao_normalizada_bi = (
            blind_index(strip_accents_upper(nome), namespace="profitability.empresa.razao")
            if nome
            else ""
        )

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self._prepare_private_fields()
        if update_fields is not None:
            update_fields = {
                *update_fields,
                "documento_tipo",
                "documento_bi",
                "documento_raiz_bi",
                "razao_normalizada_bi",
            }
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class UsuarioErp(OrganizationScopedModel):
    """`usConfUsuario` — a junção que transforma um código de usuário em pessoa.

    Apesar do nome, `i_usuario` **não** é número: em `usConfUsuario` é um varchar
    com o login (`ANA.W`, `GERENTE`), e `geloguser.usua_log` e
    `geatividades.codi_usu` carregam esse mesmo login. Tratá-lo como inteiro
    rejeitava toda linha de horas e — porque as rejeições cabiam no orçamento do
    conjunto pequeno de usuários — o ciclo relatava sucesso sem gravar ninguém.
    `i_confusuario` é inteiro mas repete entre linhas, então não serve de chave.

    Sem esta tabela os fatos de horas não têm dono e toda tela de colaborador fica
    vazia. O vínculo com `Colaborador` é proposto por um casador e existe para ser
    corrigido pelo operador.
    """

    i_usuario = models.CharField(max_length=64)
    sistema_origem = models.CharField(
        max_length=16, choices=SistemaOrigem.choices, default=SistemaOrigem.DOMINIO
    )
    nome = EncryptedTextField()
    nome_bi = models.CharField(max_length=64, db_index=True)
    situacao = models.IntegerField(default=1)
    ativo = models.BooleanField(default=True)
    colaborador = models.ForeignKey(
        Colaborador,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="usuarios_erp",
    )
    # Quem escolheu o colaborador: o casador ou uma pessoa. O casador ignora os
    # manuais, e é isso que faz a correção do operador sobreviver ao ciclo do dia
    # seguinte — sem esta marca o casamento automático desfaria a decisão dele.
    vinculo_manual = models.BooleanField(default=False)

    class Meta:
        ordering = ("i_usuario",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "sistema_origem", "i_usuario"),
                name="profitability_unique_usuario_erp",
            )
        ]

    def __str__(self) -> str:
        return self.i_usuario

    def clean(self) -> None:
        super().clean()
        colaborador = self.colaborador if self.colaborador_id else None
        if colaborador and colaborador.organization_id != self.organization_id:
            raise ValidationError({"colaborador": "O colaborador deve pertencer à organização."})

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.nome_bi = blind_index(self.nome, namespace="profitability.usuario.nome")
        if update_fields is not None:
            update_fields = {*update_fields, "nome_bi"}
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class SalarioColaborador(OrganizationScopedModel):
    """Uma observação por linha de `foaltesal`.

    O valor fica como número em claro em vez de campo cifrado: o modelo de custo
    agrega sobre ele, e cifrar forçaria decifrar a tabela inteira a cada
    recomputação de métrica. O controle compensatório é leitura restrita por papel
    e evento de auditoria quando o valor sai numa resposta.
    """

    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name="salarios")
    competencia = models.CharField(max_length=7, validators=[competencia_validator])
    salario = models.DecimalField(max_digits=12, decimal_places=2)
    fonte = models.CharField(max_length=8, choices=Colaborador.Origem.choices)

    class Meta:
        ordering = ("-competencia",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "colaborador", "competencia"),
                name="profitability_unique_salario_competencia",
            )
        ]

    def __str__(self) -> str:
        return f"{self.colaborador_id} {self.competencia}"

    def clean(self) -> None:
        super().clean()
        if self.colaborador.organization_id != self.organization_id:
            raise ValidationError({"colaborador": "O colaborador deve pertencer à organização."})


class RegistroHoras(OrganizationScopedModel):
    """A tabela de fatos de horas: logs automáticos de sessão e lançamentos F9.

    A duração é guardada em minutos inteiros, não em horas fracionárias. Valores
    reais de `tfim - tini` não são granulares de meia em meia hora, e somas em
    float derivam depois de algumas centenas de milhares de linhas.
    """

    empresa = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.PROTECT, related_name="profitability_registros_horas"
    )
    colaborador = models.ForeignKey(
        Colaborador,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_horas",
    )
    usuario_erp = models.ForeignKey(
        UsuarioErp, null=True, blank=True, on_delete=models.SET_NULL, related_name="registros"
    )
    competencia = models.CharField(max_length=7, validators=[competencia_validator], db_index=True)
    data = models.DateField()
    origem = models.CharField(max_length=12, choices=OrigemHoras.choices)
    inicio = models.TimeField(null=True, blank=True)
    fim = models.TimeField(null=True, blank=True)
    # `dfim_log`: uma sessão automática pode atravessar a meia-noite.
    data_fim = models.DateField(null=True, blank=True)
    duracao_minutos = models.IntegerField(validators=[MinValueValidator(0)])
    descricao = models.TextField(blank=True)
    # Linhas de origem iguais são legítimas. O conteúdo é hasheado e o ordinal
    # estável entre iguais preserva a multiplicidade entre repetições.
    source_content_hash = models.CharField(max_length=64)
    occurrence_index = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=12, choices=StatusRegistro.choices, default=StatusRegistro.OK
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("data", "inicio")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "source_content_hash", "occurrence_index"),
                name="profitability_unique_registro_horas_occurrence",
            )
        ]
        indexes = [
            models.Index(fields=("organization", "competencia", "empresa")),
            models.Index(fields=("organization", "competencia", "colaborador")),
            models.Index(fields=("organization", "competencia", "origem")),
        ]

    @property
    def duracao_horas(self) -> float:
        return self.duracao_minutos / 60

    def __str__(self) -> str:
        return f"{self.data} {self.origem} {self.duracao_minutos}min"

    def clean(self) -> None:
        super().clean()
        relations = {
            "empresa": self.empresa if self.empresa_id else None,
            "colaborador": self.colaborador if self.colaborador_id else None,
            "usuario_erp": self.usuario_erp if self.usuario_erp_id else None,
        }
        for field_name, related in relations.items():
            if related is not None and related.organization_id != self.organization_id:
                raise ValidationError(
                    {field_name: "O registro relacionado deve pertencer à organização."}
                )


class ServicoFaturado(OrganizationScopedModel):
    """Uma linha da saída de `billing_services` — a origem crua da mensalidade."""

    # Nulo quando `forma_localizacao` é `nao_encontrado`: o serviço existe no
    # honorários mas nenhuma empresa da carteira pôde ser casada com ele.
    empresa = models.ForeignKey(
        "hub.ClientCompany",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profitability_servicos",
    )
    codi_emp_origem = models.IntegerField()
    codi_cli = models.IntegerField()
    nome_cli = EncryptedTextField(blank=True, default="")
    documento_cli = EncryptedTextField(blank=True, default="")
    documento_cli_bi = models.CharField(max_length=64, blank=True, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_servico = models.DateField(null=True, blank=True)
    # Exigido pelo `billing_services` v2. Deliberadamente não é sintetizado a
    # partir do SELECT v1, porque isso tornaria ilusória a idempotência.
    source_id = models.CharField(max_length=128)
    competencia = models.CharField(max_length=7, validators=[competencia_validator], db_index=True)
    forma_localizacao = models.CharField(max_length=16, choices=StatusCorrespondencia.choices)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("competencia", "codi_cli")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "source_id"),
                name="profitability_unique_servico_faturado",
            )
        ]
        indexes = [models.Index(fields=("organization", "competencia", "empresa"))]

    def __str__(self) -> str:
        return f"{self.codi_cli} {self.competencia}"

    def clean(self) -> None:
        super().clean()
        empresa = self.empresa if self.empresa_id else None
        if empresa and empresa.organization_id != self.organization_id:
            raise ValidationError({"empresa": "A empresa deve pertencer à organização."})


class EventoFaturamento(OrganizationScopedModel):
    """Volume e total por evento de faturamento do Honorários, por competência.

    Não alimenta receita nenhuma: é descoberta. O cadastro de eventos é numerado
    por escritório, então qual código é a mensalidade não se sabe de fora — e a
    única forma honesta de descobrir é medindo na base do próprio escritório.
    Esta tabela é o que a tela mostra para quem tem de escolher o número.

    Guarda só código, contagem e soma. Nome e documento de cliente não entram:
    para escolher um evento eles não são necessários.
    """

    codi_emp_origem = models.IntegerField()
    i_evento = models.IntegerField()
    competencia = models.CharField(max_length=7, validators=[competencia_validator], db_index=True)
    lancamentos = models.PositiveIntegerField(default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ("-competencia", "-total")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "codi_emp_origem", "i_evento", "competencia"),
                name="profitability_unique_evento_faturamento",
            )
        ]

    def __str__(self) -> str:
        return f"{self.i_evento} {self.competencia}"


class Mensalidade(OrganizationScopedModel):
    """Agregado por empresa x competência, que é o que a interface lê.

    Derivado somando `ServicoFaturado`, mas `manual_override` vence quando
    preenchido: o operador tem de poder corrigir um casamento ruim sem que o
    ciclo seguinte reverta a correção em silêncio.
    """

    empresa = models.ForeignKey(
        "hub.ClientCompany",
        on_delete=models.CASCADE,
        related_name="profitability_mensalidades",
    )
    competencia = models.CharField(max_length=7, validators=[competencia_validator])
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fonte = models.CharField(max_length=8, choices=Colaborador.Origem.choices)
    manual_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("-competencia",)
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "competencia"),
                name="profitability_unique_mensalidade_competencia",
            )
        ]

    @property
    def valor_efetivo(self) -> Decimal:
        return self.manual_override if self.manual_override is not None else self.valor

    def __str__(self) -> str:
        return f"{self.empresa_id} {self.competencia}"

    def clean(self) -> None:
        super().clean()
        if self.empresa_id and self.empresa.organization_id != self.organization_id:
            raise ValidationError({"empresa": "A empresa deve pertencer à organização."})


class ProfitabilityConfig(UUIDTimeStampedModel):
    """Os parâmetros de custo que a tela de configuração do módulo edita.

    Na origem chamava-se `OrganizacaoConfig` e guardava mais duas colunas,
    `horas_mes_referencia` e `fator_encargos`, aposentadas pela auditoria de
    setembro de 2026 e mantidas lá só para não descartar o que o escritório já
    tinha digitado. Aqui a tabela nasce vazia, então criá-las seria estrear com
    duas colunas mortas que ninguém lê. A conta de custo horário é uma só, em
    `calc.custo_anual_colaborador`.
    """

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="profitability_config",
    )
    margem_alvo_padrao = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.2000")
    )
    margem_alvo_global = models.BooleanField(default=False)
    margem_atencao = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.1500"))
    # Piso de horas automáticas para a competência do cliente ter base de custo.
    # Abaixo dele o custo apurado é um pedaço de um mês, e dividir a mensalidade
    # inteira por esse pedaço devolve margem perto de 100% e mensalidade sugerida
    # miudíssima — o cliente sobe ao topo da carteira por falta de dado, não por
    # rentabilidade. Em 0 o comportamento anterior volta inteiro.
    minutos_minimos_custo = models.PositiveSmallIntegerField(default=10)
    # Parâmetros do custo anual: encargos sobre salários e 13º, calendário de
    # dias úteis e índice de produtividade.
    encargos_percentual = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.3500")
    )
    dias_uteis_ano = models.PositiveSmallIntegerField(default=250)
    feriados_dias_ano = models.PositiveSmallIntegerField(default=10)
    horas_dia = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("8.00"))
    indice_produtividade = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.8000")
    )
    limiar_divergencia_horas = models.PositiveSmallIntegerField(default=2)
    limiar_divergencia_colaborador = models.PositiveSmallIntegerField(default=10)
    codi_emp_confirmed = models.BooleanField(default=False)
    # De qual módulo do Domínio vem a receita deste escritório. Os dois existem e
    # os dois são legítimos, e qual vale muda de escritório para escritório mas
    # não dentro do mesmo — por isso é configuração, não descoberta a cada ciclo.
    # Rodar os dois juntos contaria a mesma receita duas vezes, porque a
    # reconstrução da mensalidade soma todo serviço faturado da competência sem
    # olhar de qual contrato veio. Em branco, nenhum roda.
    #
    # Qual fonte vale neste escritório é Q-39, e está aberta: o levantamento de
    # origem não encontrou receita em nenhum dos dois ERPs.
    fonte_receita = models.CharField(
        max_length=32, choices=FonteReceita.choices, blank=True, default=""
    )
    # Código do evento de mensalidade no cadastro de eventos do Honorários. Não é
    # constante do Domínio: cada escritório numera o seu, então um número cravado
    # no SQL funcionaria num cliente e devolveria zero, calado, no próximo. Nulo
    # enquanto ninguém descobriu — e nesse estado o ciclo pula o conjunto de
    # dados em vez de faturar o evento errado.
    evento_mensalidade = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"config {self.organization_id}"


class FaixaMargem(models.TextChoices):
    NEGATIVA = "negativa", "Margem negativa"
    ATENCAO = "atencao", "Atenção"
    SAUDAVEL = "saudavel", "Saudável"
    SEM_DADOS = "sem_dados", "Sem dados"
    INCOMPLETA = "incompleta", "Custo incompleto"


class ClienteCompetenciaMetrics(OrganizationScopedModel):
    """Modelo de leitura materializado, por empresa x competência.

    A aritmética acontece uma vez, aqui, e a tela lê o resultado. Calcular na
    tela não sobrevive a dado real: a carteira precisa de ordenação por margem
    *junto* com paginação, que ordenar a página no cliente faz errado por
    construção, e o custo depende de salário — mandar a folha inteira para o
    navegador multiplicar é exposição sem contrapartida.

    As duas tabelas de métrica são refeitas por inteiro, por escritório e
    competência, por `services.recompute_competencia`, que é idempotente.
    """

    empresa = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="profitability_metricas"
    )
    competencia = models.CharField(max_length=7, validators=[competencia_validator])

    horas_auto_minutos = models.IntegerField(default=0)
    horas_f9_minutos = models.IntegerField(default=0)
    custo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mensalidade = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    resultado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margem = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    faixa = models.CharField(max_length=12, choices=FaixaMargem.choices)
    custo_completo = models.BooleanField(default=True)
    minutos_sem_custo = models.IntegerField(default=0)
    motivos_incompletude = models.JSONField(default=list, blank=True)

    divergencia_minutos = models.IntegerField(default=0)
    tem_divergencia = models.BooleanField(default=False)
    f9_pendente = models.BooleanField(default=False)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-competencia",)
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "competencia"), name="profitability_unique_cliente_metrics"
            )
        ]
        indexes = [
            models.Index(fields=("organization", "competencia", "faixa")),
            # O que faz "ordenar por margem, paginado" ser uma varredura de
            # índice em vez de uma ordenação sobre a carteira inteira.
            models.Index(fields=("organization", "competencia", "margem")),
        ]

    def __str__(self) -> str:
        return f"{self.empresa_id} {self.competencia}"


class ColaboradorCompetenciaMetrics(OrganizationScopedModel):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name="metricas")
    competencia = models.CharField(max_length=7, validators=[competencia_validator])

    horas_auto_minutos = models.IntegerField(default=0)
    horas_f9_minutos = models.IntegerField(default=0)
    # Automáticas menos F9, contando só as empresas cujo F9 de fato chegou.
    # Incluir uma empresa pendente reportaria todo o total automático dela como
    # divergência, o que é importação faltando, não discrepância.
    diferenca_minutos = models.IntegerField(default=0)
    custo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_hora = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    # Sem salário vigente o custo/hora fica em zero, e zero é um número: a pessoa
    # aparecia custando R$ 0,00, indistinguível de quem de fato não custa —
    # enquanto a mesma hora, do lado do cliente, era marcada como custo
    # incompleto. A linha precisa carregar a diferença para a tela poder dizer
    # "sem salário" em vez de inventar um custo nulo.
    sem_salario = models.BooleanField(default=False)
    empresas_count = models.IntegerField(default=0)
    f9_pendente = models.BooleanField(default=False)
    divergente = models.BooleanField(default=False)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-competencia",)
        constraints = [
            models.UniqueConstraint(
                fields=("colaborador", "competencia"),
                name="profitability_unique_colaborador_metrics",
            )
        ]
        indexes = [models.Index(fields=("organization", "competencia", "divergente"))]

    def __str__(self) -> str:
        return f"{self.colaborador_id} {self.competencia}"
