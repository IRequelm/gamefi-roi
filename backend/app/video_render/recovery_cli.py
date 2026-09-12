"""Render an unchanged, previously recorded script with verified existing audio.

No publishing, no paid narration. Current QA is enforced even for legacy audio.
"""
import json
from dataclasses import replace
from pathlib import Path
from app.config.settings import get_settings
from app.content_package.generator import build_content_packages
from app.publishing.elevenlabs import reuse_existing_narration
from app.video_render.factory import render_package, _script_for


def main():
    package = next(p for p in build_content_packages() if p.package_id == "package-short_form-depin_setup-akash-provider")
    audio = reuse_existing_narration(package.source_inventory_item_id, Path("data/local/video_render/narration"))
    if audio is None:
        print(json.dumps({"state": "BLOCKED_NARRATION", "reason": "Verified legacy audio missing"}))
        return 1
    body = " ".join(p["text"] for p in package.factual_talking_points)
    original = audio.metadata.source_script
    if original.count(body) != 1:
        print(json.dumps({"state": "BLOCKED_PACKAGE", "reason": "Recorded factual body differs from current evidence"}))
        return 1
    hook, cta = original.split(body)
    package = replace(package, hook=hook.strip(), cta=cta.strip())
    if _script_for(package) != original:
        raise ValueError("Original spoken script must match exactly")
    def prohibit_generation(*args, **kwargs):
        raise AssertionError("Recovery must never generate narration")
    result = render_package(package, settings=get_settings(), root=Path("data/local/recovery/render"), narration_provider_factory=prohibit_generation)
    print(json.dumps({"package_id": package.package_id, "state": result.status, "reason": result.reason,
                      "narration_checksum": audio.metadata.audio_checksum, "narration_reused": (result.quality_metadata or {}).get("narration_reused"),
                      "frame_qa": (result.quality_metadata or {}).get("frame_qa"), "video_path": result.video_path,
                      "paid_generation": False, "upload_performed": False}, indent=2))
    return 0 if result.status == "RENDER_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
