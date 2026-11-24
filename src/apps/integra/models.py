from __future__ import annotations

from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.organizations.models import OrganizationScopedModel


class OfficeSerproIdentity(OrganizationScopedModel):
    """How one office reaches the Integra Contador (T10.3) and how much it may spend (T10.4).

    `default` keeps the behavior before E10: the platform contract and the CNPJ of the office as
    author, no term. `platform_termo` keeps the platform contract and sends the Termo de
    Autorização signed with the e-CNPJ of the office. `own_contract` uses the office's own Serpro
    contract (its consumer key and secret, mTLS with its own e-CNPJ A1).
    """

    class Mode(models.TextChoices):
        DEFAULT = "default", "Padrão"
        PLATFORM_TERMO = "platform_termo", "Plataforma com termo"
        OWN_CONTRACT = "own_contract", "Contrato próprio"

    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.DEFAULT)
    consumer_key = EncryptedTextField(blank=True, default="")
    consumer_secret = EncryptedTextField(blank=True, default="")
    # Spending limits, in cents of real (the 1st-band price is the reference; see governor.py).
    monthly_cap_cents = models.PositiveIntegerField(default=5000)
    conversation_cap_cents = models.PositiveIntegerField(default=500)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",), name="integra_one_identity_per_organization"
            ),
            models.CheckConstraint(
                condition=~models.Q(mode="own_contract")
                | (~models.Q(consumer_key="") & ~models.Q(consumer_secret="")),
                name="integra_own_contract_needs_credentials",
            ),
        ]


class IntegraCall(OrganizationScopedModel):
    """One call that reached the gateway: what it may have cost and who asked.

    Serpro charges 200, 202 and 403 on the paths /Consultar, /Emitir and /Declarar; /Apoiar and
    /Monitorar are free (research report, section 1.6). No payload is stored here.
    """

    service_key = models.CharField(max_length=80)
    http_status = models.PositiveSmallIntegerField()
    charged = models.BooleanField()
    cost_cents = models.PositiveIntegerField()
    conversation_id = models.CharField(max_length=64, blank=True, default="")
    request_tag = models.CharField(max_length=32)

    class Meta:
        indexes = [
            models.Index(fields=("organization", "created_at"), name="integra_call_org_month"),
            models.Index(fields=("organization", "conversation_id"), name="integra_call_conv"),
        ]


class RadarRequest(OrganizationScopedModel):
    """One batch request of update events (EVENTOSATUALIZACAO, free of charge) and its protocol."""

    class State(models.TextChoices):
        REQUESTED = "requested", "Pedido"
        COLLECTED = "collected", "Coletado"
        EXPIRED = "expired", "Vencido"

    evento = models.CharField(max_length=5)
    protocolo = models.CharField(max_length=36)
    ready_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    state = models.CharField(max_length=12, choices=State.choices, default=State.REQUESTED)
    companies_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=("organization", "state"), name="integra_radar_req_state")]


class RadarSignal(OrganizationScopedModel):
    """The last update event seen for one company: a date, or no power of attorney."""

    company = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="radar_signals"
    )
    evento = models.CharField(max_length=5)
    event_date = models.DateField(null=True, blank=True)
    sem_procuracao = models.BooleanField(default=False)
    observed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("company", "evento"), name="integra_one_radar_signal_per_event"
            )
        ]
