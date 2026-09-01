from __future__ import annotations

import json

from app.ai.nvidia import NvidiaNimConfigurationError, NvidiaNimRequestError, TextGenerationResult
from app.operator import ai_routes


class _SuccessfulClient:
    def __init__(self, config) -> None:
        self.config = config

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def smoke_test(self) -> TextGenerationResult:
        return TextGenerationResult(
            text="NVIDIA_NIM_OK",
            model="openai/gpt-oss-120b",
            finish_reason="stop",
            prompt_tokens=8,
            completion_tokens=3,
            total_tokens=11,
        )


def _payload(response) -> dict:
    return json.loads(response.body.decode("utf-8"))


def test_operator_smoke_returns_safe_success_metadata(monkeypatch) -> None:
    monkeypatch.setattr(ai_routes.NvidiaNimConfig, "from_env", lambda: object())
    monkeypatch.setattr(ai_routes, "NvidiaNimClient", _SuccessfulClient)

    response = ai_routes.nvidia_smoke(_operator="ops")
    payload = _payload(response)

    assert response.status_code == 200
    assert payload == {
        "ok": True,
        "provider": "nvidia_nim",
        "model": "openai/gpt-oss-120b",
        "finish_reason": "stop",
        "total_tokens": 11,
        "response_match": True,
    }
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert response.headers["cache-control"] == "no-store"


def test_operator_smoke_hides_provider_error_content(monkeypatch) -> None:
    monkeypatch.setattr(ai_routes.NvidiaNimConfig, "from_env", lambda: object())

    class _FailingClient(_SuccessfulClient):
        def smoke_test(self):
            raise NvidiaNimRequestError(
                "provider body may contain sensitive detail",
                status_code=429,
                retryable=True,
            )

    monkeypatch.setattr(ai_routes, "NvidiaNimClient", _FailingClient)

    response = ai_routes.nvidia_smoke(_operator="ops")
    payload = _payload(response)

    assert response.status_code == 502
    assert payload == {
        "ok": False,
        "provider": "nvidia_nim",
        "error": "provider_request_failed",
        "status_code": 429,
        "retryable": True,
    }
    assert "sensitive" not in response.body.decode("utf-8")


def test_operator_smoke_reports_missing_render_secret_without_key_value(monkeypatch) -> None:
    def _missing_config():
        raise NvidiaNimConfigurationError("NVIDIA_API_KEY is required")

    monkeypatch.setattr(ai_routes.NvidiaNimConfig, "from_env", _missing_config)

    response = ai_routes.nvidia_smoke(_operator="ops")
    payload = _payload(response)

    assert response.status_code == 503
    assert payload["ok"] is False
    assert payload["error"] == "configuration_error"
    assert payload["detail"] == "NVIDIA_API_KEY is required"
