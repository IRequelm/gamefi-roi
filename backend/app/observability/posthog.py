"""Best-effort PostHog product analytics capture."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from app import __version__
from app.config.settings import Settings
from app.observability.sentry import release_identifier

logger = logging.getLogger(__name__)

POSTHOG_ALLOWED_EVENTS = frozenset(
    {
        "opportunity_view",
        "strategy_view",
        "ranking_view",
        "opportunity_to_strategy_click",
        "ranking_to_strategy_click",
        "internal_compare_or_next_click",
        "outbound_go_click",
        "referral_outbound_click",
        "official_fallback_outbound_click",
        "opportunity_search_used",
        "ranking_filter_used",
    }
)
POSTHOG_ALLOWED_PROPERTIES = frozenset(
    {
        "opportunity_slug",
        "opportunity_id",
        "opportunity_type",
        "strategy_slug",
        "strategy_id",
        "ranking_slug",
        "destination_slug",
        "target_url_kind",
        "referral_status",
        "commercial_relationship",
        "is_affiliate",
        "placement",
        "source_page",
        "page_path",
        "snapshot_id",
        "snapshot_timestamp",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "environment",
        "release",
        "app_version",
        "event_origin",
        "traffic_class",
    }
)
_MAX_TEXT_LENGTH = 160


def track_product_event(
    settings: Settings,
    *,
    event_name: str,
    distinct_id: str,
    properties: Mapping[str, Any] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Submit a PostHog event without allowing analytics failures to break callers."""
    if not settings.posthog_project_api_key or event_name not in POSTHOG_ALLOWED_EVENTS:
        return False
    safe_distinct_id = _clean_distinct_id(distinct_id)
    if not safe_distinct_id:
        return False

    safe_properties = _safe_properties(properties or {}, settings)
    payload = {
        "api_key": settings.posthog_project_api_key,
        "event": event_name,
        "distinct_id": safe_distinct_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "properties": safe_properties,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.posthog_timeout_seconds), transport=transport) as client:
            response = client.post(f"{settings.posthog_host}/capture/", json=payload)
            if response.status_code >= 400:
                logger.warning(
                    "posthog_capture_failed",
                    extra={"event_name": event_name, "status_code": response.status_code},
                )
                return False
    except Exception as exc:
        logger.warning("posthog_capture_error", extra={"event_name": event_name, "error": str(exc)})
        return False
    return True


def _safe_properties(values: Mapping[str, Any], settings: Settings) -> dict[str, Any]:
    safe: dict[str, Any] = {
        "environment": settings.sentry_environment or settings.environment,
        "release": release_identifier(settings),
        "app_version": __version__,
        "$process_person_profile": False,
    }
    for key, value in values.items():
        if key not in POSTHOG_ALLOWED_PROPERTIES:
            continue
        cleaned = _clean_property_value(value)
        if cleaned is not None:
            safe[key] = cleaned
    return safe


def _clean_property_value(value: Any) -> str | int | float | bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    text = str(value).strip()
    if not text:
        return None
    return text[:_MAX_TEXT_LENGTH]


def _clean_distinct_id(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:128]


def distinct_id_for_outbound_click(coarse_session_id: str | None, click_event_id: str | None = None) -> str:
    if coarse_session_id and coarse_session_id.strip():
        return coarse_session_id.strip()[:128]
    if click_event_id and click_event_id.strip():
        return f"outbound:{click_event_id.strip()}"[:128]
    return f"outbound:{uuid4()}"
