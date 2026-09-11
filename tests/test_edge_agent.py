from __future__ import annotations

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from agent.local_queue import EncryptedQueue
from agent.runner import AgentRuntimeConfig, synchronize_once
from agent.sync_client import EdgeAgentConfig, enroll_agent
from agent.windows_service import decode_service_environment

from apps.intelligence.connectors import ReadOnlyDominoOdbc


class EdgeAgentLocalTests(TestCase):
    def test_service_configuration_accepts_only_a_validated_environment(self) -> None:
        environment = {
            "HUB_AGENT_DSN": "Dominio64",
            "HUB_AGENT_HUB_URL": "https://hub.example.test",
            "HUB_AGENT_ID": "agent-1",
            "HUB_AGENT_SHARED_SECRET": "device-secret",
            "HUB_AGENT_CA_FILE": "ca.pem",
            "HUB_AGENT_CERTIFICATE_FILE": "client.pem",
            "HUB_AGENT_PRIVATE_KEY_FILE": "client.key",
        }
        protected = base64.b64encode(json.dumps(environment).encode())

        self.assertEqual(
            decode_service_environment(protected, unprotect=lambda value: value), environment
        )

    def test_service_configuration_rejects_invalid_or_unknown_documents(self) -> None:
        with self.assertRaisesRegex(ValueError, "Configuração protegida"):
            decode_service_environment(b"not-base64", unprotect=lambda value: value)

        protected = base64.b64encode(b'{"HUB_AGENT_DSN":"Dominio64","unexpected":"value"}')
        with self.assertRaisesRegex(ValueError, "Configuração protegida"):
            decode_service_environment(protected, unprotect=lambda value: value)

    def test_encrypted_queue_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            queue = EncryptedQueue(Path(directory) / "queue.bin", "device-secret")
            item_id = queue.push({"companies": [{"codigo": "001"}]})

            self.assertEqual(
                queue.first(), {"id": item_id, "payload": {"companies": [{"codigo": "001"}]}}
            )
            self.assertNotIn("001", (Path(directory) / "queue.bin").read_text(errors="ignore"))
            queue.acknowledge(item_id)
            self.assertIsNone(queue.first())

    def test_edge_agent_rejects_plain_http(self) -> None:
        config = EdgeAgentConfig("http://hub.local", "agent", "secret")

        with self.assertRaises(ValueError):
            config.sync_url()

    def test_edge_agent_requires_client_certificate_material(self) -> None:
        config = EdgeAgentConfig("https://hub.local", "agent", "secret")

        with self.assertRaises(ValueError):
            config.mtls_context()

    @patch("agent.sync_client.urlopen")
    @patch.object(EdgeAgentConfig, "mtls_context", return_value=object())
    @patch.object(EdgeAgentConfig, "enrollment_identity")
    def test_enrollment_posts_only_the_one_time_identity(
        self, mocked_identity, _mocked_context, mocked_urlopen
    ) -> None:
        mocked_identity.return_value = {
            "code": "one-time",
            "label": "Servidor",
            "fingerprint": "fp",
        }
        response = mocked_urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"agent_id":"agent-1","shared_secret":"device-secret"}'
        config = EdgeAgentConfig("https://hub.local", "", "", "ca.pem", "cert.pem", "key.pem")

        credentials = enroll_agent(config, code="one-time", label="Servidor", fingerprint="fp")

        self.assertEqual(credentials, ("agent-1", "device-secret"))
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://hub.local/api/v1/intelligence/agent/enroll/")
        self.assertNotIn("key.pem", request.data.decode())

    def test_odbc_adapter_rejects_unregistered_query(self) -> None:
        with self.assertRaises(ValueError):
            ReadOnlyDominoOdbc("Dominio64").execute("DROP TABLE")

    def test_runtime_requires_a_safe_system_dsn_and_mtls_material(self) -> None:
        values = {
            "HUB_AGENT_DSN": "Dominio64;UID=forbidden",
            "HUB_AGENT_HUB_URL": "https://hub.example.test",
            "HUB_AGENT_ID": "agent-1",
            "HUB_AGENT_SHARED_SECRET": "device-secret",
            "HUB_AGENT_CA_FILE": "ca.pem",
            "HUB_AGENT_CERTIFICATE_FILE": "client.pem",
            "HUB_AGENT_PRIVATE_KEY_FILE": "client.key",
        }

        with self.assertRaises(ValueError):
            AgentRuntimeConfig.from_environment(values)

    @patch("agent.runner.post_snapshot")
    def test_runtime_replays_the_encrypted_queue_before_reading_odbc(self, mocked_post) -> None:
        runtime = AgentRuntimeConfig(
            dsn="Dominio64",
            sync=EdgeAgentConfig(
                "https://hub.example.test",
                "agent-1",
                "device-secret",
                "ca.pem",
                "client.pem",
                "client.key",
            ),
            queue_path=Path("unused"),
        )
        with TemporaryDirectory() as directory:
            queue = EncryptedQueue(Path(directory) / "queue.bin", "device-secret")
            queue.push({"companies": [{"dominio_code": "001", "cnpj_masked": "00.***"}]})

            outcome = synchronize_once(
                runtime=runtime,
                queue=queue,
                connection_factory=lambda _dsn: self.fail("ODBC não deve ser lido antes do replay"),
            )

        self.assertEqual(outcome.status, "replayed")
        self.assertEqual(outcome.company_count, 1)
        mocked_post.assert_called_once()

    @patch("agent.runner.post_snapshot")
    def test_runtime_reads_only_the_constant_company_query_then_acknowledges(
        self, mocked_post
    ) -> None:
        class Cursor:
            def execute(self, query: str) -> Cursor:
                self.query = query
                return self

            def fetchall(self) -> list[tuple[object, ...]]:
                return [("001", "Empresa", "12345678000199")]

        class Connection:
            closed = False

            def __init__(self) -> None:
                self.cursor_value = Cursor()

            def cursor(self) -> Cursor:
                return self.cursor_value

            def close(self) -> None:
                self.closed = True

        runtime = AgentRuntimeConfig(
            dsn="Dominio64",
            sync=EdgeAgentConfig(
                "https://hub.example.test",
                "agent-1",
                "device-secret",
                "ca.pem",
                "client.pem",
                "client.key",
            ),
            queue_path=Path("unused"),
        )
        connection = Connection()
        with TemporaryDirectory() as directory:
            queue = EncryptedQueue(Path(directory) / "queue.bin", "device-secret")
            outcome = synchronize_once(
                runtime=runtime,
                queue=queue,
                connection_factory=lambda _dsn: connection,
            )

            self.assertIsNone(queue.first())
        self.assertEqual(outcome.status, "synchronized")
        self.assertEqual(outcome.company_count, 1)
        self.assertTrue(connection.closed)
        self.assertIn("SELECT TOP 500 codi_emp AS codigo", connection.cursor_value.query)
        sent = mocked_post.call_args.args[1]
        self.assertEqual(sent["companies"][0]["cnpj_masked"], "12.***.***/0001-**")
        self.assertFalse(sent["full_snapshot"])
