"""Fail-closed ElevenLabs neural narration generation for local video production."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict

from app.config.settings import Settings

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsError(RuntimeError):
    """Safe operator-facing provider or configuration error."""


class ElevenLabsConfigError(ElevenLabsError):
    pass


class ElevenLabsProviderError(ElevenLabsError):
    pass


class NarrationAssetMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    script_fingerprint: str
    source_script: str
    spoken_text: str
    narration_mode: str = "neural_voice"
    voice_provider: str = "elevenlabs"
    voice_id: str
    model_id: str
    generated_at: str
    audio_path: str
    audio_checksum: str
    narration_quality_status: str = "approved"


@dataclass(frozen=True)
class ElevenLabsConfig:
    api_key: str | None
    voice_id: str | None
    model_id: str | None
    output_directory: Path = Path("data/local/youtube/narration")
    output_format: str = DEFAULT_OUTPUT_FORMAT
    timeout_seconds: float = 60.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "ElevenLabsConfig":
        return cls(
            api_key=settings.elevenlabs_api_key.get_secret_value() if settings.elevenlabs_api_key else None,
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model_id,
            output_directory=Path(settings.elevenlabs_output_directory),
        )

    def require_complete(self) -> tuple[str, str, str]:
        if not self.api_key:
            raise ElevenLabsConfigError("ELEVENLABS_API_KEY is required")
        if not self.voice_id:
            raise ElevenLabsConfigError("ELEVENLABS_VOICE_ID is required")
        if not self.model_id:
            raise ElevenLabsConfigError("ELEVENLABS_MODEL_ID is required")
        return self.api_key, self.voice_id, self.model_id


@dataclass(frozen=True)
class ElevenLabsGenerationResult:
    metadata: NarrationAssetMetadata
    reused: bool

    def safe_dict(self) -> dict[str, object]:
        return {
            "content_id": self.metadata.content_id,
            "status": self.metadata.narration_quality_status,
            "narration_mode": self.metadata.narration_mode,
            "voice_provider": self.metadata.voice_provider,
            "voice_id": self.metadata.voice_id,
            "model_id": self.metadata.model_id,
            "audio_path": self.metadata.audio_path,
            "audio_checksum": self.metadata.audio_checksum,
            "script_fingerprint": self.metadata.script_fingerprint,
            "generated_at": self.metadata.generated_at,
            "reused": self.reused,
        }


class ElevenLabsNarrationProvider:
    def __init__(self, config: ElevenLabsConfig, *, client: httpx.Client | None = None):
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds)

    def generate(self, *, content_id: str, script: str, now: datetime | None = None) -> ElevenLabsGenerationResult:
        text = script.strip()
        if not text:
            raise ElevenLabsConfigError("validated narration script must not be blank")
        api_key, voice_id, model_id = self.config.require_complete()
        fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        output = self.config.output_directory / f"{content_id}-{fingerprint[:16]}.{self.config.output_format.split('_', 1)[0]}"
        metadata_path = output.with_suffix(".json")
        existing = _load_metadata(metadata_path)
        if existing and existing.script_fingerprint == fingerprint and existing.voice_id == voice_id and existing.model_id == model_id and Path(existing.audio_path) == output and output.is_file():
            if _sha256_file(output) == existing.audio_checksum:
                return ElevenLabsGenerationResult(metadata=existing, reused=True)

        try:
            response = self.client.post(
                f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={"text": text, "model_id": model_id, "output_format": self.config.output_format},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ElevenLabsProviderError("ElevenLabs narration request failed due to a network error") from exc
        except httpx.HTTPError as exc:
            raise ElevenLabsProviderError("ElevenLabs narration request failed") from exc
        if response.status_code in {401, 403}:
            raise ElevenLabsProviderError("ElevenLabs credentials were rejected")
        if response.status_code >= 400:
            raise ElevenLabsProviderError(f"ElevenLabs narration request returned status {response.status_code}")
        if not response.content:
            raise ElevenLabsProviderError("ElevenLabs returned an empty narration asset")

        generated_at = (now or datetime.now(UTC)).isoformat()
        audio_checksum = hashlib.sha256(response.content).hexdigest()
        metadata = NarrationAssetMetadata(
            content_id=content_id,
            script_fingerprint=fingerprint,
            source_script=text,
            spoken_text=text,
            voice_id=voice_id,
            model_id=model_id,
            generated_at=generated_at,
            audio_path=str(output),
            audio_checksum=audio_checksum,
        )
        _atomic_write_bytes(output, response.content)
        _atomic_write_text(metadata_path, metadata.model_dump_json(indent=2) + "\n")
        return ElevenLabsGenerationResult(metadata=metadata, reused=False)


def _load_metadata(path: Path) -> NarrationAssetMetadata | None:
    if not path.is_file():
        return None
    try:
        return NarrationAssetMetadata.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))
