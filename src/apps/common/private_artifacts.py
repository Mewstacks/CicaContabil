"""Exclusive private JSON review files, without overwriting an existing artifact."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_private_json(path: str, payload: Any) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode()
    if len(content) > 2_000_000:
        raise ValueError("Arquivo de revisão excede o limite de 2 MB.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
