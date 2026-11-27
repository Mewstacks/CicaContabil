"""Retenção das Admissões: apaga ficha, arquivo e CPF com mais de 90 dias."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.admissions import services


class Command(BaseCommand):
    help = "Apaga os dados pessoais das admissões vencidas (90 dias)."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write(f"{services.expire()} admissões expiradas")
