"""Storage boundary for binary material handled by Triagem.

The application always streams a triage file through an authorised view.  A file
field must therefore never manufacture a public URL, even in local development.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import Storage, default_storage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateTriageStorage(Storage):
    """Delegate persistence to the configured backend but deliberately deny URLs."""

    def _open(self, name: str, mode: str = "rb") -> File[Any]:
        return default_storage.open(name, mode)

    def _save(self, name: str, content: File[Any]) -> str:
        return default_storage.save(name, content)

    def exists(self, name: str) -> bool:
        return default_storage.exists(name)

    def delete(self, name: str) -> None:
        default_storage.delete(name)

    def size(self, name: str) -> int:
        return default_storage.size(name)

    def url(self, name: str | None) -> str:
        raise SuspiciousFileOperation("Arquivos da Triagem não têm URL pública.")
