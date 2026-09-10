from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from runtime.trainer.runner import (
    TrainingRunnerError,
    load_job_spec,
    load_manifest,
    main,
    manifest_sha256,
    prepare_workspace,
    run_training,
)


class TrainingRunnerTests(TestCase):
    def job(self, manifest_hash: str) -> dict[str, object]:
        return {
            "format": "hubcontador.lora-job.v1",
            "organization_id": str(uuid4()),
            "corpus_version": "corpus-123",
            "manifest_sha256": manifest_hash,
            "example_count": 1,
            "base_model": "qwen3-14b",
            "adapter_name": "contabil-v1",
            "chat_template": "qwen3",
            "method": "qlora",
            "training": {
                "max_seq_length": 4096,
                "epochs": 3,
                "learning_rate": 0.0001,
                "quantization": "4bit-nf4",
            },
        }

    def manifest_line(self) -> dict[str, object]:
        return {
            "id": str(uuid4()),
            "category": "risk",
            "question": "Quais pendências precisam de revisão?",
            "expected_answer": "Revise as pendências e cite o procedimento aprovado.",
            "source_references": ["Procedimento de fechamento § 2"],
            "scenario_hash": "a" * 64,
        }

    def test_runner_prepares_isolated_llamafactory_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.jsonl"
            manifest_path.write_text(
                json.dumps(self.manifest_line(), ensure_ascii=False) + "\n", encoding="utf-8"
            )
            manifest = load_manifest(manifest_path)
            job_path = root / "job.json"
            job_path.write_text(json.dumps(self.job(manifest_sha256(manifest))), encoding="utf-8")
            models_root = root / "models"
            (models_root / "qwen3-14b").mkdir(parents=True)

            config_path = prepare_workspace(
                job_spec=load_job_spec(job_path),
                manifest=manifest,
                workspace=root / "workspace",
                models_root=models_root,
            )

            self.assertIn("quantization_bit: 4", config_path.read_text(encoding="utf-8"))
            dataset = (root / "workspace" / "data" / "training.jsonl").read_text(encoding="utf-8")
            self.assertIn("Fontes aprovadas", dataset)
            self.assertNotIn("scenario_hash", dataset)

    def test_runner_rejects_stale_corpus_and_personal_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stale_job = root / "stale-job.json"
            stale_job.write_text(json.dumps(self.job("b" * 64)), encoding="utf-8")
            manifest_path = root / "manifest.jsonl"
            manifest_path.write_text(json.dumps(self.manifest_line()) + "\n", encoding="utf-8")
            manifest = load_manifest(manifest_path)
            with self.assertRaisesRegex(TrainingRunnerError, "hash"):
                prepare_workspace(
                    job_spec=load_job_spec(stale_job),
                    manifest=manifest,
                    workspace=root / "workspace",
                    models_root=root / "models",
                )

            personal = self.manifest_line()
            personal["question"] = "Revisar CPF 123.456.789-09"
            manifest_path.write_text(json.dumps(personal) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(TrainingRunnerError, "identificador pessoal"):
                load_manifest(manifest_path)

    def test_runner_rejects_invalid_job_and_manifest_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            job_path.write_text("not-json", encoding="utf-8")
            with self.assertRaisesRegex(TrainingRunnerError, "Especificação"):
                load_job_spec(job_path)

            for field, value, message in (
                ("format", "wrong", "Formato"),
                ("manifest_sha256", "not-a-hash", "Hash"),
                ("example_count", 0, "Quantidade"),
                ("method", "full", "Apenas"),
                ("base_model", "../../remote", "base_model"),
                ("training", {}, "Parâmetros"),
            ):
                payload = self.job("a" * 64)
                payload[field] = value
                job_path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(TrainingRunnerError, message):
                    load_job_spec(job_path)

            manifest_path = root / "manifest.jsonl"
            manifest_path.write_text("{bad}\n", encoding="utf-8")
            with self.assertRaisesRegex(TrainingRunnerError, "JSON"):
                load_manifest(manifest_path)
            manifest_path.write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(TrainingRunnerError, "exemplo"):
                load_manifest(manifest_path)
            with self.assertRaisesRegex(TrainingRunnerError, "Não foi possível"):
                load_manifest(root / "missing.jsonl")

    def test_workspace_requires_mounted_model_and_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.jsonl"
            manifest_path.write_text(
                json.dumps(self.manifest_line(), ensure_ascii=False) + "\n", encoding="utf-8"
            )
            manifest = load_manifest(manifest_path)
            job_spec = self.job(manifest_sha256(manifest))
            with self.assertRaisesRegex(TrainingRunnerError, "Modelo base"):
                prepare_workspace(
                    job_spec=job_spec,
                    manifest=manifest,
                    workspace=root / "workspace",
                    models_root=root / "models",
                )
            models_root = root / "models"
            (models_root / "qwen3-14b").mkdir(parents=True)
            output = root / "workspace" / "output"
            output.mkdir(parents=True)
            (output / "old-adapter.bin").write_text("do-not-overwrite", encoding="utf-8")
            with self.assertRaisesRegex(TrainingRunnerError, "já existe"):
                prepare_workspace(
                    job_spec=job_spec,
                    manifest=manifest,
                    workspace=root / "workspace",
                    models_root=models_root,
                )

    def test_local_cli_is_explicit_and_main_supports_dry_run(self) -> None:
        with (
            patch("runtime.trainer.runner.shutil.which", return_value=None),
            self.assertRaisesRegex(TrainingRunnerError, "LlamaFactory"),
        ):
            run_training(config_path=Path("train.yaml"), workspace=Path("."))
        with (
            patch("runtime.trainer.runner.shutil.which", return_value="/usr/bin/llamafactory-cli"),
            patch("runtime.trainer.runner.subprocess.run") as run,
        ):
            run_training(config_path=Path("train.yaml"), workspace=Path("."))
        self.assertEqual(run.call_args.args[0], ["llamafactory-cli", "train", "train.yaml"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.jsonl"
            manifest_path.write_text(json.dumps(self.manifest_line()) + "\n", encoding="utf-8")
            manifest = load_manifest(manifest_path)
            job_path = root / "job.json"
            job_path.write_text(json.dumps(self.job(manifest_sha256(manifest))), encoding="utf-8")
            models_root = root / "models"
            (models_root / "qwen3-14b").mkdir(parents=True)
            arguments = [
                "runner.py",
                "--job",
                str(job_path),
                "--manifest",
                str(manifest_path),
                "--workspace",
                str(root / "workspace"),
                "--models-root",
                str(models_root),
            ]
            with patch.object(sys, "argv", arguments):
                main()

            self.assertTrue((root / "workspace" / "train.yaml").exists())
