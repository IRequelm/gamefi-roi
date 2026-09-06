"""CLI for local content-package narration and video rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config.settings import get_settings
from app.content_package.generator import build_content_packages
from app.video_render.factory import LONG_FORM, SHORT_FORM, RenderResult, render_package, validate_render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local review-only videos from READY content packages.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("content_id")
    build.add_argument("--format", choices=("short", "long"), default=None)
    build.add_argument("--dry-run", action="store_true")
    validate = commands.add_parser("validate")
    validate.add_argument("content_id")
    validate.add_argument("--format", choices=("short", "long"), default=None)
    commands.add_parser("report")
    args = parser.parse_args(argv)
    packages = build_content_packages()
    if args.command == "report":
        print(json.dumps(_report(packages), indent=2, sort_keys=True))
        return 0
    package = _find(packages, args.content_id, args.format)
    if package is None:
        print(json.dumps({"status": "NOT_READY", "reason": "READY content package not found"}, sort_keys=True))
        return 1
    if args.command == "validate":
        metadata_path = Path("data/local/video_render/metadata") / f"{package.package_id}.json"
        if not metadata_path.is_file():
            print(json.dumps({"content_id": package.source_inventory_item_id, "package_id": package.package_id, "status": "NOT_READY", "reason": "render metadata is missing"}, sort_keys=True))
            return 1
        result = RenderResult(**{key: value for key, value in json.loads(metadata_path.read_text(encoding="utf-8")).items() if key != "asset_checksums"})
        blockers = validate_render(result)
        print(json.dumps({"content_id": result.content_id, "package_id": result.package_id, "status": result.status, "blockers": blockers}, sort_keys=True))
        return 0 if not blockers else 1
    if args.dry_run:
        print(json.dumps({"content_id": package.source_inventory_item_id, "package_id": package.package_id, "format": package.format, "status": "READY_TO_RENDER"}, sort_keys=True))
        return 0
    result = render_package(package, settings=get_settings())
    print(json.dumps({key: value for key, value in result.__dict__.items() if key not in {"evidence_fingerprint"}}, indent=2, sort_keys=True))
    return 0 if result.status == "RENDER_READY" else 1


def _find(packages, content_id: str, requested_format: str | None):
    candidates = [package for package in packages if package.source_inventory_item_id == content_id or package.package_id == content_id]
    if requested_format:
        wanted = SHORT_FORM if requested_format == "short" else LONG_FORM
        candidates = [package for package in candidates if package.format == wanted]
    return sorted(candidates, key=lambda package: package.package_id)[0] if candidates else None


def _report(packages) -> dict[str, int]:
    metadata_dir = Path("data/local/video_render/metadata")
    results = []
    for path in sorted(metadata_dir.glob("package-*.json")):
        try:
            results.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    reason_counts: dict[str, int] = {}
    for result in results:
        blockers = _metadata_blockers(result)
        if blockers:
            reason = str(result.get("reason") or "unknown")
            if reason == "unknown":
                reason = blockers[0]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "renderable_packages": len(packages),
        "short_eligible": sum(package.format == SHORT_FORM for package in packages),
        "long_eligible": sum(package.format == LONG_FORM for package in packages),
        "rendered": len(results),
        "render_ready": sum(not _metadata_blockers(result) for result in results),
        "not_ready": sum(bool(_metadata_blockers(result)) for result in results),
        "reason_counts": reason_counts,
    }


def _metadata_blockers(result: dict) -> tuple[str, ...]:
    try:
        parsed = RenderResult(**{key: value for key, value in result.items() if key != "asset_checksums"})
        return validate_render(parsed)
    except (TypeError, ValueError):
        return ("render metadata is invalid",)


if __name__ == "__main__":
    raise SystemExit(main())
