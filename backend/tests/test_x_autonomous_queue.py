from pathlib import Path
from datetime import UTC, datetime

from app.distribution.content_pack import ContentReadiness
from app.publishing.distribution_worker import XDailyCapState
from app.distribution.x_queue import load_x_queue


ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "distribution/publish_queue/x_publish_queue.json"
GRASS_ID = "x-grass-roi-unavailable-20260831"


def test_x_yellow_content_is_approval_gated_before_publication() -> None:
    queue = load_x_queue(QUEUE)
    item = queue.find(GRASS_ID)

    assert item.status is ContentReadiness.YELLOW
    assert item.approval_required is True
    assert item.approval_state.value == "awaiting_human_approval"
    assert item not in queue.publishable
    assert item in queue.awaiting_human_approval


def test_x_daily_caps_persist_across_worker_restarts(tmp_path: Path) -> None:
    path = tmp_path / "daily-cap.json"
    now = datetime(2026, 9, 15, 12, tzinfo=UTC)
    first = XDailyCapState(path)

    assert first.available("posts", 1, now=now)
    first.record("posts", now=now)
    first.record("retweets", now=now)
    first.record("retweets", now=now)

    restarted = XDailyCapState(path)
    assert not restarted.available("posts", 1, now=now)
    assert not restarted.available("retweets", 2, now=now)
