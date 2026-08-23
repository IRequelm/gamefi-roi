"""IndexNow submission support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

import httpx
from sqlalchemy import Engine

from app.config.settings import Settings
from app.search.canonical import canonical_page_inventory, is_canonical_public_url

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

logger = logging.getLogger(__name__)


class IndexNowError(RuntimeError):
    """Raised when IndexNow submission cannot be attempted safely."""


@dataclass(frozen=True)
class IndexNowSubmitResult:
    submitted_urls: tuple[str, ...]
    status_code: int


class IndexNowClient:
    def __init__(
        self,
        *,
        settings: Settings,
        engine: Engine,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.settings = settings
        self.engine = engine
        self.transport = transport
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def submit_urls(self, urls: Iterable[str]) -> IndexNowSubmitResult:
        key = self.settings.indexnow_key
        if not key:
            raise IndexNowError("GAMEFI_INDEXNOW_KEY is required to submit IndexNow URLs")

        public_paths = {page.path for page in canonical_page_inventory(self.engine)}
        valid_urls = tuple(
            dict.fromkeys(
                url for url in urls if is_canonical_public_url(url, settings=self.settings, public_paths=public_paths)
            )
        )
        if not valid_urls:
            raise IndexNowError("No canonical public URLs were eligible for IndexNow submission")

        payload = {
            "host": urlsplit(self.settings.public_base_url).netloc,
            "key": key,
            "urlList": list(valid_urls),
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(transport=self.transport, timeout=self.timeout_seconds) as client:
                    response = client.post(INDEXNOW_ENDPOINT, json=payload)
                if response.status_code < 400:
                    logger.info("indexnow_submit_success", extra={"url_count": len(valid_urls)})
                    return IndexNowSubmitResult(submitted_urls=valid_urls, status_code=response.status_code)
                last_error = IndexNowError(f"IndexNow returned HTTP {response.status_code}")
            except (httpx.HTTPError, IndexNowError) as exc:
                last_error = exc
            logger.warning(
                "indexnow_submit_failed",
                extra={"attempt": attempt + 1, "url_count": len(valid_urls), "error": _redact_secret(str(last_error), key)},
            )

        raise IndexNowError(_redact_secret(str(last_error or "IndexNow submission failed"), key))

    def submit_all_canonical_urls(self) -> IndexNowSubmitResult:
        return self.submit_urls(page.absolute_url(self.settings) for page in canonical_page_inventory(self.engine))


def _redact_secret(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value
