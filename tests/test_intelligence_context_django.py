from __future__ import annotations

from django.test import TestCase

from apps.intelligence.services import (
    MAX_MODEL_EVIDENCE_CARDS,
    MAX_MODEL_EVIDENCE_CHARACTERS,
    EvidenceCard,
    compact_model_evidence,
    next_conversation_summary,
)


class IntelligenceContextBudgetTests(TestCase):
    def test_model_packet_keeps_priority_evidence_within_a_fixed_budget(self) -> None:
        classification = [
            EvidenceCard("Regra aprovada", "Manual 2.1", "Classificação verificável.")
        ]
        attachment = [EvidenceCard("Anexo", "nota.pdf", "a" * 1_200)]
        catalogue = [
            EvidenceCard(f"Catálogo {index}", "Catálogo", "b" * 500) for index in range(10)
        ]

        packet = compact_model_evidence(classification, attachment, catalogue)

        self.assertEqual(packet[0]["label"], "Regra aprovada")
        self.assertLessEqual(len(packet), MAX_MODEL_EVIDENCE_CARDS)
        self.assertLessEqual(
            sum(len("".join(card.values())) for card in packet), MAX_MODEL_EVIDENCE_CHARACTERS
        )

    def test_summary_rolls_forward_without_retaining_a_full_transcript(self) -> None:
        summary = next_conversation_summary(
            previous="histórico anterior " * 80,
            question="Qual obrigação precisa de revisão?",
            answer="Revise a obrigação da fonte aprovada antes do vencimento.",
        )

        self.assertIn("Pergunta: Qual obrigação precisa de revisão?", summary)
        self.assertIn("Resposta: Revise a obrigação", summary)
        self.assertLessEqual(len(summary), 980)
