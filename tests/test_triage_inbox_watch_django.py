from __future__ import annotations

import hashlib
import hmac
import json
import socket
import threading
import time
from urllib.parse import quote

import pytest
from django.test import Client, override_settings

from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.triage.inbox import inbox_path_error
from apps.triage.models import DestinationProfile, TriageItem, TriagePolicy
from apps.triage.security import ClamdScanner, ScannerUnavailable, scanner_status
from apps.triage.transitions import TriageStatus

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\ninbox file\n%%EOF"


def _signed(agent: EdgeAgent, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    signature = hmac.new(
        agent.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return {
        "X-Hub-Agent-ID": str(agent.id),
        "X-Hub-Agent-Timestamp": timestamp,
        "X-Hub-Agent-Signature": signature,
    }


def _upload(agent: EdgeAgent, body: bytes, *, name: str = "guia.pdf", sha: str | None = None):
    headers = _signed(agent, body)
    headers["X-Inbox-Filename"] = quote(name)
    headers["X-Inbox-Sha256"] = sha if sha is not None else hashlib.sha256(body).hexdigest()
    return Client().generic(
        "POST",
        "/api/agent/v2/inbox/upload",
        body,
        content_type="application/octet-stream",
        headers=headers,
        secure=True,
    )


def _config(agent: EdgeAgent) -> dict[str, object]:
    body = b"{}"
    response = Client().generic(
        "POST",
        "/api/agent/v2/configuration/next",
        body,
        content_type="application/json",
        headers=_signed(agent, body),
        secure=True,
    )
    assert response.status_code == 200
    return json.loads(response.content)["inbox_watch"]


@pytest.fixture
def office_agent(tmp_path):
    with override_settings(
        EDGE_AGENT_MTLS_REQUIRED=False,
        MEDIA_ROOT=tmp_path,
        TRIAGE_CLAMD_SOCKET="",
        TRIAGE_CLAMD_PORT=0,
    ):
        office = Organization.objects.create(name="Escritório", slug="inbox-watch", is_demo=True)
        agent = EdgeAgent.objects.create(
            organization=office, label="Servidor", fingerprint="fp", shared_secret="secret-tests"
        )
        yield office, agent


def _enable(office: Organization, **extra: object) -> None:
    DestinationProfile.objects.update_or_create(
        organization=office,
        defaults={"mode": DestinationProfile.Mode.WINDOWS, "windows_root": r"D:\Clientes"},
    )
    TriagePolicy.objects.update_or_create(
        organization=office,
        defaults={
            "inbox_watch_enabled": True,
            "inbox_watch_path": r"D:\Clientes\Entrada",
            **extra,
        },
    )


def test_config_is_off_by_default_and_reports_the_office_folder(office_agent) -> None:
    office, agent = office_agent
    assert _config(agent)["enabled"] is False
    _enable(office, inbox_stable_seconds=45)
    config = _config(agent)
    assert config["enabled"] is True
    assert config["path"] == r"D:\Clientes\Entrada"
    assert config["stable_seconds"] == 45


def test_upload_is_refused_while_the_flag_is_off(office_agent) -> None:
    _office, agent = office_agent
    response = _upload(agent, PDF)
    assert response.status_code == 422
    assert TriageItem.objects.count() == 0


def test_upload_quarantines_and_the_same_bytes_are_idempotent(office_agent) -> None:
    office, agent = office_agent
    _enable(office)
    first = _upload(agent, PDF)
    assert first.status_code == 200
    assert json.loads(first.content)["status"] == "received"
    item = TriageItem.objects.get()
    assert item.status == TriageStatus.QUARANTINED
    assert item.content_hash == hashlib.sha256(PDF).hexdigest()
    again = _upload(agent, PDF)
    assert json.loads(again.content)["status"] == "duplicate"
    assert TriageItem.objects.count() == 1


def test_wrong_hash_unsupported_format_and_size_limit_are_refused(office_agent) -> None:
    office, agent = office_agent
    _enable(office)
    assert _upload(agent, PDF, sha="0" * 64).status_code == 422
    assert _upload(agent, PDF, name="programa.exe").status_code == 422
    big = b"%PDF" + b"x" * (8 * 1024 * 1024)
    assert _upload(agent, big).status_code in {413, 422}
    assert TriageItem.objects.count() == 0


def test_unsigned_request_is_unauthorized(office_agent) -> None:
    office, _agent = office_agent
    _enable(office)
    response = Client().generic(
        "POST",
        "/api/agent/v2/inbox/upload",
        PDF,
        content_type="application/octet-stream",
        secure=True,
    )
    assert response.status_code == 401


def test_an_agent_only_writes_into_its_own_office(office_agent) -> None:
    office, agent = office_agent
    other = Organization.objects.create(name="Outro", slug="inbox-other", is_demo=True)
    _enable(other)
    # `office` never enabled the folder: the other office's flag must not leak.
    assert _upload(agent, PDF).status_code == 422
    assert TriageItem.objects.filter(organization=other).count() == 0
    assert office.pk != other.pk


# ---- ClamAV readiness -------------------------------------------------------------


class _FakeClamd:
    def __init__(self, replies: dict[bytes, bytes]) -> None:
        self.replies = replies
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(4)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                command = connection.recv(64)
                connection.sendall(self.replies.get(command, b"UNKNOWN COMMAND\0"))

    def close(self) -> None:
        self.server.close()


def test_clamd_ping_and_status_up() -> None:
    fake = _FakeClamd({b"zPING\0": b"PONG\0", b"zVERSION\0": b"ClamAV 1.4.2/27000\0"})
    try:
        scanner = ClamdScanner(loopback_port=fake.port)
        assert scanner.ping() is True
        assert scanner.version().startswith("ClamAV 1.4")
        with override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=fake.port):
            status = scanner_status()
        assert status.state == "up"
        assert "ClamAV" in status.detail
    finally:
        fake.close()


def test_clamd_without_pong_or_offline_is_down_and_unconfigured_is_off() -> None:
    fake = _FakeClamd({b"zPING\0": b"ERROR\0"})
    try:
        with override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=fake.port):
            assert scanner_status().state == "down"
    finally:
        fake.close()
    with override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=fake.port):
        assert scanner_status().state == "down"
        with pytest.raises(ScannerUnavailable):
            ClamdScanner(loopback_port=fake.port).ping()
    with override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=0):
        assert scanner_status().state == "off"


def test_watched_path_must_sit_strictly_under_the_office_root(office_agent) -> None:
    office, _agent = office_agent
    assert inbox_path_error(office, r"D:\Clientes\Entrada") == "Ative as pastas Windows antes."
    _enable(office)
    assert inbox_path_error(office, r"D:\Clientes\Entrada") is None
    assert inbox_path_error(office, r"d:\clientes\ENTRADA\sub") is None
    for bad in (
        r"D:\Clientes",
        r"D:\Outra",
        r"D:\Clientes\..\Windows",
        r"D:\ClientesX\Entrada",
        "Entrada",
        r"\\servidor\share\Entrada",
    ):
        assert inbox_path_error(office, bad) is not None, bad


def test_config_withholds_a_stored_path_outside_the_root(office_agent) -> None:
    office, agent = office_agent
    _enable(office)
    TriagePolicy.objects.filter(organization=office).update(inbox_watch_path=r"C:\Windows")
    assert _config(agent)["enabled"] is False
