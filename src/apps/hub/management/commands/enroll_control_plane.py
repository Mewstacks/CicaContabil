# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
import os
from urllib.request import Request
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.hub.controlplane import (
    ControlPlaneError,
    _fetch_json,
    apply_control,
    generate_device_private_key,
    normalize_controller_url,
    public_key_for_private,
)
from apps.hub.models import ControlPlaneBinding
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Vincula esta instalação Hub ao CRMew usando um código de uso único."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID da organização Hub")
        parser.add_argument(
            "--controller-url", required=True, help="URL base do CRMew, sem /control/v1"
        )

    def handle(self, *args, **options) -> None:
        code = os.environ.get("HUB_CONTROL_ENROLLMENT_CODE", "").strip()
        if not code:
            raise CommandError(
                "Defina HUB_CONTROL_ENROLLMENT_CODE no ambiente; "
                "não passe o código pela linha de comando."
            )
        try:
            organization = Organization.objects.get(id=UUID(options["organization"]))
        except (Organization.DoesNotExist, ValueError) as exc:
            raise CommandError("Organização Hub não encontrada.") from exc
        if ControlPlaneBinding.objects.filter(organization=organization).exists():
            raise CommandError("Esta organização já possui vínculo com o CRMew.")

        private_key = generate_device_private_key()
        body = json.dumps(
            {"code": code, "public_key": public_key_for_private(private_key)},
            separators=(",", ":"),
        ).encode()
        try:
            root = normalize_controller_url(options["controller_url"])
        except ControlPlaneError as exc:
            raise CommandError(str(exc)) from exc
        request = Request(f"{root}/control/v1/enroll/", data=body, method="POST")  # noqa: S310 - root was normalized above
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        try:
            response = _fetch_json(request)
            installation_id = UUID(str(response["installation_id"]))
            controller_public_key = str(response["controller_public_key"])
            control = response["control"]
            signature = response["signature"]
        except (ControlPlaneError, KeyError, ValueError, TypeError) as exc:
            raise CommandError(f"Enrollment recusado pelo CRMew: {exc}") from exc

        with transaction.atomic():
            binding = ControlPlaneBinding.objects.create(
                organization=organization,
                remote_installation_id=installation_id,
                controller_url=root,
                device_private_key=private_key,
                controller_public_key=controller_public_key,
            )
            try:
                apply_control(binding, control, signature)
            except ControlPlaneError:
                binding.delete()
                raise
        self.stdout.write(
            self.style.SUCCESS("Instalação vinculada ao CRMew e autorização aplicada.")
        )
