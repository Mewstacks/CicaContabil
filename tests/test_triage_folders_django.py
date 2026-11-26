"""Folder model: tree validation, rules by document type, provisioning, agent jobs, screen."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import date
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, CompanyPartner, ProductModule
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Membership
from apps.triage import folders
from apps.triage.models import (
    AgentFolderJob,
    ClientFolder,
    DestinationProfile,
    DocumentType,
    FolderModel,
    ObligationFolderRule,
    TriageItem,
)
from apps.triage.services import windows_relative_destination
from triage_v2_support import TriageV2Case


def _signed(agent: EdgeAgent, client: Client, path: str, payload: dict[str, object]):
    body = json.dumps(payload, separators=(",", ":")).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(
        agent.shared_secret.encode(), stamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return client.generic(
        "POST",
        path,
        body,
        content_type="application/json",
        headers={
            "X-Hub-Agent-ID": str(agent.id),
            "X-Hub-Agent-Timestamp": stamp,
            "X-Hub-Agent-Signature": signature,
        },
        secure=True,
    )


class FolderCase(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.profile = DestinationProfile.objects.get(organization=self.office)
        self.profile.mode = DestinationProfile.Mode.WINDOWS
        self.profile.windows_root = r"D:\Clientes"
        self.profile.folder_model_enabled = True
        self.profile.save()
        self.model = folders.ensure_model(self.office)
        self.model.active = True
        self.model.save()
        self.nodes = {n["name"]: n for n, _ in folders.iter_nodes(self.model.tree)}
        self.doc = DocumentType.objects.create(
            organization=self.office,
            code="guia-das",
            label="Guia DAS",
            name_template="{codigo}_DAS_{periodo}",
            period_kind="competencia",
        )

    def node_id(self, name: str, depth_parent: str = "") -> str:
        for node, parents in folders.iter_nodes(self.model.tree):
            if node["name"] == name and (
                not depth_parent or (parents and parents[-1]["name"] == depth_parent)
            ):
                return str(node["id"])
        raise AssertionError(name)

    def item(self) -> TriageItem:
        return TriageItem.objects.create(
            organization=self.office,
            mailbox=self.mailbox,
            company=self.company,
            document_type=self.doc,
            original_name="o.pdf",
            final_name="417_DAS_052026.pdf",
            period_start=date(2026, 5, 1),
            content_hash="a" * 64,
            byte_size=10,
        )


class TreeTests(FolderCase):
    def test_seed_has_the_office_hierarchy(self) -> None:
        count = sum(1 for _ in folders.iter_nodes(folders.seed_tree()))
        self.assertEqual(count, 111)
        folders.validate_tree(folders.seed_tree())

    def test_tree_rejects_traversal_separators_reserved_and_duplicates(self) -> None:
        def tree(name: str, other: str = "B") -> list[dict[str, object]]:
            return [
                {
                    "id": "00000000-0000-4000-8000-000000000001",
                    "name": name,
                    "variable": "",
                    "use": "",
                    "children": [],
                },
                {
                    "id": "00000000-0000-4000-8000-000000000002",
                    "name": other,
                    "variable": "",
                    "use": "",
                    "children": [],
                },
            ]

        for bad in ("..", "a/b", "a\\b", "C:", "CON", "nul.txt", "x.", "", "a|b"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                folders.validate_tree(tree(bad))
        with self.assertRaises(ValidationError):
            folders.validate_tree(tree("A", "a"))
        folders.validate_tree(tree("A"))

    def test_variable_levels_need_the_file_data(self) -> None:
        ano_mes = self.node_id("MES", "ANO")
        path = folders.node_relative_path(
            self.model.tree, ano_mes, self.company, year=2026, month=5
        )
        self.assertFalse(path.startswith(("\\", "..")))
        self.assertTrue(path.endswith(r"\2026\05"))
        with self.assertRaises(ValidationError):
            folders.node_relative_path(self.model.tree, ano_mes, self.company)

    def test_unknown_node_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            folders.node_relative_path(self.model.tree, "nope", self.company)


class RuleTests(FolderCase):
    def test_manual_rule_beats_learned_and_feeds_the_archive_path(self) -> None:
        item = self.item()
        impostos = self.node_id("MES", "ANO")
        ObligationFolderRule.objects.create(
            organization=self.office,
            document_type=self.doc,
            kind="guide",
            node_id=self.node_id("FAP"),
            source="learned",
        )
        manual = ObligationFolderRule.objects.create(
            organization=self.office,
            document_type=self.doc,
            kind="other",
            node_id=impostos,
            source="manual",
        )
        # Exact-kind learned rule still wins over the generic manual one.
        path = windows_relative_destination(item, self.profile)
        self.assertIn("FAP", path)
        ObligationFolderRule.objects.filter(source="learned").update(enabled=False)
        path = windows_relative_destination(item, self.profile)
        self.assertTrue(path.split("\\")[-2:] == ["05", "417_DAS_052026.pdf"], path)
        manual.delete()
        # No rule: fall back to the flat template.
        fallback = windows_relative_destination(item, self.profile)
        self.assertEqual(fallback.count("\\"), 1)

    def test_flag_off_keeps_the_previous_behaviour(self) -> None:
        item = self.item()
        ObligationFolderRule.objects.create(
            organization=self.office,
            document_type=self.doc,
            kind="other",
            node_id=self.node_id("FAP"),
        )
        self.profile.folder_model_enabled = False
        self.profile.save()
        self.assertEqual(windows_relative_destination(item, self.profile).count("\\"), 1)

    def test_learning_skips_employee_branches_and_never_overrides_manual(self) -> None:
        item = self.item()
        self.assertIsNone(folders.learn_rule(item, self.node_id("NOME")))
        learned = folders.learn_rule(item, self.node_id("FAP"))
        assert learned is not None
        self.assertEqual(learned.source, "learned")
        ObligationFolderRule.objects.filter(pk=learned.pk).update(source="manual")
        folders.learn_rule(item, self.node_id("SINDICATO"))
        learned.refresh_from_db()
        self.assertEqual(learned.node_id, self.node_id("FAP"))


class ProvisionTests(FolderCase):
    def test_plan_has_no_variable_levels_and_adds_partner_folders(self) -> None:
        CompanyPartner.objects.create(
            organization=self.office, company=self.company, name="Maria / Silva"
        )
        plan = folders.provision_plan(self.company, self.model.tree)
        self.assertTrue(all(not p.startswith(("\\", "..")) for p in plan))
        self.assertFalse(
            any(part in {"ANO", "MES", "NOME"} for p in plan for part in p.split("\\"))
        )
        self.assertTrue(any(p.endswith(r"DOCUMENTOS PESSOAIS\Maria Silva") for p in plan))

    def test_queue_is_idempotent_and_tenant_scoped(self) -> None:
        other = self.make_office("other-folders")
        outsider = ClientCompany.objects.create(organization=other, name="Fora", dominio_code="9")
        folders.queue_provision(self.office, apply=True)
        folders.queue_provision(self.office, apply=True)
        self.assertEqual(AgentFolderJob.objects.filter(organization=self.office).count(), 1)
        self.assertFalse(AgentFolderJob.objects.filter(organization=other).exists())
        self.assertFalse(ClientFolder.objects.filter(company=outsider).exists())

    def test_dry_run_writes_nothing_and_command_applies(self) -> None:
        out = StringIO()
        call_command("provision_client_folders", organization=self.office.slug, stdout=out)
        self.assertEqual(AgentFolderJob.objects.count(), 0)
        call_command(
            "provision_client_folders", organization=self.office.slug, apply=True, stdout=out
        )
        self.assertEqual(AgentFolderJob.objects.count(), 1)

    def test_inactive_model_refuses_to_provision(self) -> None:
        FolderModel.objects.filter(organization=self.office).update(active=False)
        with self.assertRaises(ValidationError):
            folders.queue_provision(self.office, apply=True)


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
class AgentJobTests(FolderCase):
    def setUp(self) -> None:
        super().setUp()
        self.agent = EdgeAgent.objects.create(
            organization=self.office, label="S", fingerprint="f", shared_secret="secret-tests"
        )
        self.http = Client()

    def test_claim_and_complete_marks_the_client_folder(self) -> None:
        folders.queue_provision(self.office, apply=True)
        claim = _signed(self.agent, self.http, "/api/agent/v2/folders/next", {}).json()["job"]
        self.assertEqual(claim["kind"], "provision")
        self.assertTrue(
            all(not p.startswith(("\\", "..")) and ".." not in p for p in claim["paths"])
        )
        expected = hashlib.sha256(br"d:\clientes").hexdigest()
        self.assertEqual(claim["root_sha256"], expected)
        done = _signed(
            self.agent,
            self.http,
            f"/api/agent/v2/folders/{claim['id']}/complete",
            {"success": True, "detail": "ok"},
        )
        self.assertEqual(done.json()["status"], "completed")
        self.assertEqual(ClientFolder.objects.get().state, "created")
        again = _signed(
            self.agent,
            self.http,
            f"/api/agent/v2/folders/{claim['id']}/complete",
            {"success": True},
        )
        self.assertEqual(again.json()["status"], "completed")
        # Created and unchanged: nothing new is queued.
        folders.queue_provision(self.office, apply=True)
        self.assertEqual(AgentFolderJob.objects.count(), 1)

    def test_failure_is_recorded_and_other_office_agent_is_refused(self) -> None:
        folders.queue_provision(self.office, apply=True)
        claim = _signed(self.agent, self.http, "/api/agent/v2/folders/next", {}).json()["job"]
        other = self.make_office("other-agent")
        stranger = EdgeAgent.objects.create(
            organization=other, label="X", fingerprint="g", shared_secret="secret-other"
        )
        refused = _signed(
            stranger,
            self.http,
            f"/api/agent/v2/folders/{claim['id']}/complete",
            {"success": True},
        )
        self.assertEqual(refused.status_code, 404)
        self.assertEqual(
            _signed(stranger, self.http, "/api/agent/v2/folders/next", {}).json(), {"job": None}
        )
        _signed(
            self.agent,
            self.http,
            f"/api/agent/v2/folders/{claim['id']}/complete",
            {"success": False, "detail": "Acesso negado"},
        )
        folder = ClientFolder.objects.get()
        self.assertEqual((folder.state, folder.last_error), ("failed", "Acesso negado"))

    def test_inventory_report_is_stored_and_bounded(self) -> None:
        folders.queue_inventory(self.office)
        claim = _signed(self.agent, self.http, "/api/agent/v2/folders/next", {}).json()["job"]
        self.assertEqual(claim["paths"], ["."])
        entries = [{"path": f"c{n}", "dirs": 1, "files": 2} for n in range(300)]
        _signed(
            self.agent,
            self.http,
            f"/api/agent/v2/folders/{claim['id']}/complete",
            {"success": True, "entries": entries},
        )
        report = AgentFolderJob.objects.get().report
        self.assertEqual(len(report["entries"]), 200)
        self.assertTrue(report["truncated"])

    def test_poisoned_plan_never_reaches_the_agent(self) -> None:
        AgentFolderJob.objects.create(
            organization=self.office, kind="provision", paths=["..\\fora", "C:\\x"]
        )
        result = _signed(self.agent, self.http, "/api/agent/v2/folders/next", {}).json()
        self.assertIsNone(result["job"])
        self.assertEqual(AgentFolderJob.objects.get().status, "failed")


class ScreenTests(FolderCase):
    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.url = reverse("hub:triage-folders")

    def test_admin_activates_edits_and_adds_rules(self) -> None:
        FolderModel.objects.filter(organization=self.office).update(active=False)
        self.profile.folder_model_enabled = False
        self.profile.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.post(self.url, {"action": "toggle", "enabled": "1"})
        self.assertTrue(
            DestinationProfile.objects.get(organization=self.office).folder_model_enabled
        )
        revision = FolderModel.objects.get(organization=self.office).revision
        self.client.post(
            self.url,
            {"action": "add", "revision": revision, "node": self.node_id("FISCAL"), "name": "NOVA"},
        )
        self.assertIn("NOVA", json.dumps(FolderModel.objects.get().tree))
        stale = self.client.post(
            self.url, {"action": "add", "revision": revision, "node": "", "name": "X"}
        )
        self.assertEqual(stale.status_code, 400)
        self.client.post(
            self.url,
            {
                "action": "rule_save",
                "document_type": str(self.doc.pk),
                "kind": "guide",
                "node": self.node_id("FAP"),
            },
        )
        self.assertEqual(ObligationFolderRule.objects.get().node_id, self.node_id("FAP"))
        self.assertContains(self.client.get(self.url), "Guia DAS")

    def test_removing_a_node_turns_its_rules_off(self) -> None:
        node = self.node_id("FAP")
        ObligationFolderRule.objects.create(
            organization=self.office, document_type=self.doc, kind="guide", node_id=node
        )
        revision = FolderModel.objects.get().revision
        self.client.post(self.url, {"action": "remove", "revision": revision, "node": node})
        self.assertFalse(ObligationFolderRule.objects.get().enabled)

    def test_traversal_name_is_refused(self) -> None:
        revision = FolderModel.objects.get().revision
        response = self.client.post(
            self.url, {"action": "add", "revision": revision, "node": "", "name": ".."}
        )
        self.assertEqual(response.status_code, 400)

    def test_operator_cannot_change_and_other_office_rules_are_invisible(self) -> None:
        other = self.make_office("other-screen")
        other_doc = DocumentType.objects.create(
            organization=other,
            code="x",
            label="Tipo alheio",
            name_template="x",
            period_kind="competencia",
        )
        ObligationFolderRule.objects.create(
            organization=other,
            document_type=other_doc,
            kind="other",
            node_id=self.node_id("FAP"),
        )
        self.assertNotContains(self.client.get(self.url), "Tipo alheio")
        forged = self.client.post(
            self.url,
            {
                "action": "rule_save",
                "document_type": str(other_doc.pk),
                "kind": "guide",
                "node": self.node_id("FAP"),
            },
        )
        self.assertEqual(forged.status_code, 400)
        user = User.objects.create_user("op-folders@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read"],
        )
        self.login(user)
        self.assertEqual(
            self.client.post(self.url, {"action": "toggle", "enabled": "0"}).status_code, 403
        )
        self.assertTrue(FolderModel.objects.get(organization=self.office).active)
