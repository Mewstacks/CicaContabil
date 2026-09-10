from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptedQueue:
    """Small crash-safe queue; its key is supplied by OS secret storage, never this file."""

    def __init__(self, path: Path, secret: str) -> None:
        self.path = path
        self.key = hashlib.sha256(secret.encode()).digest()

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = base64.urlsafe_b64decode(self.path.read_bytes())
        nonce, ciphertext = raw[:12], raw[12:]
        return json.loads(AESGCM(self.key).decrypt(nonce, ciphertext, None))

    def _write(self, items: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        nonce = os.urandom(12)
        ciphertext = AESGCM(self.key).encrypt(nonce, json.dumps(items).encode(), None)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(base64.urlsafe_b64encode(nonce + ciphertext))
        temporary.replace(self.path)

    def push(self, payload: dict[str, Any]) -> str:
        items = self._read()
        item_id = str(uuid.uuid4())
        items.append({"id": item_id, "payload": payload})
        self._write(items)
        return item_id

    def first(self) -> dict[str, Any] | None:
        items = self._read()
        return items[0] if items else None

    def acknowledge(self, item_id: str) -> None:
        self._write([item for item in self._read() if item["id"] != item_id])
