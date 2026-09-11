from __future__ import annotations


class IntegraError(Exception):
    """Anything that stopped an Integra Contador call from producing an answer."""


class IntegraConfigurationError(IntegraError):
    """Credentials or the certificate are missing or unusable."""


class IntegraAuthenticationError(IntegraError):
    """The store refused the certificate or the consumer key pair."""


class IntegraTransportError(IntegraError):
    """The gateway could not be reached, or answered something unreadable."""


class IntegraServiceError(IntegraError):
    """The gateway answered, and the answer is a refusal from the service itself."""

    def __init__(self, message: str, *, status: int, code: str = "", payload: object = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.payload = payload


class IntegraNotAuthorized(IntegraServiceError):
    """Usually a missing or expired electronic power of attorney for this contributor."""
