"""Read-only operational recovery evidence; never publishes or generates audio."""
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import get_settings
from app.publishing.elevenlabs import _load_metadata, _sha256_file
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.storage.database import create_database_engine, check_connectivity
from app.storage.history import HistoryRepository
from app.strategies.catalog import list_opportunities
from app.doctor.checks import check_migrations


def main():
    settings = get_settings()
    report = {"observed_at": datetime.now(UTC).isoformat()}
    report["taxonomy"] = dict(Counter(o.opportunity_type for o in list_opportunities()))
    assets = []
    paths = [p for root in ("data/local/video_render/narration", "data/local/youtube/narration") for p in Path(root).glob("*.json")]
    for path in paths:
        m = _load_metadata(path)
        if m:
            audio = Path(m.audio_path)
            assets.append({"content_id": m.content_id, "metadata_path": str(path), "script_fingerprint": m.script_fingerprint,
                           "checksum_valid": audio.is_file() and _sha256_file(audio) == m.audio_checksum,
                           "quality": m.narration_quality_status})
    report["narration"] = assets
    heartbeat = Path("data/local/distribution/worker_heartbeat.json")
    if heartbeat.exists():
        report["worker"] = json.loads(heartbeat.read_text())
        report["worker"]["age_seconds"] = (datetime.now(UTC)-datetime.fromisoformat(report["worker"]["updated_at"])).total_seconds()
    try:
        engine = create_database_engine(settings)
        check_connectivity(engine)
        report["migrations"] = check_migrations(settings, engine).__dict__
        history = HistoryRepository(engine)
        failures = history.list_failures()
        report["failure_clusters"] = [dict(strategy_id=k[0], error_type=k[1], message=k[2], count=v) for k,v in Counter((f.strategy_id,f.error_type,f.error_message) for f in failures).items()]
        report["snapshots"] = [{"strategy_id": s.strategy_id, "calculated_at": s.calculated_at.isoformat()} for s in history.latest_snapshots()]
        engine.dispose()
    except Exception as exc:
        report["database"] = {"status": "unavailable", "error_category": type(exc).__name__}
    publisher = YouTubePublisher(config=YouTubePublisherConfig.from_settings(settings))
    report["youtube"] = publisher.check_capabilities()
    if report["youtube"].get("channel_verified"):
        channels = publisher.service.channels().list(part="contentDetails", mine=True).execute()
        playlist = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        report["youtube_videos"] = []
        token = None
        while True:
            data = publisher.service.playlistItems().list(part="snippet,contentDetails", playlistId=playlist, maxResults=50, pageToken=token).execute()
            report["youtube_videos"].extend({"id": i["contentDetails"]["videoId"], "title": i["snippet"]["title"], "published_at": i["snippet"]["publishedAt"]} for i in data["items"])
            token = data.get("nextPageToken")
            if not token:
                break
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
