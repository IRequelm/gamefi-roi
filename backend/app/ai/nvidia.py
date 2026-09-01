"""NVIDIA NIM text-generation client.

The client is intentionally isolated from ROI, ranking, risk, confidence, and
publishing. It provides a bounded, observable text-generation primitive that
higher-level Growth/Operations workflows can opt into explicitly.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

ChatRole = Literal["system", "user", "assistant"]
DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "openai/gpt-oss-120b"


class NvidiaNimConfigurationError(ValueError):
    """Raised when the NVIDIA NIM runtime configuration is unusable."""


class NvidiaNimRequestError(RuntimeError):
    """Raised when NVIDIA NIM cannot return a usable completion."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("chat message content must not be blank")

    def as_payload(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class NvidiaNimConfig:
    api_key: str = field(repr=False)
    base_url: str = DEFAULT_NVIDIA_BASE_URL
    model: str = DEFAULT_NVIDIA_MODEL
    timeout_seconds: float = 60.0
    max_retries: int = 2
    default_max_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise NvidiaNimConfigurationError("NVIDIA_API_KEY is required")
        if not self.model.strip():
            raise NvidiaNimConfigurationError("GAMEFI_NVIDIA_MODEL must not be blank")
        if not 0 < self.timeout_seconds <= 180:
            raise NvidiaNimConfigurationError(
                "GAMEFI_NVIDIA_TIMEOUT_SECONDS must be > 0 and <= 180"
            )
        if not 0 <= self.max_retries <= 5:
            raise NvidiaNimConfigurationError(
                "GAMEFI_NVIDIA_MAX_RETRIES must be between 0 and 5"
            )
        if not 1 <= self.default_max_tokens <= 16_384:
            raise NvidiaNimConfigurationError(
                "GAMEFI_NVIDIA_MAX_TOKENS must be between 1 and 16384"
            )

        normalized_base_url = self.base_url.strip().rstrip("/")
        parsed = urlsplit(normalized_base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise NvidiaNimConfigurationError(
                "GAMEFI_NVIDIA_BASE_URL must be an HTTPS URL with a host"
            )
        if parsed.query or parsed.fragment:
            raise NvidiaNimConfigurationError(
                "GAMEFI_NVIDIA_BASE_URL must not include query or fragment"
            )
        object.__setattr__(self, "base_url", normalized_base_url)
        object.__setattr__(self, "model", self.model.strip())

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "NvidiaNimConfig":
        source = os.environ if environ is None else environ
        api_key = str(source.get("NVIDIA_API_KEY", "")).strip()
        base_url = str(
            source.get("GAMEFI_NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL)
        ).strip()
        model = str(source.get("GAMEFI_NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL)).strip()
        timeout_seconds = _env_float(
            source,
            "GAMEFI_NVIDIA_TIMEOUT_SECONDS",
            default=60.0,
        )
        max_retries = _env_int(
            source,
            "GAMEFI_NVIDIA_MAX_RETRIES",
            default=2,
        )
        default_max_tokens = _env_int(
            source,
            "GAMEFI_NVIDIA_MAX_TOKENS",
            default=2048,
        )
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            default_max_tokens=default_max_tokens,
        )


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    model: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class NvidiaNimClient:
    """Small OpenAI-compatible NVIDIA NIM client with bounded retries."""

    def __init__(
        self,
        config: NvidiaNimConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(config.timeout_seconds),
            transport=transport,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NvidiaNimClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        top_p: float = 1.0,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> TextGenerationResult:
        if not messages:
            raise ValueError("at least one chat message is required")
        if not 0 <= temperature <= 1:
            raise ValueError("temperature must be between 0 and 1")
        if not 0 < top_p <= 1:
            raise ValueError("top_p must be > 0 and <= 1")

        active_max_tokens = max_tokens or self.config.default_max_tokens
        if not 1 <= active_max_tokens <= 16_384:
            raise ValueError("max_tokens must be between 1 and 16384")

        active_model = (model or self.config.model).strip()
        if not active_model:
            raise ValueError("model must not be blank")

        payload = {
            "model": active_model,
            "messages": [message.as_payload() for message in messages],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": active_max_tokens,
            "stream": False,
        }

        attempts = self.config.max_retries + 1
        last_error: NvidiaNimRequestError | None = None

        for attempt in range(attempts):
            retry_after: str | None = None
            try:
                response = self._client.post("chat/completions", json=payload)
            except httpx.HTTPError as exc:
                retryable = attempt < attempts - 1
                last_error = NvidiaNimRequestError(
                    f"NVIDIA NIM request failed: {type(exc).__name__}",
                    retryable=retryable,
                )
            else:
                if response.status_code < 400:
                    result = _parse_completion(response, requested_model=active_model)
                    logger.info(
                        "nvidia_nim_completion_success model=%s finish_reason=%s "
                        "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                        result.model,
                        result.finish_reason,
                        result.prompt_tokens,
                        result.completion_tokens,
                        result.total_tokens,
                    )
                    return result

                retryable_status = _is_retryable_status(response.status_code)
                retry_after = response.headers.get("Retry-After")
                last_error = NvidiaNimRequestError(
                    f"NVIDIA NIM returned HTTP {response.status_code}",
                    status_code=response.status_code,
                    retryable=retryable_status and attempt < attempts - 1,
                )
                if not retryable_status:
                    logger.warning(
                        "nvidia_nim_request_failed status_code=%s retryable=false",
                        response.status_code,
                    )
                    raise last_error

            if attempt < attempts - 1 and last_error is not None and last_error.retryable:
                delay = _retry_delay_seconds(attempt, retry_after)
                logger.warning(
                    "nvidia_nim_retry attempt=%s/%s status_code=%s delay_seconds=%s",
                    attempt + 1,
                    attempts,
                    last_error.status_code,
                    delay,
                )
                self._sleep(delay)
                continue

            if last_error is not None:
                logger.warning(
                    "nvidia_nim_request_failed status_code=%s retryable=%s",
                    last_error.status_code,
                    last_error.retryable,
                )
                raise last_error

        raise NvidiaNimRequestError("NVIDIA NIM request failed without a response")

    def smoke_test(self) -> TextGenerationResult:
        return self.complete(
            (
                ChatMessage(
                    role="system",
                    content="You are a connectivity probe. Keep the answer extremely short.",
                ),
                ChatMessage(role="user", content="Reply with NVIDIA_NIM_OK."),
            ),
            temperature=0,
            max_tokens=32,
        )


def _parse_completion(
    response: httpx.Response,
    *,
    requested_model: str,
) -> TextGenerationResult:
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise NvidiaNimRequestError(
            "NVIDIA NIM returned invalid JSON",
            status_code=response.status_code,
            retryable=False,
        ) from exc

    if not isinstance(payload, dict):
        raise NvidiaNimRequestError(
            "NVIDIA NIM JSON response must be an object",
            status_code=response.status_code,
            retryable=False,
        )

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise NvidiaNimRequestError(
            "NVIDIA NIM response is missing choices[0]",
            status_code=response.status_code,
            retryable=False,
        )

    first = choices[0]
    message = first.get("message")
    if not isinstance(message, dict):
        raise NvidiaNimRequestError(
            "NVIDIA NIM response is missing choices[0].message",
            status_code=response.status_code,
            retryable=False,
        )

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise NvidiaNimRequestError(
            "NVIDIA NIM response contains no text content",
            status_code=response.status_code,
            retryable=False,
        )

    usage = payload.get("usage")
    usage_mapping = usage if isinstance(usage, dict) else {}
    model = payload.get("model")

    # Deliberately ignore provider-specific reasoning_content. GamCryp only
    # consumes the final answer and token metadata; hidden reasoning is neither
    # persisted nor logged.
    return TextGenerationResult(
        text=content.strip(),
        model=str(model).strip() if isinstance(model, str) and model.strip() else requested_model,
        finish_reason=_optional_text(first.get("finish_reason")),
        prompt_tokens=_optional_int(usage_mapping.get("prompt_tokens")),
        completion_tokens=_optional_int(usage_mapping.get("completion_tokens")),
        total_tokens=_optional_int(usage_mapping.get("total_tokens")),
    )


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 409, 425, 429} or status_code >= 500


def _retry_delay_seconds(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 8.0)
        except ValueError:
            pass
    return min(0.5 * (2**attempt), 8.0)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _env_int(source: Mapping[str, str], key: str, *, default: int) -> int:
    raw = str(source.get(key, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise NvidiaNimConfigurationError(f"{key} must be an integer") from exc


def _env_float(source: Mapping[str, str], key: str, *, default: float) -> float:
    raw = str(source.get(key, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise NvidiaNimConfigurationError(f"{key} must be a number") from exc
