from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from app.sources.errors import SourceParseError, SourceRequestError
from app.sources.evm import (
    ContractCallObservationRequest,
    ContractCallOutput,
    EvmJsonRpcSource,
    decode_address_word,
    decode_uint_words,
)


def test_evm_source_maps_json_rpc_results_to_observations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "eth_chainId":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0xd2af"}, request=request)
        if payload["method"] == "eth_gasPrice":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x2540be4000"}, request=request)
        if payload["method"] == "eth_call":
            result = "0x" + "0" * 63 + "a" + "0" * 63 + "f"
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result}, request=request)
        raise AssertionError(payload["method"])

    source = EvmJsonRpcSource(
        provider_name="fixture-rpc",
        rpc_url="https://rpc.example",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    chain_id = source.observe_chain_id(timedelta(minutes=5))
    gas_price = source.observe_gas_price_wei(timedelta(minutes=5))
    outputs = source.observe_contract_call_words(
        ContractCallObservationRequest(
            to_address="0x0000000000000000000000000000000000000001",
            data="0x12345678",
            block_tag="latest",
            operation="fixture_call",
            freshness_window=timedelta(minutes=5),
            outputs=(
                ContractCallOutput("strategy", "fixture", "fixture.word0", "unit", 0),
                ContractCallOutput("strategy", "fixture", "fixture.word1", "unit", 1),
            ),
        )
    )

    assert chain_id.value == Decimal(53935)
    assert gas_price.value == Decimal(160000000000)
    assert [observation.value for observation in outputs] == [Decimal(10), Decimal(15)]
    assert all(observation.source_provider == "fixture-rpc" for observation in outputs)


def test_evm_source_reports_json_rpc_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"message": "boom"}}, request=request)

    source = EvmJsonRpcSource(
        provider_name="fixture-rpc",
        rpc_url="https://rpc.example",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SourceRequestError, match="boom"):
        source.observe_chain_id(timedelta(minutes=5))


def test_evm_source_preserves_rpc_query_for_request_and_redacts_locator() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0xd2af"}, request=request)

    source = EvmJsonRpcSource(
        provider_name="fixture-rpc",
        rpc_url="https://rpc.example/dfk/rpc?apikey=secret-token&network=dfk",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    observation = source.observe_chain_id(timedelta(minutes=5))

    assert seen_urls == ["https://rpc.example/dfk/rpc?apikey=secret-token&network=dfk"]
    assert "apikey=secret-token" not in observation.source_locator
    assert "apikey=REDACTED" in observation.source_locator
    assert "network=dfk" in observation.source_locator


def test_evm_decoder_rejects_bad_call_data() -> None:
    with pytest.raises(SourceParseError):
        decode_uint_words("0x123", provider="fixture", operation="decode")


def test_evm_decoder_reads_address_words() -> None:
    address = "000000000000000000000000ccb93dabd71c8dad03fc4ce5559dc3d89f67a260"

    assert (
        decode_address_word(f"0x{address}", provider="fixture", operation="decode")
        == "0xccb93dabd71c8dad03fc4ce5559dc3d89f67a260"
    )
