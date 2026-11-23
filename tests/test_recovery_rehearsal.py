"""Safety boundaries of the local-only synthetic recovery runner."""

import subprocess
import sys

import pytest
from scripts import rehearse_contad_recovery as rehearsal


@pytest.mark.parametrize("endpoint", ["tcp://host:2375", "ssh://host", "npipe://docker"])
def test_remote_docker_host_is_rejected_before_contact(monkeypatch, endpoint):
    monkeypatch.setenv("DOCKER_HOST", endpoint)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setattr(rehearsal.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(rehearsal, "run", lambda *_a, **_k: pytest.fail("Remote contact"))
    with pytest.raises(RuntimeError, match="local Docker Unix socket"):
        rehearsal.local_docker_command()


def test_context_override_is_checked_instead_of_ignoring_it(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///local.sock")
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    monkeypatch.setattr(rehearsal.shutil, "which", lambda _: "/usr/bin/docker")
    commands = []

    def inspect(command):
        commands.append(command)
        return b"ssh://remote-host\n"

    monkeypatch.setattr(rehearsal, "run", inspect)
    with pytest.raises(RuntimeError, match="local Docker Unix socket"):
        rehearsal.local_docker_command()
    assert commands == [
        [
            "/usr/bin/docker",
            "context",
            "inspect",
            "remote-context",
            "--format",
            "{{.Endpoints.docker.Host}}",
        ]
    ]


def test_docker_command_cannot_inherit_remote_redirection(monkeypatch):
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    monkeypatch.setenv("DOCKER_HOST", "ssh://remote-host")
    observed = []

    def capture(command, **kwargs):
        observed.append(kwargs["env"])
        return b"ok"

    monkeypatch.setattr(rehearsal.subprocess, "check_output", capture)
    rehearsal.run(["/usr/bin/docker", "--host", "unix:///local.sock", "image", "ls"])
    assert not any(key.startswith("DOCKER_") for key in observed[0])


@pytest.mark.parametrize("existing", ["file", "dangling-symlink"])
def test_receipt_is_not_overwritten_or_symlink_followed(tmp_path, monkeypatch, existing):
    output = tmp_path / "receipt.json"
    target = tmp_path / "absent.json"
    if existing == "file":
        output.write_text("original")
    else:
        output.symlink_to(target)
    monkeypatch.setattr(rehearsal, "local_docker_command", lambda: pytest.fail("Docker contact"))
    with pytest.raises(FileExistsError):
        rehearsal.rehearse(output)
    assert not target.exists()
    assert (
        output.is_symlink() if existing == "dangling-symlink" else output.read_text() == "original"
    )


def test_optimized_python_is_rejected_before_any_work():
    result = subprocess.run(  # noqa: S603 -- current Python and repository script, fixed flags.
        [sys.executable, "-O", rehearsal.__file__, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "requires assertions" in result.stderr


def test_cleanup_is_limited_to_created_container_on_failure(tmp_path, monkeypatch):
    docker = ["/usr/bin/docker", "--host", "unix:///local.sock"]
    monkeypatch.setattr(rehearsal, "local_docker_command", lambda: docker)
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        action = command[3]
        if action == "image":
            return b"sha256:synthetic-image"
        if action == "run":
            return b"synthetic-container"
        if action == "port":
            raise RuntimeError("simulated port failure")
        assert action == "rm"
        return b"removed"

    monkeypatch.setattr(rehearsal, "run", execute)
    with pytest.raises(RuntimeError, match="simulated port failure"):
        rehearsal.rehearse(tmp_path / "receipt.json")
    created_command = next(command for command in calls if command[3] == "run")
    created_name = created_command[created_command.index("--name") + 1]
    assert created_name.startswith("cica-recovery-")
    assert calls[-1] == [*docker, "rm", "--force", "--volumes", created_name]
    assert not (tmp_path / "receipt.json").exists()
