"""Re-render the current review packet with the Remotion motion renderer only."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config.settings import get_settings
from app.content_package.generator import build_content_packages
from app.video_render.factory import RENDER_READY, SHORT_FORM, render_package


TARGET_OPPORTUNITIES = {"filecoin-storage-provider", "golem-provider"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="render even when a Remotion result already exists")
    args = parser.parse_args()
    settings = get_settings()
    packages = [
        package
        for package in build_content_packages()
        if package.format == SHORT_FORM and package.opportunity_id in TARGET_OPPORTUNITIES
    ]
    print(f"rendering {len(packages)} Remotion review packages")
    failures = 0
    for package in packages:
        metadata_path = Path("data/local/video_render/metadata") / f"{package.package_id}.json"
        if not args.force and metadata_path.is_file():
            raw = metadata_path.read_text(encoding="utf-8")
            if '"render_engine": "remotion"' in raw and '"quality_version": "short-social-remotion-v2-source-led"' in raw and '"status": "RENDER_READY"' in raw:
                print(f"SKIP {package.package_id} already Remotion-ready")
                continue
        result = render_package(package, settings=settings)
        print(f"{result.status} {package.package_id} {result.reason or ''}".rstrip())
        failures += result.status != RENDER_READY
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
