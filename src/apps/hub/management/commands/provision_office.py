"""Provision a full-access office (all modules, manual billing) idempotently.

Used to open an office that is migrating from another system and must see every module
from day one (e.g. Fedrizzi Contabilidade). It only creates rows for ONE organization and
never touches another office. Re-running changes nothing that already exists.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.encryption import blind_index
from apps.hub.models import OfficeProfile, ProductModule
from apps.organizations.models import Membership, Organization
from apps.platform.models import Entitlement, Plan, TenantContract, TenantLifecycle

PLAN_CODE = "completo-interno"


class Command(BaseCommand):
    help = "Cria (ou completa) um escritório com todos os módulos habilitados."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--name", required=True)
        parser.add_argument("--slug", required=True)
        parser.add_argument("--cnpj", default="", help="CNPJ do escritório (opcional).")
        parser.add_argument("--owner-email", default="", help="Dono; criado sem senha.")
        parser.add_argument("--owner-name", default="")
        parser.add_argument("--reference", default="", help="Texto livre do contrato.")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        name = str(options["name"]).strip()
        slug = str(options["slug"]).strip().casefold()
        cnpj = "".join(ch for ch in str(options["cnpj"]) if ch.isalnum()).upper()
        owner_email = str(options["owner_email"]).strip().casefold()
        if not name or not slug:
            raise CommandError("Nome e slug são obrigatórios.")
        codes = [code for code, _label in ProductModule.Code.choices]
        today = timezone.localdate()
        now = timezone.now()

        organization = Organization.objects.filter(slug=slug).first()
        created = organization is None
        if options["dry_run"]:
            state = "criaria" if created else "completaria"
            self.stdout.write(f"dry-run: {state} {name} com {len(codes)} módulos")
            transaction.set_rollback(True)
            return
        if organization is None:
            organization = Organization.objects.create(name=name, slug=slug, is_active=True)

        profile, _ = OfficeProfile.objects.get_or_create(
            organization=organization,
            defaults={
                "legal_name": name,
                "contract_status": OfficeProfile.ContractStatus.ACTIVE,
                "nfse_collection_mode": OfficeProfile.NfseCollectionMode.PROCURACAO,
                "require_dominio_code": True,
            },
        )
        if cnpj and not profile.cnpj_hash:
            hashed = blind_index(cnpj, namespace="office-cnpj")
            if OfficeProfile.objects.filter(cnpj_hash=hashed).exclude(pk=profile.pk).exists():
                raise CommandError("Este CNPJ já pertence a outro escritório.")
            profile.cnpj = cnpj
            profile.cnpj_hash = hashed
            profile.save(update_fields=["cnpj", "cnpj_hash", "updated_at"])

        plan, _ = Plan.objects.get_or_create(
            code=PLAN_CODE,
            defaults={
                "name": "Completo (interno)",
                "version": 1,
                "is_active": False,
                "modules": codes,
            },
        )
        if not TenantContract.objects.filter(organization=organization).exists():
            TenantContract.objects.create(
                organization=organization,
                plan=plan,
                monthly_price_cents=0,
                monthly_price_locked=True,
                status=TenantContract.Status.ACTIVE,
                billing_mode=TenantContract.BillingMode.MANUAL,
                reference=str(options["reference"])[:120],
                starts_on=today,
                selected_modules=codes,
            )
        TenantLifecycle.objects.get_or_create(
            organization=organization,
            defaults={
                "state": TenantLifecycle.State.ACTIVE,
                "reason": "Escritório aberto com todos os módulos.",
            },
        )
        for code in codes:
            module, _ = ProductModule.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"enabled": True, "enabled_at": now},
            )
            if not module.enabled:
                module.enabled = True
                module.enabled_at = now
                module.save(update_fields=["enabled", "enabled_at", "updated_at"])
            entitlement, _ = Entitlement.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"enabled": True},
            )
            if not entitlement.enabled:
                entitlement.enabled = True
                entitlement.save(update_fields=["enabled", "updated_at"])

        if owner_email:
            user = User.objects.filter(email=owner_email).first()
            if user is None:
                user = User(email=owner_email, full_name=str(options["owner_name"])[:150])
                user.set_unusable_password()
                user.save()
            Membership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": Membership.Role.OWNER, "is_active": True},
            )
        record_event(
            action="hub.office.provisioned",
            organization=organization,
            target=organization,
            metadata={"modules": codes, "created": created},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{name}: {'criado' if created else 'completado'}; "
                f"{len(codes)} módulos habilitados."
            )
        )
