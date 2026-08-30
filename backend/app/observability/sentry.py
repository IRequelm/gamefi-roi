"""Optional Sentry integration for production error monitoring."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app import __version__
from app.config.settings import Settings

logger = logging.getLogger(__name__)

_DENY_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "key",
    "credential",
    "wallet",
    "private",
    "signature",
)
_initialized_key: tuple[str, str | None] | None = None


def initialize_sentry(settings: Settings) -> bool:
    """Initialize Sentry if a DSN is configured; otherwise remain inert."""
    global _initialized_key
    if not settings.sentry_dsn:
        return False

    release = release_identifier(settings)
    current_key = (settings.sentry_dsn, release)
    if _initialized_key == current_key:
        return True

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError as exc:
        logger.error("sentry_sdk_unavailable", extra={"error": str(exc)})
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.environment,
        release=release,
        send_default_pii=False,
        sample_rate=settings.sentry_error_sample_rate,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        max_request_body_size="never",
        include_local_variables=False,
        attach_stacktrace=True,
        before_send=sanitize_sentry_event,
        integrations=[
            StarletteIntegration(failed_request_status_codes=set(range(500, 600))),
            FastApiIntegration(failed_request_status_codes=set(range(500, 600))),
        ],
    )
    _initialized_key = current_key
    logger.info(
        "sentry_initialized",
        extra={
            "environment": settings.sentry_environment or settings.environment,
            "release": release,
            "traces_sample_rate": settings.sentry_traces_sample_rate,
        },
    )
    return True


def release_identifier(settings: Settings) -> str:
    configured = settings.sentry_release
    if configured:
        return configured
    for key in ("RENDER_GIT_COMMIT", "GITHUB_SHA"):
        value = os.environ.get(key)
        if value:
            return value[:200]
    return f"gamefi-roi@{__version__}"


def sanitize_sentry_event(event: dict[str, Any], hint: object | None = None) -> dict[str, Any] | None:
    """Remove sensitive request/user fields before Sentry receives an event."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("query_string", None)
        request.pop("env", None)
        if isinstance(request.get("headers"), Mapping):
            request["headers"] = _scrub_mapping(request["headers"])
        if isinstance(request.get("url"), str):
            request["url"] = _strip_query_and_fragment(request["url"])

    user = event.get("user")
    if isinstance(user, dict):
        for key in ("email", "username", "ip_address"):
            user.pop(key, None)
        if not user:
            event.pop("user", None)

    for key in ("extra", "contexts", "tags"):
        value = event.get(key)
        if isinstance(value, dict):
            event[key] = _scrub_mapping(value)
    return event


def _scrub_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in values.items():
        key_text = str(key)
        lowered = key_text.lower().replace("-", "_")
        if any(part in lowered for part in _DENY_KEY_PARTS):
            scrubbed[key_text] = "[Filtered]"
        elif isinstance(value, Mapping):
            scrubbed[key_text] = _scrub_mapping(value)
        elif isinstance(value, (list, tuple)):
            scrubbed[key_text] = ["[Filtered]" if _looks_sensitive(item) else item for item in value[:20]]
        else:
            scrubbed[key_text] = value
    return scrubbed


def _looks_sensitive(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(part in lowered for part in _DENY_KEY_PARTS)


def _strip_query_and_fragment(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def reset_sentry_for_tests() -> None:
    global _initialized_key
    _initialized_key = None
