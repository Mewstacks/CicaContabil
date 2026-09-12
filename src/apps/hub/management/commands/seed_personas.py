from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.hub.seeding import DEFAULT_PASSWORD, build_personas


class Command(BaseCommand):
    help = "Create one account per persona so every flow can be driven locally."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Shared password for every persona. Development only.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not getattr(settings, "SEED_DEMO_ALLOWED", False):
            raise CommandError(
                "seed_personas only runs with DEBUG on. It creates accounts with a known password."
            )

        with transaction.atomic():
            world = build_personas(password=options["password"])

        self.stdout.write(self.style.SUCCESS("Personas prontas."))
        self.stdout.write(f"Senha de todas:  {world.password}")
        self.stdout.write("")
        # No characters outside cp1252: the Windows console raises UnicodeEncodeError on
        # anything it cannot map, which would abort the command after the writes landed.
        self.stdout.write("Escritorio (/entrar/ -> /app/)")
        for role, user in sorted(world.office_users.items()):
            self.stdout.write(f"  {role:<10} {user.email}")
        self.stdout.write("")
        self.stdout.write("Plataforma (/platform/)")
        for role, user in sorted(world.platform_users.items()):
            self.stdout.write(f"  {role:<10} {user.email}")
        self.stdout.write("")
        if world.invitation_token:
            # Only the digest is stored, so this is the one moment the link exists.
            self.stdout.write("Convite pendente (abre uma vez):")
            self.stdout.write(f"  /ativar/{world.invitation_token}/")
