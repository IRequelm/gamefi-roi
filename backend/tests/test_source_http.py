from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.sources.errors import SourceParseError, SourceRequestError
from app.sources.http import SourceHttpClient


def test_http_client_retries_retryable_provider_errors(monkeypatch) -> None:
    monkeypatch.setattr("app.sources.http.time.sleep", lambda _: None)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, text="unavailable", request=request)
        return httpx.Response(200, text='{"price": 1.25}', request=request)

    client = SourceHttpClient(
        provider="fixture",
        base_url="https://provider.example",
        timeout_seconds=1,
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )

    payload = client.get_json("/price", params={}, operation="test")

    assert calls == 2
    assert payload["price"] == Decimal("1.25")


def test_http_client_does_not_retry_non_retryable_status(monkeypatch) -> None:
    monkeypatch.setattr("app.sources.http.time.sleep", lambda _: None)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, text="not found", request=request)

    client = SourceHttpClient(
        provider="fixture",
        base_url="https://provider.example",
        timeout_seconds=1,
        max_retries=3,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SourceRequestError) as exc_info:
        client.get_json("/missing", params={}, operation="test")

    assert calls == 1
    assert exc_info.value.detail.status_code == 404
    assert exc_info.value.detail.retryable is False


def test_http_client_reports_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="{not json", request=request)

    client = SourceHttpClient(
        provider="fixture",
        base_url="https://provider.example",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SourceParseError):
        client.get_json("/broken", params={}, operation="test")


def test_http_client_posts_json_payloads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/rpc"
        assert request.content == b'{"jsonrpc":"2.0","id":1}'
        return httpx.Response(200, text='{"result": "ok"}', request=request)

    client = SourceHttpClient(
        provider="fixture",
        base_url="https://provider.example",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    assert client.post_json("/rpc", json_payload={"jsonrpc": "2.0", "id": 1}, operation="post") == {"result": "ok"}
