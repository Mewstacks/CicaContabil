"""Operator-facing mailbox state, without presenting consent as active intake."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.triage.models import Mailbox


@dataclass(frozen=True)
class MailboxPresentation:
    mailbox: Mailbox
    state: str
    label: str
    explanation: str
    action_hint: str
    provider_anchor: str


def present_mailbox(
    mailbox: Mailbox, *, poll_enabled: bool, now: datetime | None = None
) -> MailboxPresentation:
    """One truthful state and next step for each connected mailbox."""
    now = now or timezone.now()
    provider_anchors: Mapping[str, str] = {
        Mailbox.Provider.MS365_GRAPH: "triage-provider-ms",
        Mailbox.Provider.GMAIL_API: "triage-provider-google",
        Mailbox.Provider.IMAP: "triage-provider-imap",
    }
    provider_anchor = provider_anchors.get(str(mailbox.provider), "triage-connect-heading")
    if mailbox.status == Mailbox.Status.DISABLED:
        return MailboxPresentation(
            mailbox,
            "disconnected",
            "Desconectada",
            "A CICA não tem autorização para ler esta caixa.",
            "Conecte novamente pelo provedor acima.",
            provider_anchor,
        )
    if mailbox.status == Mailbox.Status.ERROR:
        return MailboxPresentation(
            mailbox,
            "attention",
            "Ação necessária",
            mailbox.last_error or "A última leitura falhou; confira a conexão e peça suporte.",
            "Confira a configuração do provedor. Se estiver correta, peça suporte à Mewstack.",
            provider_anchor,
        )
    if mailbox.status == Mailbox.Status.PENDING:
        return MailboxPresentation(
            mailbox,
            "pending",
            "Aguardando autorização",
            "A caixa ainda não confirmou o acesso de leitura.",
            "Conclua a conexão pelo provedor acima.",
            provider_anchor,
        )
    if mailbox.since is None:
        return MailboxPresentation(
            mailbox,
            "setup",
            "Conectada; falta configurar a leitura",
            "Nenhum anexo é buscado. Escolha a pasta e a data inicial antes da ativação.",
            "A ativação guiada ainda não está disponível nesta instalação.",
            provider_anchor,
        )
    if not mailbox.active:
        return MailboxPresentation(
            mailbox,
            "paused",
            "Leitura pausada",
            "A caixa está autorizada, mas não recebe anexos enquanto estiver pausada.",
            "A reativação pelo escritório ainda não está disponível nesta instalação.",
            provider_anchor,
        )
    if not poll_enabled:
        return MailboxPresentation(
            mailbox,
            "paused",
            "Leitura automática desligada",
            "A caixa está configurada, mas esta instalação ainda não consulta o provedor.",
            "A Mewstack precisa homologar e habilitar a execução periódica.",
            provider_anchor,
        )
    if mailbox.poll_retry_after and mailbox.poll_retry_after > now:
        return MailboxPresentation(
            mailbox,
            "retry",
            "Retentativa programada",
            mailbox.last_error or "O provedor não respondeu na última tentativa.",
            "A CICA tentará novamente no horário indicado. Nenhuma entrega anterior foi apagada.",
            provider_anchor,
        )
    if mailbox.last_polled_at is None:
        return MailboxPresentation(
            mailbox,
            "pending",
            "Aguardando primeira leitura",
            "A leitura está habilitada; o primeiro lote ainda não foi confirmado.",
            "Acompanhe a primeira execução antes de considerar esta caixa operacional.",
            provider_anchor,
        )
    return MailboxPresentation(
        mailbox,
        "receiving",
        "Leitura habilitada",
        "A caixa foi consultada. Os anexos recebidos continuam em quarentena para revisão.",
        "A fila de anexos e pendências de segurança ainda não está disponível nesta tela.",
        provider_anchor,
    )
