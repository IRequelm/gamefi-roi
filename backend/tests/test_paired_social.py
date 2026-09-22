from datetime import UTC, datetime
from types import SimpleNamespace

from app.distribution.x_queue import x_weighted_character_count
from app.publishing.paired_social import (
    PairedSocialStore,
    build_paired_x_text,
    pairing_key,
    write_outbox,
    youtube_record,
)


def _item() -> SimpleNamespace:
    return SimpleNamespace(
        package_id="package-short_form-demo",
        content_id="demo-content",
        title="A useful GamCryp Short",
        source_url="https://gamcryp.com/opportunities/demo?utm_source=youtube",
        video_path="data/local/video_render/short/demo.mp4",
        video_checksum="abc123",
    )


def test_paired_copy_is_within_x_limit_and_contains_youtube_link() -> None:
    copy = build_paired_x_text(
        title="A useful GamCryp Short",
        youtube_video_id="abc12345678",
        source_url="https://gamcryp.com/opportunities/demo",
    )
    assert x_weighted_character_count(copy) <= 280
    assert "https://youtu.be/abc12345678" in copy


def test_paired_store_and_outbox_are_restart_safe(tmp_path) -> None:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    item = _item()
    record = youtube_record(item=item, youtube_video_id="abc12345678", now=now)
    state_path = tmp_path / "paired.json"
    outbox_path = tmp_path / "outbox.json"

    store = PairedSocialStore(state_path)
    store.put(pairing_key(item.content_id, item.video_checksum), record)
    reloaded = PairedSocialStore(state_path)
    assert reloaded.get(record["key"])["youtube_video_id"] == "abc12345678"

    write_outbox(outbox_path, reloaded.all(), now=now)
    payload = outbox_path.read_text(encoding="utf-8")
    assert "abc12345678" in payload
    assert "x_status" in payload


def test_published_pair_is_not_written_to_manual_outbox(tmp_path) -> None:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    record = youtube_record(item=_item(), youtube_video_id="abc12345678", now=now)
    record["x_status"] = "published"
    outbox_path = tmp_path / "outbox.json"

    write_outbox(outbox_path, [record], now=now)
    assert '"items": []' in outbox_path.read_text(encoding="utf-8")
