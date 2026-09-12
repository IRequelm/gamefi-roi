"""Operator CLI for GamCryp YouTube API publishing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.publishing.youtube_distribution import (
    YouTubeDistributionConfig,
    YouTubeDistributionPublisher,
)
from app.publishing.youtube import (
    YouTubePublisher,
    YouTubePublisherConfig,
    YouTubePublisherError,
    redact_sensitive_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operate the GamCryp YouTube Data API publisher.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("status", help="Check OAuth configuration and token state without mutating YouTube.")
    subcommands.add_parser("reconcile-state", help="Reconcile local upload state against the authenticated channel.")
    subcommands.add_parser("authorize", help="Run first-time Google OAuth and store a local refreshable token.")
    subcommands.add_parser("queue", help="Show the current YouTube publication queue.")
    subcommands.add_parser("rebuild-queue", help="Rebuild the YouTube queue from canonical Content Packs.")

    preview = subcommands.add_parser("preview", help="Preview current package, asset, and approval gates.")
    _add_package_asset_arguments(preview, require_video=False)

    approve = subcommands.add_parser("approve", help="Approve an exact YELLOW package and creative checksum.")
    _add_package_asset_arguments(approve, require_video=True)

    revoke = subcommands.add_parser("revoke", help="Revoke a prior YELLOW creative approval.")
    revoke.add_argument("content_id")

    dry_run = subcommands.add_parser("dry-run", help="Validate a queued package without mutating YouTube.")
    _add_package_asset_arguments(dry_run, require_video=True)

    upload = subcommands.add_parser("upload", help="Upload an approved queued package through YouTube Data API.")
    _add_package_asset_arguments(upload, require_video=True)
    upload.add_argument(
        "--confirm-publish",
        action="store_true",
        help="Required for real upload operations. Use dry-run first.",
    )
    upload.add_argument("--privacy", choices=("private", "unlisted", "public"), default="private")
    upload.add_argument("--category-id", default=None)
    upload.add_argument("--made-for-kids", choices=("true", "false"), default="false")

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
        distribution = _distribution_publisher(publisher)
        if args.command == "status":
            capability = publisher.check_capabilities()
            _print_json(capability)
            return 0 if capability["upload_scope_verified"] else 1
        if args.command == "reconcile-state":
            reconciliation = publisher.reconcile_local_state()
            from app.publishing.short_youtube_handoff import reconcile_handoff_state
            reconciliation["handoff_marked_ambiguous"] = reconcile_handoff_state(set(reconciliation["verified"]))
            _print_json(reconciliation)
            return 0
        if args.command == "authorize":
            _print_json(publisher.authorize_interactive().to_safe_dict())
            return 0
        if args.command == "queue":
            _print_json(distribution.queue_summary())
            return 0
        if args.command == "rebuild-queue":
            _print_json(distribution.rebuild_queue().model_dump(mode="json"))
            return 0
        if args.command == "preview":
            _print_json(
                distribution.preview(
                    args.content_id,
                    video_path=Path(args.video) if args.video else None,
                    thumbnail_path=Path(args.thumbnail) if args.thumbnail else None,
                ).model_dump(mode="json")
            )
            return 0
        if args.command == "approve":
            _print_json(
                distribution.approve(
                    args.content_id,
                    video_path=Path(args.video),
                    thumbnail_path=Path(args.thumbnail) if args.thumbnail else None,
                ).model_dump(mode="json")
            )
            return 0
        if args.command == "revoke":
            _print_json(distribution.revoke(args.content_id).model_dump(mode="json"))
            return 0
        if args.command == "dry-run":
            _print_json(
                distribution.dry_run(
                    args.content_id,
                    video_path=Path(args.video),
                    thumbnail_path=Path(args.thumbnail) if args.thumbnail else None,
                ).to_safe_dict()
            )
            return 0
        if args.command == "upload":
            _print_json(
                distribution.upload(
                    args.content_id,
                    video_path=Path(args.video),
                    thumbnail_path=Path(args.thumbnail) if args.thumbnail else None,
                    confirm_publish=bool(args.confirm_publish),
                    privacy=args.privacy,
                    category_id=args.category_id,
                    made_for_kids=args.made_for_kids == "true",
                ).to_safe_dict()
            )
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


def _distribution_publisher(publisher: YouTubePublisher) -> YouTubeDistributionPublisher:
    settings = get_settings()
    return YouTubeDistributionPublisher(
        publisher,
        config=YouTubeDistributionConfig(
            content_pack_file=Path(settings.youtube_content_pack_file),
            queue_file=Path(settings.youtube_queue_file),
            approval_file=Path(settings.youtube_approval_file),
        ),
    )


def _add_package_asset_arguments(parser: argparse.ArgumentParser, *, require_video: bool) -> None:
    parser.add_argument("content_id")
    parser.add_argument("--video", required=require_video, help="Rendered video file path.")
    parser.add_argument("--thumbnail", help="Optional custom thumbnail file path.")


def _parse_datetime(value: str) -> Any:
    from datetime import datetime

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
