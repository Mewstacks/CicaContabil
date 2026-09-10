from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.intelligence.models import DominioSchemaObject, SemanticPackage
from apps.intelligence.package_governance import (
    activate_semantic_package,
    validate_semantic_package,
)
from apps.organizations.models import Organization


class SemanticPackageGovernanceTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.schema = DominioSchemaObject.objects.create(
            organization=self.organization,
            schema_name="dbo",
            object_name="obligation_source",
            object_kind=DominioSchemaObject.ObjectKind.TABLE,
            columns=[
                {"name": "company_code", "type": "varchar", "ordinal": 1, "nullable": False},
                {"name": "obligation_id", "type": "varchar", "ordinal": 2, "nullable": False},
                {"name": "description", "type": "varchar", "ordinal": 3, "nullable": True},
            ],
            structure_hash="a" * 64,
            sensitivity="restricted",
        )

    def package(self) -> SemanticPackage:
        return SemanticPackage.objects.create(
            organization=self.organization,
            module="Fiscal",
            tool_name="list_obligations",
            query_name="obligations_snapshot",
            source_reference="Domínio Fiscal",
            data_classification="restricted",
            company_key="company_code",
            primary_key="obligation_id",
            update_strategy=SemanticPackage.UpdateStrategy.SNAPSHOT_HASH,
            max_rows=100,
            max_period_days=90,
            max_staleness_seconds=3_600,
            schema_dependencies=[
                {
                    "schema_name": "dbo",
                    "object_name": "obligation_source",
                    "object_kind": "table",
                    "columns": ["company_code", "obligation_id", "description"],
                }
            ],
            test_specification={"card_fields": ["description"]},
        )

    def test_unapproved_schema_cannot_activate_a_package(self) -> None:
        package = self.package()

        validation = activate_semantic_package(package=package)

        package.refresh_from_db()
        self.assertFalse(validation.valid)
        self.assertFalse(package.enabled)
        self.assertIn("não aprovada", validation.reason)

    def test_only_approved_non_excluded_schema_can_activate_package(self) -> None:
        package = self.package()
        self.schema.approved_for_package = True
        self.schema.save(update_fields=["approved_for_package", "updated_at"])

        validation = activate_semantic_package(package=package)

        package.refresh_from_db()
        self.assertTrue(validation.valid)
        self.assertTrue(package.enabled)

        self.schema.sensitivity = "excluded"
        self.schema.save(update_fields=["sensitivity", "updated_at"])
        rejected = validate_semantic_package(package)
        self.assertFalse(rejected.valid)
        self.assertIn("excluídos", rejected.reason)

    def test_package_cannot_expose_a_column_missing_from_the_approved_object(self) -> None:
        package = self.package()
        self.schema.approved_for_package = True
        self.schema.save(update_fields=["approved_for_package", "updated_at"])
        package.schema_dependencies[0]["columns"].append("cpf")
        package.save(update_fields=["schema_dependencies", "updated_at"])

        validation = validate_semantic_package(package)

        self.assertFalse(validation.valid)
        self.assertIn("coluna ausente", validation.reason)

    def test_activation_command_uses_the_same_governance_gate(self) -> None:
        package = self.package()
        with self.assertRaises(CommandError):
            call_command(
                "activate_semantic_package",
                organization=str(self.organization.id),
                package=str(package.id),
            )

        self.schema.approved_for_package = True
        self.schema.save(update_fields=["approved_for_package", "updated_at"])
        output = StringIO()
        call_command(
            "activate_semantic_package",
            organization=str(self.organization.id),
            package=str(package.id),
            stdout=output,
        )
        package.refresh_from_db()
        self.assertTrue(package.enabled)
        self.assertIn("ativado", output.getvalue())
