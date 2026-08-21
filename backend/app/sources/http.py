"""HTTP helpers for external source connectors."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from app.sources.errors import SourceErrorDetail, SourceParseError, SourceRequestError

logger = logging.getLogger(__name__)


class SourceHttpClient:
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")

        self.provider = provider
        self.base_url = base_url.rstrip("/") + "/"
        self.max_retries = max_retries
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        attempts = self.max_retries + 1
        last_error: SourceRequestError | None = None

        for attempt in range(attempts):
            try:
                response = self._client.get(path, params=params, headers=headers)
            except httpx.HTTPError as exc:
                last_error = SourceRequestError(
                    SourceErrorDetail(
                        provider=self.provider,
                        operation=operation,
                        message=f"HTTP request failed: {exc}",
                        retryable=attempt < attempts - 1,
                    )
                )
            else:
                if response.status_code < 400:
                    return self._decode_json(response, operation)

                last_error = SourceRequestError(
                    SourceErrorDetail(
                        provider=self.provider,
                        operation=operation,
                        message=f"Provider returned HTTP {response.status_code}",
                        retryable=response.status_code >= 500 and attempt < attempts - 1,
                        status_code=response.status_code,
                    )
                )
                if response.status_code < 500:
                    _log_failure(last_error)
                    raise last_error

            if attempt < attempts - 1:
                _log_retry(last_error, attempt=attempt, attempts=attempts)
                time.sleep(_retry_sleep_seconds(attempt))

        if last_error is not None:
            _log_failure(last_error)
            raise last_error

        raise SourceRequestError(
            SourceErrorDetail(
                provider=self.provider,
                operation=operation,
                message="HTTP request failed before a response was available",
                retryable=False,
            )
        )

    def source_locator(self, path: str, params: Mapping[str, str]) -> str:
        query = urlencode(sorted(params.items()))
        joined = urljoin(self.base_url, path.lstrip("/"))
        return f"{joined}?{query}" if query else joined

    def _decode_json(self, response: httpx.Response, operation: str) -> dict[str, Any]:
        try:
            payload = json.loads(response.text, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider,
                    operation=operation,
                    message=f"Provider returned invalid JSON: {exc}",
                    retryable=False,
                    status_code=response.status_code,
                )
            ) from exc

        if not isinstance(payload, dict):
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider,
                    operation=operation,
                    message="Provider JSON payload must be an object",
                    retryable=False,
                    status_code=response.status_code,
                )
            )

        return payload

    def post_json(
        self,
        path: str,
        *,
        json_payload: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        attempts = self.max_retries + 1
        last_error: SourceRequestError | None = None

        for attempt in range(attempts):
            try:
                response = self._client.post(path, json=json_payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = SourceRequestError(
                    SourceErrorDetail(
                        provider=self.provider,
                        operation=operation,
                        message=f"HTTP request failed: {exc}",
                        retryable=attempt < attempts - 1,
                    )
                )
            else:
                if response.status_code < 400:
                    return self._decode_json(response, operation)

                last_error = SourceRequestError(
                    SourceErrorDetail(
                        provider=self.provider,
                        operation=operation,
                        message=f"Provider returned HTTP {response.status_code}",
                        retryable=response.status_code >= 500 and attempt < attempts - 1,
                        status_code=response.status_code,
                    )
                )
                if response.status_code < 500:
                    _log_failure(last_error)
                    raise last_error

            if attempt < attempts - 1:
                _log_retry(last_error, attempt=attempt, attempts=attempts)
                time.sleep(_retry_sleep_seconds(attempt))

        if last_error is not None:
            _log_failure(last_error)
            raise last_error

        raise SourceRequestError(
            SourceErrorDetail(
                provider=self.provider,
                operation=operation,
                message="HTTP request failed before a response was available",
                retryable=False,
            )
        )


def _retry_sleep_seconds(attempt: int) -> float:
    return min(0.25 * (2**attempt), 2.0)


def _log_retry(error: SourceRequestError | None, *, attempt: int, attempts: int) -> None:
    if error is None:
        return
    detail = error.detail
    logger.warning(
        "provider_retry provider=%s operation=%s attempt=%s/%s status_code=%s retryable=%s message=%s",
        detail.provider,
        detail.operation,
        attempt + 1,
        attempts,
        detail.status_code,
        detail.retryable,
        detail.message,
    )


def _log_failure(error: SourceRequestError) -> None:
    detail = error.detail
    logger.error(
        "provider_failure provider=%s operation=%s status_code=%s retryable=%s message=%s",
        detail.provider,
        detail.operation,
        detail.status_code,
        detail.retryable,
        detail.message,
    )
