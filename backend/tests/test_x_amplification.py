from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.distribution.x_amplification import (
    AmplificationDecision,
    XAmplificationOutbox,
    XSourcePost,
    XSourceWhitelistEntry,
    classify_candidate,
)


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def _post(**updates):
    value = {
        "source_account": "OfficialSource",
        "source_verified": True,
        "source_type": "project_official",
        "original_url": "https://x.com/OfficialSource/status/12345",
        "post_id": "12345",
        "posted_at": (NOW - timedelta(hours=2)).isoformat(),
        "text": "GEODNET network update: new coverage is live.",
    }
    value.update(updates)
    return XSourcePost.model_validate(value)


def _whitelist():
    return {"officialsource": XSourceWhitelistEntry(source_account="OfficialSource", source_type="project_official", verified=True, official_source_url="https://geodnet.com")}


def test_verified_fresh_relevant_source_is_repost_now():
    result = classify_candidate(_post(), _whitelist(), now=NOW)
    assert result.decision == AmplificationDecision.REPOST_NOW
    assert result.recommendation == "REPOST"


def test_untrusted_or_stale_source_cannot_be_repost_now():
    unknown = classify_candidate(_post(source_account="Unknown"), _whitelist(), now=NOW)
    stale = classify_candidate(_post(posted_at=(NOW - timedelta(days=4)).isoformat()), _whitelist(), now=NOW)
    assert unknown.decision == AmplificationDecision.IGNORE
    assert stale.decision == AmplificationDecision.IGNORE


def test_duplicate_candidate_is_not_written_twice(tmp_path: Path):
    outbox = XAmplificationOutbox(tmp_path / "ready.json", tmp_path / "history.json")
    item = classify_candidate(_post(), _whitelist(), now=NOW)
    assert outbox.write([item]) == "written"
    assert outbox.write([item]) == "unchanged"
    assert len(outbox.current()) == 1


def test_unsafe_source_is_manual_review_not_automatic_repost():
    result = classify_candidate(_post(text="GEODNET giveaway: guaranteed 100x, buy now"), _whitelist(), now=NOW)
    assert result.decision == AmplificationDecision.MANUAL_REVIEW
    assert result.recommendation == "QUOTE"
