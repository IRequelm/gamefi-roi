from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.publishing.elevenlabs import (
    ElevenLabsConfig,
    ElevenLabsConfigError,
    ElevenLabsNarrationProvider,
    ElevenLabsProviderError,
)


def _config(tmp_path: Path, **overrides) -> ElevenLabsConfig:
    values = {
        "api_key": "secret-eleven-key",
        "voice_id": "voice-123",
        "model_id": "model-123",
        "output_directory": tmp_path / "narration",
    }
    values.update(overrides)
    return ElevenLabsConfig(**values)


def _client(response: httpx.Response) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


def test_successful_neural_narration_records_safe_metadata(tmp_path: Path) -> None:
    provider = ElevenLabsNarrationProvider(
        _config(tmp_path),
        client=_client(httpx.Response(200, content=b"neural-audio")),
    )

    result = provider.generate(content_id="green-video", script="A source-backed explanation.")

    assert result.reused is False
    assert result.metadata.narration_mode == "neural_voice"
    assert result.metadata.voice_provider == "elevenlabs"
    assert result.metadata.voice_id == "voice-123"
    assert result.metadata.model_id == "model-123"
    assert result.metadata.narration_quality_status == "approved"
    assert Path(result.metadata.audio_path).is_file()
    assert Path(result.metadata.audio_path).with_suffix(".json").is_file()


def test_matching_asset_is_reused_without_second_api_request(tmp_path: Path) -> None:
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda request: (calls.append(request), httpx.Response(200, content=b"audio"))[1]))
    provider = ElevenLabsNarrationProvider(_config(tmp_path), client=client)

    first = provider.generate(content_id="green-video", script="Same script.")
    second = provider.generate(content_id="green-video", script="Same script.")

    assert first.reused is False
    assert second.reused is True
    assert len(calls) == 1


@pytest.mark.parametrize(
    "config",
    [
        _config(Path("."), api_key=None),
        _config(Path("."), voice_id=None),
        _config(Path("."), model_id=None),
    ],
)
def test_missing_required_configuration_fails_closed(config: ElevenLabsConfig) -> None:
    provider = ElevenLabsNarrationProvider(config, client=_client(httpx.Response(200, content=b"audio")))

    with pytest.raises(ElevenLabsConfigError):
        provider.generate(content_id="green-video", script="Script")


def test_rejected_credentials_fail_closed_without_secret_in_error(tmp_path: Path) -> None:
    provider = ElevenLabsNarrationProvider(
        _config(tmp_path),
        client=_client(httpx.Response(401, json={"detail": "invalid api key"})),
    )

    with pytest.raises(ElevenLabsProviderError, match="credentials were rejected") as error:
        provider.generate(content_id="green-video", script="Script")
    assert "secret-eleven-key" not in str(error.value)
    assert not list((tmp_path / "narration").glob("*"))


def test_provider_error_does_not_fallback_to_basic_tts(tmp_path: Path) -> None:
    provider = ElevenLabsNarrationProvider(
        _config(tmp_path),
        client=_client(httpx.Response(500, content=b"provider failure")),
    )

    with pytest.raises(ElevenLabsProviderError):
        provider.generate(content_id="green-video", script="Script")
    assert not list((tmp_path / "narration").glob("*"))


def test_safe_result_does_not_expose_api_key(tmp_path: Path) -> None:
    provider = ElevenLabsNarrationProvider(
        _config(tmp_path),
        client=_client(httpx.Response(200, content=b"audio")),
    )
    result = provider.generate(content_id="green-video", script="Script")

    assert "secret-eleven-key" not in json.dumps(result.safe_dict())
