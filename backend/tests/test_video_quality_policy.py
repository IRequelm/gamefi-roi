from __future__ import annotations

from pathlib import Path

import pytest

from app.distribution.content_pack import ContentReadiness
from app.distribution.x_queue import load_content_pack_batch
from app.distribution.youtube_queue import build_youtube_publish_queue, narration_quality_blockers

ROOT = Path(__file__).resolve().parents[2]
SOURCE_BATCH = ROOT / "distribution/content_packs/learning_batch_001.json"


def _green_video_pack(*, mode: str, provider: str | None = None, quality: str = "approved"):
    payload, packs = load_content_pack_batch(SOURCE_BATCH)
    source = next(pack for pack in packs if pack.content_id == "x-gamcryp-methodology-not-recommendation-20260831")
    editorial = source.editorial.model_copy(
        update={
            "youtube_title": "GamCryp methodology",
            "youtube_short_script": "Source-backed methodology video.",
            "youtube_description": "A source-backed methodology explanation.",
            "narration_mode": mode,
            "voice_provider": provider,
            "narration_quality_status": quality,
        }
    )
    return payload, (source.model_copy(update={"editorial": editorial}),)


@pytest.mark.parametrize(
    ("mode", "provider", "quality", "expected"),
    [
        ("neural_voice", "system", "approved", "forbidden"),
        ("neural_voice", "elevenlabs", "not_ready", "not approved"),
        ("neural_voice", "elevenlabs", "approved", None),
        ("music_only", None, "approved", "publishable Shorts require approved narration"),
        ("silent", None, "approved", "publishable Shorts require approved narration"),
        ("unknown", None, "unknown", "unknown"),
    ],
)
def test_narration_quality_gate(mode, provider, quality, expected) -> None:
    payload, packs = _green_video_pack(mode=mode, provider=provider, quality=quality)
    queue = build_youtube_publish_queue(
        batch_payload=payload,
        packs=packs,
        source_batch_bytes=b"quality-policy-fixture",
    )
    item = queue.items[0]
    blockers = narration_quality_blockers(item)
    if expected:
        assert expected in blockers[0]
        assert queue.publishable == ()
        assert queue.pending_asset == (item,)
    else:
        assert blockers == ()
        assert queue.publishable == (item,)


def test_quality_metadata_is_bound_into_explicit_package_checksum() -> None:
    payload, neural = _green_video_pack(mode="neural_voice", provider="elevenlabs")
    _, silent = _green_video_pack(mode="silent")
    neural_queue = build_youtube_publish_queue(batch_payload=payload, packs=neural, source_batch_bytes=b"same")
    silent_queue = build_youtube_publish_queue(batch_payload=payload, packs=silent, source_batch_bytes=b"same")
    assert neural_queue.items[0].package_checksum != silent_queue.items[0].package_checksum
