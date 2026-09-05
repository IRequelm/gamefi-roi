"""Operator CLI for local ElevenLabs narration generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.config.settings import get_settings
from app.publishing.elevenlabs import ElevenLabsConfig, ElevenLabsError, ElevenLabsNarrationProvider
from app.publishing.youtube import YouTubePublisher, YouTubePublisherConfig
from app.publishing.youtube_distribution import YouTubeDistributionConfig, YouTubeDistributionPublisher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate fail-closed ElevenLabs narration assets.")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Generate or reuse one validated narration asset.")
    generate.add_argument("content_id")
    generate.add_argument("--dry-run", action="store_true", help="Validate configuration and script without an API request.")
    args = parser.parse_args(argv)
    try:
        settings = get_settings()
        distribution = _distribution(settings)
        queue, packs = distribution._load_context()
        item = queue.find(args.content_id)
        pack = next(pack for pack in packs if pack.content_id == args.content_id)
        blockers = distribution._package_blockers(item, pack)
        if blockers:
            raise ElevenLabsError("Narration source validation failed: " + "; ".join(blockers))
        if item.status.value == "RED":
            raise ElevenLabsError("RED content cannot generate a publishable narration asset")
        config = ElevenLabsConfig.from_settings(settings)
        if args.dry_run:
            config.require_complete()
            result = {"content_id": item.content_id, "status": "ready", "script_fingerprint": _fingerprint(item.short_script), "dry_run": True}
        else:
            result = ElevenLabsNarrationProvider(config).generate(content_id=item.content_id, script=item.short_script).safe_dict()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ElevenLabsError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "NOT_READY", "error": str(exc)}, sort_keys=True))
        return 1


def _distribution(settings) -> YouTubeDistributionPublisher:
    publisher = YouTubePublisher(config=YouTubePublisherConfig.from_settings(settings))
    return YouTubeDistributionPublisher(
        publisher,
        config=YouTubeDistributionConfig(
            content_pack_file=Path(settings.youtube_content_pack_file),
            queue_file=Path(settings.youtube_queue_file),
            approval_file=Path(settings.youtube_approval_file),
        ),
    )


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
