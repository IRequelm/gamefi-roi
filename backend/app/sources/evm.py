"""Generic EVM JSON-RPC source helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.sources.errors import SourceErrorDetail, SourceParseError, SourceRequestError
from app.sources.http import SourceHttpClient
from app.sources.observations import Observation, ObservationStatus, SourceType


UINT_WORD_HEX_LENGTH = 64


@dataclass(frozen=True)
class ContractCallOutput:
    entity_type: str
    entity_id: str
    metric: str
    unit: str
    word_index: int
    quote_currency: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractCallObservationRequest:
    to_address: str
    data: str
    block_tag: str
    outputs: tuple[ContractCallOutput, ...]
    freshness_window: timedelta
    operation: str


class EvmJsonRpcSource:
    provider_name: str

    def __init__(
        self,
        *,
        provider_name: str,
        rpc_url: str,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.provider_name = provider_name
        base_url, rpc_path = _split_rpc_url(rpc_url)
        self._rpc_path = rpc_path
        self._client = SourceHttpClient(
            provider=provider_name,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def call(self, method: str, params: list[Any], *, operation: str) -> Any:
        payload = self._client.post_json(
            self._rpc_path,
            json_payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            },
            operation=operation,
        )
        if "error" in payload:
            error = payload["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise SourceRequestError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"JSON-RPC error: {message}",
                    retryable=False,
                )
            )
        if "result" not in payload:
            raise SourceParseError(
                SourceErrorDetail(
                    provider=self.provider_name,
                    operation=operation,
                    message="JSON-RPC response did not include a result",
                    retryable=False,
                )
            )
        return payload["result"]

    def observe_chain_id(self, freshness_window: timedelta) -> Observation:
        result = self.call("eth_chainId", [], operation="eth_chainId")
        value = Decimal(hex_to_int(result, provider=self.provider_name, operation="eth_chainId"))
        return self._observation(
            entity_type="chain",
            entity_id=f"evm:{int(value)}",
            metric="evm.chain_id",
            value=value,
            unit="chain_id",
            source_locator=self._source_locator("eth_chainId", []),
            metadata={},
            freshness_window=freshness_window,
        )

    def observe_gas_price_wei(self, freshness_window: timedelta) -> Observation:
        result = self.call("eth_gasPrice", [], operation="eth_gasPrice")
        value = Decimal(hex_to_int(result, provider=self.provider_name, operation="eth_gasPrice"))
        return self._observation(
            entity_type="chain",
            entity_id="evm:gas",
            metric="evm.gas_price_wei",
            value=value,
            unit="wei",
            source_locator=self._source_locator("eth_gasPrice", []),
            metadata={},
            freshness_window=freshness_window,
        )

    def observe_contract_call_words(self, request: ContractCallObservationRequest) -> tuple[Observation, ...]:
        raw = self.call(
            "eth_call",
            [{"to": request.to_address, "data": request.data}, request.block_tag],
            operation=request.operation,
        )
        words = decode_uint_words(raw, provider=self.provider_name, operation=request.operation)
        retrieved_at = datetime.now(UTC)
        fresh_until = retrieved_at + request.freshness_window
        locator = self._source_locator(
            "eth_call",
            [{"to": request.to_address, "data": request.data}, request.block_tag],
        )
        observations: list[Observation] = []
        for output in request.outputs:
            if output.word_index >= len(words):
                raise SourceParseError(
                    SourceErrorDetail(
                        provider=self.provider_name,
                        operation=request.operation,
                        message=f"Output word index {output.word_index} was not present",
                        retryable=False,
                    )
                )
            observations.append(
                Observation(
                    observation_id=self._observation_id(
                        entity_id=output.entity_id,
                        metric=output.metric,
                        observed_at=retrieved_at,
                    ),
                    entity_type=output.entity_type,
                    entity_id=output.entity_id,
                    metric=output.metric,
                    value=Decimal(words[output.word_index]),
                    unit=output.unit,
                    quote_currency=output.quote_currency,
                    source_provider=self.provider_name,
                    source_type=SourceType.ONCHAIN,
                    source_locator=locator,
                    observed_at=retrieved_at,
                    retrieved_at=retrieved_at,
                    fresh_until=fresh_until,
                    status=ObservationStatus.FRESH,
                    metadata={
                        "contract_address": request.to_address,
                        "call_data": request.data,
                        "block_tag": request.block_tag,
                        "word_index": output.word_index,
                        **output.metadata,
                    },
                )
            )
        return tuple(observations)

    def _observation(
        self,
        *,
        entity_type: str,
        entity_id: str,
        metric: str,
        value: Decimal,
        unit: str,
        source_locator: str,
        metadata: dict[str, Any],
        freshness_window: timedelta,
    ) -> Observation:
        retrieved_at = datetime.now(UTC)
        return Observation(
            observation_id=self._observation_id(entity_id=entity_id, metric=metric, observed_at=retrieved_at),
            entity_type=entity_type,
            entity_id=entity_id,
            metric=metric,
            value=value,
            unit=unit,
            quote_currency=None,
            source_provider=self.provider_name,
            source_type=SourceType.ONCHAIN,
            source_locator=source_locator,
            observed_at=retrieved_at,
            retrieved_at=retrieved_at,
            fresh_until=retrieved_at + freshness_window,
            status=ObservationStatus.FRESH,
            metadata=metadata,
        )

    def _source_locator(self, method: str, params: list[Any]) -> str:
        return f"{self._client.source_locator(self._rpc_path, {})}#{method}:{params}"

    def _observation_id(self, *, entity_id: str, metric: str, observed_at: datetime) -> str:
        key = f"{self.provider_name}|{entity_id}|{metric}|{observed_at.isoformat()}"
        return str(uuid5(NAMESPACE_URL, key))


def hex_to_int(value: Any, *, provider: str, operation: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise SourceParseError(
            SourceErrorDetail(
                provider=provider,
                operation=operation,
                message="Expected a hex-encoded JSON-RPC value",
                retryable=False,
            )
        )
    try:
        return int(value, 16)
    except ValueError as exc:
        raise SourceParseError(
            SourceErrorDetail(
                provider=provider,
                operation=operation,
                message=f"Invalid hex-encoded JSON-RPC value: {value}",
                retryable=False,
            )
        ) from exc


def decode_uint_words(data: Any, *, provider: str, operation: str) -> tuple[int, ...]:
    if not isinstance(data, str) or not data.startswith("0x"):
        raise SourceParseError(
            SourceErrorDetail(
                provider=provider,
                operation=operation,
                message="Expected hex-encoded call data",
                retryable=False,
            )
        )
    body = data[2:]
    if len(body) % UINT_WORD_HEX_LENGTH != 0:
        raise SourceParseError(
            SourceErrorDetail(
                provider=provider,
                operation=operation,
                message="Call data length is not a whole number of ABI words",
                retryable=False,
            )
        )
    return tuple(int(body[index : index + UINT_WORD_HEX_LENGTH], 16) for index in range(0, len(body), UINT_WORD_HEX_LENGTH))


def decode_address_word(data: Any, *, provider: str, operation: str, word_index: int = 0) -> str:
    words = decode_uint_words(data, provider=provider, operation=operation)
    if word_index >= len(words):
        raise SourceParseError(
            SourceErrorDetail(
                provider=provider,
                operation=operation,
                message=f"Address word index {word_index} was not present",
                retryable=False,
            )
        )
    return f"0x{words[word_index]:040x}"


def _split_rpc_url(rpc_url: str) -> tuple[str, str]:
    normalized = rpc_url.rstrip("/")
    parsed = urlsplit(normalized)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return normalized, ""

    rpc_path = path_parts[-1]
    parent_path = "/" + "/".join(path_parts[:-1]) if len(path_parts) > 1 else ""
    base_url = urlunsplit((parsed.scheme, parsed.netloc, parent_path, "", ""))
    return base_url, rpc_path
