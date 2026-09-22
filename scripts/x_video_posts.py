"""Prepare or publish X posts paired with the exact rendered Short video.

The default command only writes a reviewable handoff. Publishing requires both
``--publish`` and ``--confirm-publish``. It never follows, likes, DMs, or
replies to users; growth comes from useful source-led posts and curated,
whitelisted reposts only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from app.content_package.generator import ContentPackage, build_content_packages
from app.distribution.x_publisher import XApiClient, XPublisherConfig, XPublisherError, XOAuthManager
from app.distribution.x_queue import x_weighted_character_count
from app.strategies.catalog import get_opportunity


DEFAULT_OUTBOX = Path("distribution/manual_outbox/x_video_posts.json")
VIDEO_ROOT = Path("data/local/video_render/short")
TARGET_OPPORTUNITIES = {"filecoin-storage-provider", "golem-provider"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pair current source-led Shorts with X video posts.")
    parser.add_argument("--publish", action="store_true", help="Upload video and create the X post")
    parser.add_argument("--confirm-publish", action="store_true", help="Confirm the external X publication")
    parser.add_argument("--limit", type=int, default=2, help="Maximum posts in this run; default follows the daily cap")
    parser.add_argument("--outbox", type=Path, default=DEFAULT_OUTBOX)
    args = parser.parse_args()
    load_dotenv(dotenv_path=Path(".env"), override=False, encoding="utf-8-sig")
    packages = [
        package
        for package in build_content_packages()
        if package.format == "SHORT_FORM" and package.opportunity_id in TARGET_OPPORTUNITIES
    ]
    records = [_record_for(package) for package in packages]
    args.outbox.parent.mkdir(parents=True, exist_ok=True)
    args.outbox.write_text(json.dumps({"generated_at": _now(), "items": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"prepared {len(records)} video-matched X posts at {args.outbox}")
    if not args.publish:
        print("DRY_RUN: no X API call; use --publish --confirm-publish after reviewing the outbox")
        return 0
    if not args.confirm_publish:
        print("BLOCKED: --confirm-publish is required for external X publication")
        return 1
    config = XPublisherConfig.from_environment()
    client = XApiClient(XOAuthManager(config))
    failures = 0
    published = 0
    for record in records:
        if published >= max(0, args.limit):
            break
        if record["status"] != "ready":
            print(f"BLOCKED {record['package_id']} {record['status_reason']}")
            failures += 1
            continue
        try:
            media_id = client.upload_media(Path(record["video_path"]))
            post_id = client.create_post(record["post_text"], media_id=media_id)
            record["status"] = "published"
            record["post_id"] = post_id
            record["media_id"] = media_id
            published += 1
            print(f"PUBLISHED {record['package_id']} post_id={post_id}")
        except XPublisherError as exc:
            record["status"] = "failed"
            record["status_reason"] = str(exc)
            failures += 1
            print(f"FAILED {record['package_id']} {exc}")
    args.outbox.write_text(json.dumps({"generated_at": _now(), "items": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failures else 0


def _record_for(package: ContentPackage) -> dict[str, object]:
    video_path = VIDEO_ROOT / f"{package.package_id}.mp4"
    metadata_path = Path("data/local/video_render/metadata") / f"{package.package_id}.json"
    metadata = _read_json(metadata_path)
    quality = metadata.get("quality_metadata") if isinstance(metadata.get("quality_metadata"), dict) else {}
    source = package.required_source_references[0]["url"] if package.required_source_references else package.canonical_source_url
    title = package.title_candidates[0] if package.title_candidates else package.opportunity_id or "GamCryp review"
    point = next((str(item.get("text", "")).strip() for item in package.factual_talking_points if item.get("text")), "Review the official source before acting.")
    opportunity = get_opportunity(package.opportunity_id) if package.opportunity_id else None
    tag = "#GameFi" if opportunity and opportunity.opportunity_type == "GAME" else "#DePIN"
    post_text = f"{title}\n\n{package.hook}\n\n{point}\n\nSource: {source}\n\n#GamCryp {tag}"
    if x_weighted_character_count(post_text) > 280:
        post_text = f"{title}\n\n{package.hook}\n\nSource: {source}\n\n#GamCryp {tag}"
    if x_weighted_character_count(post_text) > 280:
        post_text = f"{title}\n\nSource: {source}\n\n#GamCryp {tag}"
    status = "ready"
    status_reason = ""
    if not video_path.is_file():
        status, status_reason = "blocked", "rendered video is missing"
    elif metadata.get("status") != "RENDER_READY":
        status, status_reason = "blocked", "render metadata is not RENDER_READY"
    elif quality.get("frame_qa", {}).get("status") != "PASSED":
        status, status_reason = "blocked", "frame QA is not PASSED"
    elif quality.get("audio_mode") != "neural_voice":
        status, status_reason = "blocked", "paired X publishing waits for approved ElevenLabs narration"
    return {
        "package_id": package.package_id,
        "video_path": str(video_path),
        "video_checksum": _sha256(video_path) if video_path.is_file() else None,
        "post_text": post_text,
        "weighted_character_count": x_weighted_character_count(post_text),
        "source_url": source,
        "status": status,
        "status_reason": status_reason,
        "prepared_at": _now(),
    }


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
