from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    AccumulatorObservation,
    AccumulatorRule,
    ClientCompany,
    CompanyAccessGrant,
    Connector,
    DteMessage,
    DteRun,
    OfficeProfile,
    ProductModule,
    UsageAllowance,
)
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.hub.services import create_document_and_artifact, prepare_dte_run, store_certificate
from apps.organizations.models import Membership, Organization

COMPANIES: list[tuple[str, str, str]] = [
    ("Padaria Vila Nova Ltda", "12.345.678/0001-95", "0101"),
    ("Transportes Guaíba ME", "23.456.789/0001-95", "0102"),
    ("Clínica Odonto Sorriso", "34.567.890/0001-30", "0103"),
    ("Mercado São Jorge Ltda", "45.678.901/0001-75", "0104"),
    ("Studio Alfa Arquitetura", "56.789.012/0001-00", "0105"),
    ("Oficina Motor Forte", "67.890.123/0001-16", "0106"),
    ("Consultoria Ponte Nova", "78.901.234/0001-05", "0107"),
    ("Distribuidora Campo Bom", "89.012.345/0001-79", "0108"),
]

SERVICE_CODES = ["1401", "0702", "1701", "0910"]

DTE_SUBJECTS = [
    "Comunicado de pendência - Malha Fiscal",
    "Intimação eletrônica - DCTFWeb",
    "Aviso de débito inscrito em dívida ativa",
    "Comunicado de regularidade cadastral",
    "Termo de intimação - Simples Nacional",
]


class Command(BaseCommand):
    help = "Populate one demonstration office with companies, documents, tasks and DTE evidence."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", default="escritorio-demo")
        parser.add_argument("--name", default="Escritório Demonstração")
        parser.add_argument("--email", default="demo@hubcontador.local")
        parser.add_argument(
            "--password",
            default="",
            help="Owner password. Generated and printed once when omitted.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not getattr(settings, "SEED_DEMO_ALLOWED", False):
            raise CommandError(
                "seed_demo only runs with DEBUG on. It writes fabricated fiscal evidence."
            )

        password = options["password"] or secrets.token_urlsafe(12)
        with transaction.atomic():
            organization, owner, owner_created = self._office(options, password)
            companies = self._companies(organization, owner)
            self._modules_and_limits(organization)
            self._certificates(companies[:3], owner)
            self._documents(organization, companies)
            self._dte(organization, companies, owner)

        self.stdout.write(self.style.SUCCESS(f"Escritório: {organization.name}"))
        self.stdout.write(f"Login:      {owner.email}")
        if owner_created and not options["password"]:
            self.stdout.write(f"Senha:      {password}")
        elif not owner_created:
            self.stdout.write("Senha:      inalterada (a conta já existia)")

    def _office(self, options: dict[str, Any], password: str) -> tuple[Organization, User, bool]:
        organization, _ = Organization.objects.get_or_create(
            slug=options["slug"], defaults={"name": options["name"]}
        )
        owner = User.objects.filter(email=options["email"].casefold()).first()
        owner_created = owner is None
        if owner is None:
            owner = User.objects.create_user(email=options["email"], password=password)
            owner.full_name = "Operador Demonstração"
            owner.save(update_fields=["full_name"])
        Membership.objects.get_or_create(
            organization=organization,
            user=owner,
            defaults={"role": Membership.Role.OWNER},
        )
        OfficeProfile.objects.get_or_create(
            organization=organization,
            defaults={
                "legal_name": f"{organization.name} Serviços Contábeis Ltda",
                "contract_status": OfficeProfile.ContractStatus.ACTIVE,
            },
        )
        Connector.objects.get_or_create(
            organization=organization,
            kind=Connector.Kind.DOMINIO_AGENT,
            defaults={"enabled": True, "status": "healthy", "last_checked_at": timezone.now()},
        )
        return organization, owner, owner_created

    def _companies(self, organization: Organization, owner: User) -> list[ClientCompany]:
        membership = Membership.objects.get(organization=organization, user=owner)
        companies: list[ClientCompany] = []
        for index, (name, cnpj, code) in enumerate(COMPANIES):
            company, _ = ClientCompany.objects.get_or_create(
                organization=organization,
                dominio_code=code,
                defaults={
                    "name": name,
                    "cnpj_masked": cnpj,
                    "active": index != len(COMPANIES) - 1,
                    "last_dominio_sync_at": timezone.now() - dt.timedelta(hours=index),
                },
            )
            CompanyAccessGrant.objects.get_or_create(
                organization=organization,
                membership=membership,
                company=company,
                defaults={
                    "modules": list(OFFERED_MODULE_CODES),
                    "capabilities": ["read", "write", "dispatch"],
                },
            )
            companies.append(company)
        return companies

    def _modules_and_limits(self, organization: Organization) -> None:
        for code in OFFERED_MODULE_CODES:
            ProductModule.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"enabled": True, "enabled_at": timezone.now()},
            )
        today = timezone.localdate()
        period_start = today.replace(day=1)
        next_month = (period_start + dt.timedelta(days=32)).replace(day=1)
        for metric, included, consumed in (
            (UsageAllowance.Metric.COMPANIES, 25, len(COMPANIES)),
            (UsageAllowance.Metric.USERS, 10, 1),
            (UsageAllowance.Metric.DOCUMENTS, 2000, 412),
        ):
            UsageAllowance.objects.get_or_create(
                organization=organization,
                metric=metric,
                period_start=period_start,
                defaults={
                    "included": included,
                    "consumed": consumed,
                    "period_end": next_month - dt.timedelta(days=1),
                },
            )

    def _certificates(self, companies: list[ClientCompany], owner: User) -> None:
        for company in companies:
            if company.certificates.exists():
                continue
            pfx_bytes, password = _self_signed_pfx(company.name)
            store_certificate(
                company=company,
                pfx_bytes=pfx_bytes,
                password=password,
                label=f"A1 {company.name}",
                actor=owner,
            )

    def _documents(self, organization: Organization, companies: list[ClientCompany]) -> None:
        now = timezone.now()
        for index, company in enumerate(companies[:6]):
            AccumulatorRule.objects.get_or_create(
                organization=organization,
                company=company,
                name="Serviços tomados - padrão",
                defaults={
                    "match": {"service_code": SERVICE_CODES[index % len(SERVICE_CODES)]},
                    "accumulator_code": f"{1000 + index}",
                    "priority": 10,
                    "is_transitory": index % 3 == 2,
                },
            )
            AccumulatorObservation.objects.get_or_create(
                organization=organization,
                company=company,
                accumulator_code=f"{2000 + index}",
                service_code=SERVICE_CODES[(index + 1) % len(SERVICE_CODES)],
                defaults={"frequency": 6 + index, "last_used_at": now - dt.timedelta(days=index)},
            )
            for sequence in range(4):
                service_code = SERVICE_CODES[(index + sequence) % len(SERVICE_CODES)]
                amount = round(480.50 + index * 137 + sequence * 61.25, 2)
                create_document_and_artifact(
                    company=company,
                    original_xml=(
                        f"<nfse><id>{company.dominio_code}-{sequence}</id>"
                        f"<servico>{service_code}</servico><valor>{amount}</valor></nfse>"
                    ),
                    normalized_data={
                        "service_code": service_code,
                        "counterparty_ref": f"CP{index}{sequence}",
                        "amount": amount,
                        "issued_at": (now - dt.timedelta(days=sequence * 3)).isoformat(),
                    },
                    source_nsu=f"{company.dominio_code}{sequence:04d}",
                )

    def _dte(self, organization: Organization, companies: list[ClientCompany], owner: User) -> None:
        connector, _ = Connector.objects.get_or_create(
            organization=organization,
            kind=Connector.Kind.INTEGRA,
            defaults={"enabled": True, "status": "healthy"},
        )
        scope = [company for company in companies if company.active][:5]
        if not DteRun.objects.filter(organization=organization).exists():
            prepare_dte_run(
                organization=organization,
                connector=connector,
                companies=scope,
                actor=owner,
            )
        now = timezone.now()
        for index, company in enumerate(scope[:4]):
            for sequence, subject in enumerate(DTE_SUBJECTS[: 2 + index % 2]):
                source_isn = f"{company.dominio_code}-{sequence}"
                if DteMessage.objects.filter(
                    organization=organization, company=company, source_isn=source_isn
                ).exists():
                    continue
                sent_at = now - dt.timedelta(days=index * 2 + sequence, hours=sequence)
                DteMessage.objects.create(
                    organization=organization,
                    company=company,
                    source_isn=source_isn,
                    subject=subject,
                    sender="Receita Federal do Brasil",
                    sent_at=sent_at,
                    read_at=None if sequence == 0 else sent_at + dt.timedelta(hours=5),
                    raw_payload="",
                )


def _self_signed_pfx(common_name: str) -> tuple[bytes, str]:
    """A throwaway A1 so the certificate screen exercises the real custody path."""

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name[:64])])
    now = dt.datetime.now(dt.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=180))
        .sign(key, hashes.SHA256())
    )
    password = secrets.token_urlsafe(16)
    blob = pkcs12.serialize_key_and_certificates(
        name=hashlib.sha256(common_name.encode()).hexdigest()[:16].encode(),
        key=key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )
    return blob, password
