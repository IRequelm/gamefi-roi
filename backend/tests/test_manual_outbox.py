from __future__ import annotations

import json
from datetime import UTC, datetime

from app.distribution.manual_outbox import XManualOutbox, manual_ready_record


def test_manual_outbox_deduplicates_and_keeps_existing_pending_item(tmp_path):
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    first = manual_ready_record(
        content_id="first",
        post_text="First post",
        source_url="https://example.com/first",
        checksum="checksum-1",
        now=datetime(2026, 9, 5, tzinfo=UTC),
    )
    older = manual_ready_record(
        content_id="older",
        post_text="Older post",
        source_url="https://example.com/older",
        checksum="checksum-2",
        now=datetime(2026, 9, 4, tzinfo=UTC),
    )

    assert outbox.prepare(first) == "written"
    assert outbox.prepare(first) == "unchanged"
    assert outbox.prepare(older) == "retained_existing"
    assert outbox.current().content_id == "first"


def test_manual_outbox_clear_marks_explicit_confirmation(tmp_path):
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    record = manual_ready_record(
        content_id="first",
        post_text="First post",
        source_url="https://example.com/first",
        checksum="checksum-1",
        now=datetime(2026, 9, 5, tzinfo=UTC),
    )
    outbox.prepare(record)

    outbox.clear(content_id="first", checksum="checksum-1")

    assert outbox.current().published is True
    assert outbox.pending() is None


def test_manual_outbox_archives_and_replaces_stale_pending_item(tmp_path):
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    now = datetime(2026, 9, 6, tzinfo=UTC)
    stale = manual_ready_record(
        content_id="stale",
        post_text="Stale post",
        source_url="https://example.com/stale",
        checksum="checksum-stale",
        now=datetime(2026, 9, 4, tzinfo=UTC),
    )
    fresh = manual_ready_record(
        content_id="fresh",
        post_text="Fresh post",
        source_url="https://example.com/fresh",
        checksum="checksum-fresh",
        now=now,
    )

    outbox.prepare(stale)

    assert outbox.prepare(fresh, now=now, stale_after_hours=24) == "replaced_stale"
    assert outbox.current().content_id == "fresh"
    archived = (tmp_path / "x_manual_ready_archive.jsonl").read_text(encoding="utf-8")
    assert '"content_id": "stale"' in archived


def test_manual_outbox_replaces_changed_copy_for_same_content_immediately(tmp_path):
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    first = manual_ready_record(
        content_id="same-content",
        post_text="Old copy",
        source_url="https://example.com/same",
        checksum="old-checksum",
        now=datetime(2026, 9, 6, tzinfo=UTC),
    )
    updated = manual_ready_record(
        content_id="same-content",
        post_text="Reviewed copy",
        source_url="https://example.com/same",
        checksum="new-checksum",
        now=datetime(2026, 9, 6, tzinfo=UTC),
    )

    outbox.prepare(first)
    assert outbox.prepare_many([updated]) == "written_batch"
    assert outbox.current().post_text == "Reviewed copy"
    archived = (tmp_path / "x_manual_ready_archive.jsonl").read_text(encoding="utf-8")
    assert '"checksum": "old-checksum"' in archived


def test_manual_outbox_keeps_two_ready_items_and_confirms_in_order(tmp_path):
    outbox = XManualOutbox(tmp_path / "x_manual_ready.json")
    first = manual_ready_record(content_id="first", post_text="First", source_url="https://example.com/1", checksum="one")
    second = manual_ready_record(content_id="second", post_text="Second", source_url="https://example.com/2", checksum="two")

    assert outbox.prepare_many([first, second]) == "written_batch"
    assert outbox.current().content_id == "first"
    payload = json.loads((tmp_path / "x_manual_ready.json").read_text(encoding="utf-8"))
    assert len(payload["items"]) == 2

    outbox.clear(content_id="first", checksum="one")
    assert outbox.current().content_id == "second"
