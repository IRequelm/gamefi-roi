from __future__ import annotations

from pathlib import Path

import pytest

from app.distribution.content_pack import ContentReadiness
from app.distribution.x_queue import load_content_pack_batch
from app.distribution.youtube_queue import (
    build_youtube_publish_queue,
    load_youtube_queue,
    youtube_package_checksum,
)
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.publishing.youtube_distribution import (
    YouTubeApprovalStore,
    YouTubeDistributionConfig,
    YouTubeDistributionError,
    YouTubeDistributionPublisher,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_BATCH = ROOT / "distribution/content_packs/learning_batch_001.json"
SOURCE_QUEUE = ROOT / "distribution/publish_queue/youtube_publish_queue.json"
GRASS_ID = "x-grass-roi-unavailable-20260831"
DIMO_ID = "x-dimo-subscription-catch-20260831"
GEODNET_ID = "x-geodnet-rank-risk-20260831"


def _service(tmp_path: Path) -> YouTubeDistributionPublisher:
    publisher = YouTubePublisher(
        config=YouTubePublisherConfig(
            client_secrets_file=None,
            token_file=None,
            state_file=tmp_path / "publish_state.json",
        ),
        service=object(),
    )
    config = YouTubeDistributionConfig(
        content_pack_file=SOURCE_BATCH,
        queue_file=SOURCE_QUEUE,
        approval_file=tmp_path / "approvals.json",
    )
    return YouTubeDistributionPublisher(
        publisher,
        config=config,
        approvals=YouTubeApprovalStore(config.approval_file),
    )


def _video(tmp_path: Path, content: bytes = b"rendered-short") -> Path:
    path = tmp_path / "short.mp4"
    path.write_bytes(content)
    return path


def test_current_youtube_queue_is_deterministic_and_uses_current_gating() -> None:
    source_bytes = SOURCE_BATCH.read_bytes()
    payload, packs = load_content_pack_batch(SOURCE_BATCH)

    first = build_youtube_publish_queue(
        batch_payload=payload,
        packs=packs,
        source_batch_bytes=source_bytes,
    )
    second = build_youtube_publish_queue(
        batch_payload=payload,
        packs=packs,
        source_batch_bytes=source_bytes,
    )

    assert first == second == load_youtube_queue(SOURCE_QUEUE)
    assert first.publishable == ()
    assert [item.content_id for item in first.awaiting_human_approval] == [GRASS_ID]
    assert {item.content_id for item in first.blocked} == {DIMO_ID, GEODNET_ID}
    assert all(item.video_asset_state == "missing" for item in first.items)
    assert all(item.thumbnail_asset_state == "missing" for item in first.items)
    assert all(item.upload_state == "not_uploaded" for item in first.items)


def test_queue_preserves_provenance_without_financial_recomputation() -> None:
    queue = load_youtube_queue(SOURCE_QUEUE)
    _, packs = load_content_pack_batch(SOURCE_BATCH)

    for item in queue.items:
        pack = next(pack for pack in packs if pack.content_id == item.content_id)
        assert item.source_snapshot_id == pack.source.snapshot_id
        assert item.source_snapshot_timestamp == pack.source.snapshot_timestamp
        assert item.source_snapshot_hash == pack.source.source_snapshot_hash
        assert item.official_source_refs == tuple(pack.source.official_source_refs)
        assert item.package_checksum == youtube_package_checksum(pack)
        assert item.attribution_url in item.description


def test_grass_yellow_requires_exact_creative_approval(tmp_path: Path) -> None:
    service = _service(tmp_path)
    video = _video(tmp_path)

    before = service.preview(GRASS_ID, video_path=video)
    approval = service.approve(GRASS_ID, video_path=video)
    after = service.preview(GRASS_ID, video_path=video)

    assert before.readiness is ContentReadiness.YELLOW
    assert before.approval_state == "awaiting_human_approval"
    assert before.would_upload is False
    assert after.approval_state == "approved"
    assert after.creative_checksum == approval.creative_checksum
    assert after.would_upload is True


def test_asset_or_package_change_invalidates_yellow_approval(tmp_path: Path) -> None:
    service = _service(tmp_path)
    video = _video(tmp_path)
    service.approve(GRASS_ID, video_path=video)
    video.write_bytes(b"different-render")

    preview = service.preview(GRASS_ID, video_path=video)

    assert preview.approval_state == "approval_invalidated_by_content_or_asset_change"
    assert preview.would_upload is False


@pytest.mark.parametrize("content_id", [DIMO_ID, GEODNET_ID])
def test_current_red_youtube_packages_are_hard_blocked(content_id: str, tmp_path: Path) -> None:
    service = _service(tmp_path)
    video = _video(tmp_path)

    preview = service.preview(content_id, video_path=video)

    assert preview.readiness is ContentReadiness.RED
    assert preview.would_upload is False
    assert any("permanently blocked" in blocker for blocker in preview.blockers)
    with pytest.raises(YouTubeDistributionError, match="RED package cannot be approved"):
        service.approve(content_id, video_path=video)


def test_dry_run_uses_approved_queue_package_and_makes_no_api_call(tmp_path: Path) -> None:
    service = _service(tmp_path)
    video = _video(tmp_path)
    service.approve(GRASS_ID, video_path=video)

    result = service.dry_run(GRASS_ID, video_path=video)

    assert result.status == "ready"
    assert result.would_mutate is False
    assert result.content_id == GRASS_ID
    assert not (tmp_path / "publish_state.json").exists()


def test_revoke_restores_yellow_human_gate(tmp_path: Path) -> None:
    service = _service(tmp_path)
    video = _video(tmp_path)
    service.approve(GRASS_ID, video_path=video)

    service.revoke(GRASS_ID)
    preview = service.preview(GRASS_ID, video_path=video)

    assert preview.approval_state == "awaiting_human_approval"
    assert preview.would_upload is False


def test_missing_video_asset_blocks_preview_and_approval(tmp_path: Path) -> None:
    service = _service(tmp_path)

    preview = service.preview(GRASS_ID)

    assert preview.video_asset_state == "missing"
    assert preview.would_upload is False
    with pytest.raises(YouTubeDistributionError, match="video file does not exist"):
        service.approve(GRASS_ID, video_path=tmp_path / "missing.mp4")
