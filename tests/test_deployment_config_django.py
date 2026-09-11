from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigurationTests(SimpleTestCase):
    def test_cobalchini_workflow_is_digest_pinned_signed_and_health_gated(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "deploy-cobalchini.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("EXPECTED_IMAGE_REPOSITORY", workflow)
        self.assertIn("COSIGN_PUBLIC_KEY_B64", workflow)
        self.assertIn("cosign verify --key", workflow)
        self.assertIn(
            "docker compose --env-file $env:COBALCHINI_ENV_FILE "
            "-f compose.cobalchini.yml config --quiet",
            workflow,
        )
        self.assertIn("--profile deploy run --rm migrate", workflow)
        self.assertIn("/api/v1/health/ready/", workflow)
        self.assertIn("PREVIOUS_HUB_IMAGE", workflow)
        self.assertIn("$failedImage = $env:HUB_IMAGE", workflow)
        self.assertIn(
            "acknowledge_control_release --release $failedImage --outcome rolled_back", workflow
        )
        self.assertIn("COBALCHINI_ENV_FILE", workflow)
        self.assertNotIn("--env-file .env.cobalchini", workflow)
        self.assertIn("docker logout ghcr.io", workflow)

        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("docker build --tag saas-backend:test .", ci)
        self.assertIn(
            "docker build --file runtime/multimodal/Dockerfile --tag hubcontador-multimodal:test .",
            ci,
        )

    def test_cobalchini_compose_keeps_odbc_outside_containers_and_uses_immutable_image_variable(
        self,
    ) -> None:
        compose = (ROOT / "compose.cobalchini.yml").read_text(encoding="utf-8")

        self.assertIn("${HUB_IMAGE:?", compose)
        self.assertNotIn("pyodbc", compose.casefold())
        self.assertNotIn("DSN=", compose)
        self.assertIn("health/ready/", compose)
        self.assertIn('profiles: ["deploy"]', compose)

    def test_optional_multimodal_stack_stays_private_and_requires_a_pinned_ollama_image(
        self,
    ) -> None:
        compose = (ROOT / "compose.cobalchini.yml").read_text(encoding="utf-8")
        adapter = (ROOT / "runtime" / "multimodal" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('profiles: ["ai"]', compose)
        self.assertIn("${OLLAMA_IMAGE:?Defina o digest imutável e aprovado do Ollama}", compose)
        self.assertNotIn("sha256:000000", compose)
        self.assertIn("LOCAL_MULTIMODAL_MODEL", compose)
        self.assertNotIn("8081:8081", compose)
        self.assertIn("poppler-utils", adapter)
        self.assertIn("Pillow==12.3.0", adapter)
        self.assertIn("USER 10001:10001", adapter)
        self.assertIn('CMD ["python", "multimodal.py"]', adapter)
        self.assertNotIn("fastapi", adapter.casefold())
        self.assertNotIn("uvicorn", adapter.casefold())

    def test_training_runtime_requires_an_operator_pinned_llamafactory_image(self) -> None:
        trainer = (ROOT / "runtime" / "trainer" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("ARG LLAMAFACTORY_IMAGE", trainer)
        self.assertIn("FROM ${LLAMAFACTORY_IMAGE}", trainer)
        self.assertIn("LLAMAFACTORY_IMAGE precisa usar digest", trainer)
        self.assertIn('ENTRYPOINT ["python", "/opt/hubcontador/runner.py"]', trainer)
        self.assertNotIn("EXPOSE", trainer)

    def test_fly_release_command_and_readiness_check_remain_declared(self) -> None:
        fly = (ROOT / "fly.toml").read_text(encoding="utf-8")

        self.assertIn('release_command = "python manage.py migrate --noinput"', fly)
        self.assertIn('path = "/api/v1/health/ready/"', fly)
        self.assertIn('strategy = "canary"', fly)
        self.assertIn('wait_timeout = "10m"', fly)

    def test_edge_agent_mtls_proxy_keeps_the_web_service_private(self) -> None:
        compose = (ROOT / "compose.cobalchini.yml").read_text(encoding="utf-8")
        proxy = (ROOT / "deploy" / "nginx" / "edge-agent-mtls.conf").read_text(encoding="utf-8")
        production = (ROOT / "src" / "config" / "settings" / "production.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"127.0.0.1:8000:8000"', compose)
        self.assertIn("ssl_client_certificate", proxy)
        self.assertIn("$ssl_client_verify != SUCCESS", proxy)
        self.assertIn("$ssl_client_escaped_cert", proxy)
        self.assertIn("EDGE_AGENT_MTLS_REQUIRED", production)

    def test_production_refuses_a_database_link_without_a_verified_tls_mode(self) -> None:
        """libpq falls back to "prefer" - refusing only sslmode=disable leaves a plaintext gap."""

        production = (ROOT / "src" / "config" / "settings" / "production.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('SECURE_DB_SSL_MODES = {"require", "verify-ca", "verify-full"}', production)
        self.assertIn('for alias in ("default", "knowledge"):', production)
        self.assertIn("DB_TLS_ENFORCED_BY_NETWORK", production)

        fly = (ROOT / "fly.toml").read_text(encoding="utf-8")
        self.assertIn('DB_SSL_REQUIRE = "true"', fly)
