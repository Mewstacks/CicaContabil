"""The typed side of the registry: how to build the `dados` of a service and read its answer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from apps.integra.catalog import service
from apps.integra.typed.base import Request


@dataclass(frozen=True)
class TypedService:
    """One registry service with its request model (None when `dados` stays empty) and reader.

    `read` takes the answer of the gateway (what `IntegraClient.call` returns) and returns a
    typed result; it raises IntegraPayloadError when the answer breaks the documented contract.
    """

    key: str
    request: type[Request] | None
    read: Callable[[Mapping[str, Any]], Any]

    def __post_init__(self) -> None:
        service(self.key)  # refuses a key that is not in the registry
