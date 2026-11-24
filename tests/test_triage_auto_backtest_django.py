"""AC-11.6: auto-aprovação opt-in com porquê e amostra; backtest sobre conjunto rotulado."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from django.core.management import call_command

from apps.triage.auto import is_sampled
from apps.triage.backtest import run_backtest
from apps.triage.extraction import extract_item
from apps.triage.models import DocumentType, TriageItem, TriagePolicy
from apps.triage.reclassify import bump_engine_version
from apps.triage.transitions import TriageStatus
from triage_v2_support import TriageV2Case

CNPJ = "12.345.678/0001-95"


class AutoCase(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.type = DocumentType.objects.create(
            organization=self.office,
            code="extrato",
            label="Extrato",
            name_template="{codigo}_EXTRATO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
            keywords=["saldo anterior"],
        )

    def policy(self, **fields: Any) -> TriagePolicy:
        base: dict[str, Any] = {"auto_approve": True, "auto_warmup": 0, "auto_sample_every": 1000}
        base.update(fields)
        return TriagePolicy.objects.update_or_create(organization=self.office, defaults=base)[0]

    def good(self, name: str = "extrato.xml", body: str = "") -> TriageItem:
        text = f"<a>CNPJ {CNPJ} saldo anterior 09/2026 {body}</a>"
        item = self.released(filename=name, payload=text.encode())
        # Same bytes in one office are duplicates: make each payload distinct.
        return extract_item(item_id=item.pk)

    def human_archived(self, count: int) -> None:
        for index in range(count):
            TriageItem.objects.create(
                organization=self.office,
                original_name=f"h{index}.pdf",
                status=TriageStatus.ARCHIVED,
                reviewed_by=self.owner,
                content_hash=f"{index:064d}",
            )


class AutoApprovalTests(AutoCase):
    def test_default_is_review_everything(self) -> None:
        item = self.good("a1.xml", "um")
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.auto_decision, "")

    def test_opt_in_approves_what_the_engine_accepted_and_records_why(self) -> None:
        self.policy()
        item = self.good("a2.xml", "dois")
        self.assertEqual(item.status, TriageStatus.READY_TO_ARCHIVE)
        self.assertEqual(item.auto_decision, "auto")
        self.assertIsNone(item.reviewed_by)
        reason = item.ai_fields["Auto"]["evidencia"]
        self.assertIn("CNPJ no conteúdo", reason)
        self.assertIn("Extrato", reason)
        self.assertTrue(item.events.filter(note__startswith="Aprovado automaticamente").exists())

    def test_warmup_keeps_the_first_documents_in_review(self) -> None:
        self.policy(auto_warmup=5)
        self.human_archived(4)
        self.assertEqual(self.good("a3.xml", "tres").status, TriageStatus.AWAITING_REVIEW)
        self.human_archived(1)
        self.assertEqual(self.good("a4.xml", "quatro").status, TriageStatus.READY_TO_ARCHIVE)

    def test_auto_approved_items_do_not_count_as_human_reviews(self) -> None:
        self.policy(auto_warmup=2)
        TriageItem.objects.create(
            organization=self.office,
            original_name="x.pdf",
            status=TriageStatus.ARCHIVED,
            auto_decision="auto",
            content_hash="a" * 64,
        )
        self.assertEqual(self.good("a5.xml", "cinco").status, TriageStatus.AWAITING_REVIEW)

    def test_sample_goes_to_a_person_with_the_reason(self) -> None:
        self.policy(auto_sample_every=1)
        item = self.good("a6.xml", "seis")
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.auto_decision, "sampled")
        self.assertTrue(item.events.filter(note__startswith="Amostra de auditoria").exists())

    def test_sampling_is_deterministic_and_roughly_one_in_n(self) -> None:
        ids = [f"{index:032x}" for index in range(2000)]
        picked = [value for value in ids if is_sampled(value, 20)]
        self.assertEqual(picked, [value for value in ids if is_sampled(value, 20)])
        self.assertTrue(60 <= len(picked) <= 140)
        self.assertTrue(all(is_sampled(value, 1) for value in ids[:10]))

    def test_no_proof_conflict_or_missing_type_stay_in_review(self) -> None:
        self.policy()
        cases = {
            "n1.xml": "<a>saldo anterior 09/2026 sem empresa</a>",
            "n2.xml": f"<a>CNPJ {CNPJ} 09/2026 sem tipo</a>",
            "n3.xml": f"<a>CNPJ {CNPJ} saldo anterior sem periodo</a>",
        }
        for name, text in cases.items():
            item = self.released(filename=name, payload=text.encode())
            self.assertEqual(extract_item(item_id=item.pk).status, TriageStatus.AWAITING_REVIEW)

    def test_each_office_has_its_own_switch(self) -> None:
        other = self.make_office("e11-auto-other")
        TriagePolicy.objects.create(organization=other, auto_approve=True, auto_warmup=0)
        self.assertEqual(self.good("o1.xml", "outro").status, TriageStatus.AWAITING_REVIEW)

    def test_the_approved_item_can_be_archived_like_any_other(self) -> None:
        from apps.triage.services import archive_internal, update_review_fields

        self.policy()
        item = self.good("a7.xml", "sete")
        archived = archive_internal(item=item, actor=self.owner)
        self.assertEqual(archived.status, TriageStatus.ARCHIVED)
        del update_review_fields


class EngineVersionTests(AutoCase):
    def test_bumping_the_version_reclassifies_pending_items(self) -> None:
        item = self.released(filename="v1.xml", payload=b"<a>sem pista</a>")
        item = extract_item(item_id=item.pk)
        self.assertIsNone(item.company)
        from apps.hub.models import ClientCompany

        ClientCompany.objects.filter(pk=self.company.pk).update(name="Sem Pista Padaria Sol")
        self.assertEqual(bump_engine_version(self.office), 2)
        item.refresh_from_db()
        self.assertEqual(item.engine_version, 2)
        self.assertTrue(item.events.filter(note__startswith="Reclassificado").exists())

    def test_bump_never_touches_another_office(self) -> None:
        other = self.make_office("e11-bump-other")
        bump_engine_version(self.office)
        self.assertFalse(TriagePolicy.objects.filter(organization=other).exists())


class BacktestTests(AutoCase):
    ROWS = [
        {
            "name": "a.xml",
            "text": f"CNPJ {CNPJ} saldo anterior 09/2026",
            "expected": {"company": "417", "type": "extrato", "period": "2026-09"},
        },
        {
            "name": "b.xml",
            "text": f"CNPJ {CNPJ} saldo anterior 08/2026",
            "expected": {"company": "417", "type": "extrato", "period": "2026-08"},
        },
        {
            "name": "c.xml",
            "text": f"CNPJ {CNPJ} saldo anterior 07/2026",
            "expected": {"company": "999", "type": "extrato", "period": "2026-07"},
        },
        {
            "name": "d.xml",
            "text": "nada reconhecível",
            "expected": {"company": "417", "type": "extrato", "period": "2026-06"},
        },
    ]

    def test_accuracy_is_of_what_was_answered_and_coverage_of_everything(self) -> None:
        report = run_backtest(self.office, self.ROWS)
        company = report.fields["company"]
        self.assertEqual((company.total, company.answered, company.correct), (4, 3, 2))
        self.assertAlmostEqual(company.accuracy, 2 / 3)
        self.assertAlmostEqual(company.coverage, 3 / 4)
        self.assertEqual(report.fields["type"].answered, 3)
        self.assertEqual(report.fields["period"].correct, 3)
        self.assertEqual(report.wrong_company, 1)

    def test_empty_dataset_is_zero_not_an_error(self) -> None:
        report = run_backtest(self.office, [])
        self.assertEqual(report.fields["company"].total, 0)
        self.assertEqual(report.fields["company"].accuracy, 0.0)

    def test_backtest_never_writes_items(self) -> None:
        before = TriageItem.objects.count()
        run_backtest(self.office, self.ROWS)
        self.assertEqual(TriageItem.objects.count(), before)

    def test_command_prints_accuracy_and_coverage(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "set.json"
            path.write_text(json.dumps(self.ROWS), encoding="utf-8")
            out = StringIO()
            call_command(
                "triagem_backtest", organization=self.office.slug, dataset=str(path), stdout=out
            )
        text = out.getvalue()
        self.assertIn("Acurácia", text)
        self.assertIn("Cobertura", text)
        self.assertIn("66,7%", text)

    def test_command_refuses_an_unknown_office_and_a_bad_file(self) -> None:
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("triagem_backtest", organization="nao-existe", dataset="x.json")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command("triagem_backtest", organization=self.office.slug, dataset=str(path))
