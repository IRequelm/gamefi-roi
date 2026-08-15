"""Structured source connector errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceErrorDetail:
    provider: str
    operation: str
    message: str
    retryable: bool = False
    status_code: int | None = None


class SourceError(Exception):
    def __init__(self, detail: SourceErrorDetail) -> None:
        super().__init__(detail.message)
        self.detail = detail


class SourceRequestError(SourceError):
    """Raised when provider transport or status handling fails."""


class SourceParseError(SourceError):
    """Raised when provider payloads do not match the expected contract."""


class UnsupportedSourceCapability(SourceError):
    """Raised when a provider does not implement a requested source capability."""
