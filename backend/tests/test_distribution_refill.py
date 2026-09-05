from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.distribution.content_pack import ContentReadiness, set_expected_source_hash, validate_pack
from app.distribution.refill import DistributionRefillConfig, DistributionRefiller
from app.distribution.x_queue import load_content_pack_batch
from app.distribution.youtube_queue import (
    YouTubeApprovalState,
    YouTubePublishQueue,
    YouTubeQueueItem,
    build_youtube_publish_queue,
    write_youtube_queue,
)


ROOT = Path(__file__).parents[2]
SOURCE_PACK = ROOT / "distribution/content_packs/learning_batch_001.json"
SOURCE_YOUTUBE_QUEUE = ROOT / "distribution/publish_queue/youtube_publish_queue.json"
SOURCE_X_QUEUE = ROOT / "distribution/publish_queue/x_publish_queue.json"
NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def _item(content_id: str = "green-video") -> YouTubeQueueItem:
    return YouTubeQueueItem(
        content_id=content_id,
        project="Test",
        title="Test video",
        description="Test description",
        short_script="Test script",
        attribution_url="https://example.com/?utm_content=green-video",
        status=ContentReadiness.GREEN,
        approval_required=False,
        approval_state=YouTubeApprovalState.NOT_REQUIRED,
        source_snapshot_hash="source",
        official_source_refs=(),
        package_checksum="package",
        recommended_order=1,
        source_pack_version="content-pack-lite-v1",
        generated_at=NOW.isoformat(),
    )


def _queue(path: Path, *items: YouTubeQueueItem) -> None:
    write_youtube_queue(
        path,
        YouTubePublishQueue(
            source_batch_id="test",
            source_batch_hash="test",
            generated_at=NOW.isoformat(),
            publishable=items,
            awaiting_human_approval=(),
            blocked=(),
        ),
    )


def _config(tmp_path: Path, *, buffer_size: int = 1) -> DistributionRefillConfig:
    return DistributionRefillConfig(
        enabled=True,
        buffer_size=buffer_size,
        cooldown_hours=24,
        content_pack_file=tmp_path / "learning.json",
        youtube_queue_file=tmp_path / "youtube.json",
        x_queue_file=tmp_path / "x.json",
        handoff_file=tmp_path / "handoff.json",
        youtube_state_file=tmp_path / "youtube-state.json",
        x_state_file=tmp_path / "x-state.json",
        video_directory=tmp_path / "videos",
        state_file=tmp_path / "refill-state.json",
    )


def test_no_refill_when_both_platform_buffers_are_sufficient(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _queue(config.youtube_queue_file, _item())
    config.x_queue_file.write_text(json.dumps({"publishable": [{"content_id": "green-x"}]}), encoding="utf-8")
    refiller = DistributionRefiller(config, fetch_json=lambda _: (_ for _ in ()).throw(AssertionError("fetched")))

    result = refiller.run(now=NOW)

    assert result["status"] == "buffer_sufficient"


def test_refill_is_bounded_and_restart_safe(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.content_pack_file.write_bytes(SOURCE_PACK.read_bytes())
    config.youtube_queue_file.write_bytes(SOURCE_YOUTUBE_QUEUE.read_bytes())
    config.x_queue_file.write_bytes(SOURCE_X_QUEUE.read_bytes())
    _, packs = load_content_pack_batch(SOURCE_PACK)
    calls: list[str] = []

    def fetch(_: str) -> dict:
        calls.append("fetch")
        return {}

    refiller = DistributionRefiller(config, fetch_json=fetch, build_packs=lambda *_args, **_kwargs: list(packs))

    first = refiller.run(now=NOW)
    second = refiller.run(now=NOW + timedelta(hours=1))

    assert first["status"] == "refilled"
    assert second["status"] == "cooldown"
    assert calls == ["fetch", "fetch"]


def test_stale_source_pack_is_not_green() -> None:
    _, packs = load_content_pack_batch(SOURCE_PACK)

    stale = [pack for pack in packs if pack.facts.freshness.display.lower() == "stale"]

    assert stale
    assert all(validate_pack(pack).readiness is ContentReadiness.RED for pack in stale)


def test_youtube_green_without_render_asset_is_pending_asset(tmp_path: Path) -> None:
    _, packs = load_content_pack_batch(SOURCE_PACK)
    methodology = next(pack for pack in packs if pack.source.opportunity_id == "gamcryp-methodology")
    candidate = set_expected_source_hash(
        methodology.model_copy(
            update={
                "editorial": methodology.editorial.model_copy(
                    update={
                        "youtube_title": "Test title",
                        "youtube_short_script": "Test script",
                        "youtube_description": "Test description",
                    }
                )
            }
        )
    )
    assert validate_pack(candidate).readiness is ContentReadiness.GREEN

    queue = build_youtube_publish_queue(
        batch_payload={"batch_id": "test", "generated_at": NOW.isoformat()},
        packs=(candidate,),
        source_batch_bytes=b"test",
        video_directory=tmp_path / "missing-videos",
    )

    assert queue.publishable == ()
    assert [item.content_id for item in queue.pending_asset] == [candidate.content_id]
