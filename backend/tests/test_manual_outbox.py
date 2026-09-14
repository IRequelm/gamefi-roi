from __future__ import annotations

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
