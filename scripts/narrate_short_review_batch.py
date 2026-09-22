"""Generate approved ElevenLabs narration and re-render the current Short review batch.

This is intentionally an operator-only command. It spends ElevenLabs credits
only when the caller passes ``--confirm-quality-approved``; without that flag
it performs a configuration/package dry-run and never contacts the provider.
"""

from __future__ import annotations

import argparse

from app.config.settings import get_settings
from app.content_package.generator import build_content_packages
from app.publishing.elevenlabs import ElevenLabsConfig
from app.video_render.factory import RENDER_READY, SHORT_FORM, render_package


TARGET_OPPORTUNITIES = {"filecoin-storage-provider", "golem-provider"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate approved ElevenLabs narration for the current Short review batch.")
    parser.add_argument("--confirm-quality-approved", action="store_true", help="Confirm the exact source-led renders passed human creative review before spending credits")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    settings = get_settings()
    config = ElevenLabsConfig.from_settings(settings)
    config.require_complete()
    packages = [
        package
        for package in build_content_packages()
        if package.format == SHORT_FORM and package.opportunity_id in TARGET_OPPORTUNITIES
    ][: max(0, args.limit)]
    print(f"selected {len(packages)} Short packages")
    if not args.confirm_quality_approved:
        print("DRY_RUN: no ElevenLabs request will be made; pass --confirm-quality-approved after human review")
        for package in packages:
            print(f"READY {package.package_id}")
        return 0

    failures = 0
    for package in packages:
        result = render_package(
            package,
            settings=settings,
            allow_narration_generation=True,
            creative_approval=True,
        )
        reused = bool(result.quality_metadata and result.quality_metadata.get("narration_reused"))
        print(f"{result.status} {package.package_id} audio={result.audio_mode} reused={reused} voice={result.voice_id or 'none'} {result.reason or ''}".rstrip())
        failures += result.status != RENDER_READY or result.audio_mode != "neural_voice"
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
