from __future__ import annotations

import json

import httpx
import pytest

from app.ai.nvidia import (
    ChatMessage,
    NvidiaNimClient,
    NvidiaNimConfig,
    NvidiaNimConfigurationError,
    NvidiaNimRequestError,
)


def test_config_reads_render_secret_without_exposing_it_in_repr() -> None:
    config = NvidiaNimConfig.from_env(
        {
            "NVIDIA_API_KEY": "nvapi-secret-test",
            "GAMEFI_NVIDIA_MODEL": "openai/gpt-oss-120b",
        }
    )

    assert config.api_key == "nvapi-secret-test"
    assert config.model == "openai/gpt-oss-120b"
    assert "nvapi-secret-test" not in repr(config)


def test_config_requires_api_key() -> None:
    with pytest.raises(NvidiaNimConfigurationError):
        NvidiaNimConfig.from_env({})


def test_completion_uses_openai_compatible_endpoint_and_parses_usage() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "NVIDIA_NIM_OK",
                            "reasoning_content": "must not be persisted",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            },
        )

    config = NvidiaNimConfig(api_key="nvapi-secret-test")
    with NvidiaNimClient(
        config,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    ) as client:
        result = client.complete(
            [ChatMessage(role="user", content="ping")],
            max_tokens=32,
        )

    assert captured["path"] == "/v1/chat/completions"
    assert captured["authorization"] == "Bearer nvapi-secret-test"
    assert captured["payload"] == {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 32,
        "stream": False,
    }
    assert result.text == "NVIDIA_NIM_OK"
    assert result.total_tokens == 14
    assert not hasattr(result, "reasoning_content")


def test_429_retries_with_retry_after_then_succeeds() -> None:
    attempts = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1.25"}, json={"error": "rate limit"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    config = NvidiaNimConfig(api_key="nvapi-secret-test", max_retries=2)
    with NvidiaNimClient(
        config,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    ) as client:
        result = client.complete([ChatMessage(role="user", content="ping")])

    assert result.text == "ok"
    assert attempts == 2
    assert sleeps == [1.25]


def test_401_fails_closed_without_retry_or_secret_leak() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    config = NvidiaNimConfig(api_key="nvapi-secret-test", max_retries=2)
    with NvidiaNimClient(
        config,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: pytest.fail("401 must not retry"),
    ) as client:
        with pytest.raises(NvidiaNimRequestError) as caught:
            client.complete([ChatMessage(role="user", content="ping")])

    assert attempts == 1
    assert caught.value.status_code == 401
    assert "nvapi-secret-test" not in str(caught.value)


def test_malformed_success_payload_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    config = NvidiaNimConfig(api_key="nvapi-secret-test")
    with NvidiaNimClient(
        config,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    ) as client:
        with pytest.raises(NvidiaNimRequestError, match=r"choices\[0\]"):
            client.complete([ChatMessage(role="user", content="ping")])
