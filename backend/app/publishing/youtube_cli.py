"""Operator CLI for GamCryp YouTube API publishing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.publishing.youtube import (
    YouTubePublisher,
    YouTubePublisherConfig,
    YouTubePublisherError,
    load_manifest,
    redact_sensitive_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operate the GamCryp YouTube Data API publisher.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("status", help="Check OAuth configuration and token state without mutating YouTube.")
    subcommands.add_parser("authorize", help="Run first-time Google OAuth and store a local refreshable token.")

    dry_run = subcommands.add_parser("dry-run", help="Validate a publish manifest without mutating YouTube.")
    dry_run.add_argument("--manifest", required=True, help="Path to a JSON publish manifest.")

    upload = subcommands.add_parser("upload", help="Upload a manifest video through the YouTube Data API.")
    upload.add_argument("--manifest", required=True, help="Path to a JSON publish manifest.")
    upload.add_argument(
        "--confirm-publish",
        action="store_true",
        help="Required for real upload operations. Use dry-run first.",
    )

    thumbnail = subcommands.add_parser("thumbnail", help="Set a custom thumbnail on an existing YouTube video.")
    thumbnail.add_argument("--video-id", required=True)
    thumbnail.add_argument("--image", required=True)
    thumbnail.add_argument("--dry-run", action="store_true")

    metadata = subcommands.add_parser("metadata", help="Update metadata on an existing YouTube video.")
    metadata.add_argument("--video-id", required=True)
    metadata.add_argument("--title")
    metadata.add_argument("--description")
    metadata.add_argument("--tag", action="append", dest="tags")
    metadata.add_argument("--privacy", choices=("private", "unlisted", "public"))
    metadata.add_argument("--publish-at", help="ISO-8601 scheduled publish timestamp with timezone.")
    metadata.add_argument("--category-id")
    metadata.add_argument("--confirm-update", action="store_true", help="Required for real metadata mutations.")

    verify = subcommands.add_parser("verify", help="Verify video upload/processing status.")
    verify.add_argument("--video-id", required=True)
    verify.add_argument("--thumbnail", action="store_true", help="Verify custom thumbnail state instead of video status.")

    args = parser.parse_args(argv)

    try:
        publisher = _publisher()
        if args.command == "status":
            _print_json(publisher.validate_auth_state().to_safe_dict())
            return 0
        if args.command == "authorize":
            _print_json(publisher.authorize_interactive().to_safe_dict())
            return 0
        if args.command == "dry-run":
            _print_json(publisher.dry_run_upload(load_manifest(Path(args.manifest))).to_safe_dict())
            return 0
        if args.command == "upload":
            if not args.confirm_publish:
                raise YouTubePublisherError("upload requires --confirm-publish after a successful dry-run")
            _print_json(publisher.upload_video(load_manifest(Path(args.manifest))).to_safe_dict())
            return 0
        if args.command == "thumbnail":
            _print_json(
                publisher.set_thumbnail(
                    video_id=args.video_id,
                    image_path=Path(args.image),
                    dry_run=bool(args.dry_run),
                ).to_safe_dict()
            )
            return 0
        if args.command == "metadata":
            if not args.confirm_update:
                raise YouTubePublisherError("metadata update requires --confirm-update")
            publish_at = _parse_datetime(args.publish_at) if args.publish_at else None
            _print_json(
                publisher.update_video_metadata(
                    video_id=args.video_id,
                    title=args.title,
                    description=args.description,
                    tags=args.tags,
                    privacy=args.privacy,
                    publish_at=publish_at,
                    category_id=args.category_id,
                ).to_safe_dict()
            )
            return 0
        if args.command == "verify":
            result = publisher.verify_thumbnail(args.video_id) if args.thumbnail else publisher.verify_video(args.video_id)
            _print_json(result.to_safe_dict())
            return 0
    except YouTubePublisherError as exc:
        _print_json({"status": "error", "error": redact_sensitive_text(str(exc))})
        return 1
    return 1


def _publisher() -> YouTubePublisher:
    settings = get_settings()
    return YouTubePublisher(config=YouTubePublisherConfig.from_settings(settings))


def _parse_datetime(value: str) -> Any:
    from datetime import datetime

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())