import hashlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_export_document_migration_preserves_legacy_manifest_and_rebuilds_links():
    executor = MigrationExecutor(connection)
    other_apps = [node for node in executor.loader.graph.leaf_nodes() if node[0] != "hub"]
    before = [*other_apps, ("hub", "0066_alter_nfsesync_status")]
    after = [*other_apps, ("hub", "0067_nfseexport_documents")]
    executor.migrate(before)
    try:
        old_apps = executor.loader.project_state(before).apps
        Organization = old_apps.get_model("organizations", "Organization")
        Company = old_apps.get_model("hub", "ClientCompany")
        Document = old_apps.get_model("hub", "NfseDocument")
        Export = old_apps.get_model("hub", "NfseExport")
        office = Organization.objects.create(name="Legacy migration", slug="legacy-migration")
        company = Company.objects.create(organization=office, name="Legacy company")
        documents = Document.objects.bulk_create(
            [
                Document(
                    organization=office,
                    company=company,
                    document_hash=hashlib.sha256(str(index).encode()).hexdigest(),
                    original_xml=f"<nfse id='{index}' />",
                    normalized_data={},
                )
                for index in range(1001)
            ]
        )
        snapshot = {
            "documents": [{"document_id": str(doc.pk)} for doc in documents],
            "layout": "legacy-layout",
        }
        export = Export.objects.create(
            organization=office,
            document_count=1001,
            content_hash="a" * 64,
            snapshot=snapshot,
            content="private/legacy-package.zip",
        )
        invalid = Export.objects.create(
            organization=office,
            document_count=1,
            content_hash="b" * 64,
            snapshot={"documents": [{"document_id": "invalid"}]},
        )
        executor = MigrationExecutor(connection)
        executor.migrate(after)
        new_apps = executor.loader.project_state(after).apps
        migrated = new_apps.get_model("hub", "NfseExport").objects.get(pk=export.pk)
        assert migrated.documents.count() == 1001
        assert migrated.snapshot == snapshot
        assert migrated.content.name == "private/legacy-package.zip"
        assert migrated.content_hash == "a" * 64
        assert (
            not new_apps.get_model("hub", "NfseExport")
            .objects.get(pk=invalid.pk)
            .documents.exists()
        )
        assert new_apps.get_model("hub", "NfseDocument").objects.count() == 1001
        # Reversing the added index must not erase the original archive or its manifest.
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        preserved = old_apps.get_model("hub", "NfseExport").objects.get(pk=export.pk)
        assert preserved.snapshot == snapshot
        assert preserved.content.name == "private/legacy-package.zip"
    finally:
        MigrationExecutor(connection).migrate(after)
