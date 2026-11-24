"""Comandos de operação sem outro caminho de teste: release, reclassificação, seed Contraprova."""

from __future__ import annotations

import json
import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.crosscheck.models import CrosscheckRun
from apps.hub.models import ClientCompany
from crosscheck_support import CrosscheckCase


class ReleaseTests(SimpleTestCase):
    def test_usa_enderecos_diretos_e_migra_os_dois_bancos(self) -> None:
        from config import release

        env = {
            "DATABASE_URL_UNPOOLED": "postgres://direto/main",
            "KNOWLEDGE_DATABASE_URL_UNPOOLED": "postgres://direto/knowledge",
        }
        with (
            patch.dict(os.environ, env, clear=False),
            patch("django.setup") as setup,
            patch("django.core.management.call_command") as migrate,
        ):
            release.main()

            assert os.environ["DATABASE_URL"] == "postgres://direto/main"
            assert os.environ["KNOWLEDGE_DATABASE_URL"] == "postgres://direto/knowledge"
            assert os.environ["DB_PGBOUNCER"] == "false"

        setup.assert_called_once_with()
        assert [call.kwargs["database"] for call in migrate.call_args_list] == [
            "default",
            "knowledge",
        ]
        assert all(call.kwargs["interactive"] is False for call in migrate.call_args_list)

    def test_sem_enderecos_diretos_mantem_os_atuais(self) -> None:
        from config import release

        with (
            patch.dict(os.environ, {"DATABASE_URL": "postgres://pool/main"}, clear=False),
            patch("django.setup"),
            patch("django.core.management.call_command"),
        ):
            os.environ.pop("DATABASE_URL_UNPOOLED", None)
            os.environ.pop("KNOWLEDGE_DATABASE_URL_UNPOOLED", None)
            release.main()

            assert os.environ["DATABASE_URL"] == "postgres://pool/main"


class ReclassifyCommandTests(CrosscheckCase):
    databases = {"default", "knowledge"}

    def test_escritorio_inexistente_e_recusado(self) -> None:
        with self.assertRaisesMessage(CommandError, "Escritório não encontrado"):
            call_command("reclassify_nfse_from_backup", organization="nao-existe")

    def test_erro_de_regra_vira_erro_de_comando(self) -> None:
        with (
            patch(
                "apps.hub.management.commands.reclassify_nfse_from_backup.reclassify_nfse_from_backup",
                side_effect=ValueError("sem backup elegível"),
            ),
            self.assertRaisesMessage(CommandError, "sem backup elegível"),
        ):
            call_command("reclassify_nfse_from_backup", organization=self.office.slug)

    def test_previa_nao_persiste_e_imprime_json(self) -> None:
        class Resumo:
            def payload(self) -> dict[str, object]:
                return {"apply": False, "total": 0}

        with patch(
            "apps.hub.management.commands.reclassify_nfse_from_backup.reclassify_nfse_from_backup",
            return_value=Resumo(),
        ) as chamado:
            saida = StringIO()
            call_command("reclassify_nfse_from_backup", organization=self.office.slug, stdout=saida)

        assert json.loads(saida.getvalue()) == {"apply": False, "total": 0}
        assert chamado.call_args.kwargs["apply"] is False

    def test_apply_repassa_a_flag(self) -> None:
        class Resumo:
            def payload(self) -> dict[str, object]:
                return {"apply": True}

        with patch(
            "apps.hub.management.commands.reclassify_nfse_from_backup.reclassify_nfse_from_backup",
            return_value=Resumo(),
        ) as chamado:
            call_command(
                "reclassify_nfse_from_backup",
                organization=self.office.slug,
                apply=True,
                stdout=StringIO(),
            )

        assert chamado.call_args.kwargs["apply"] is True


class SeedCrosscheckTests(CrosscheckCase):
    databases = {"default", "knowledge"}

    def seed(self, **opcoes: object) -> str:
        saida = StringIO()
        call_command(
            "seed_crosscheck",
            organization=self.office.slug,
            user=self.user.email,
            stdout=saida,
            **opcoes,
        )
        return saida.getvalue()

    @override_settings(DEBUG=False)
    def test_recusa_sem_debug(self) -> None:
        with self.assertRaisesMessage(CommandError, "só roda com DEBUG"):
            self.seed()

    @override_settings(DEBUG=True)
    def test_escritorio_ou_usuario_inexistente(self) -> None:
        with self.assertRaisesMessage(CommandError, "não encontrado"):
            call_command(
                "seed_crosscheck",
                organization="nao-existe",
                user=self.user.email,
                stdout=StringIO(),
            )

    @override_settings(DEBUG=True)
    def test_sem_empresa_ativa_e_recusado(self) -> None:
        ClientCompany.objects.filter(organization=self.office).update(active=False)

        with self.assertRaisesMessage(CommandError, "não tem empresas ativas"):
            self.seed()

    @override_settings(DEBUG=True)
    def test_cria_conferencias_e_nao_repete_sem_force(self) -> None:
        self.seed()

        total = CrosscheckRun.objects.filter(organization=self.office).count()
        estados = set(
            CrosscheckRun.objects.filter(organization=self.office).values_list("state", flat=True)
        )
        assert total > 5
        assert {
            CrosscheckRun.State.DONE,
            CrosscheckRun.State.FAILED,
            CrosscheckRun.State.QUEUED,
            CrosscheckRun.State.PROCESSING,
            CrosscheckRun.State.CANCELED,
        } <= estados

        assert "nada a fazer" in self.seed()
        assert CrosscheckRun.objects.filter(organization=self.office).count() == total
