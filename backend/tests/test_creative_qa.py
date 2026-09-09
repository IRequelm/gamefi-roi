from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from dataclasses import replace

from app.content_package.generator import build_content_packages
from app.video_render.creative_qa import (
    ASSETS_READY,
    BLOCKED_MISSING_ASSETS,
    asset_plan,
    creative_preflight,
    frame_qa,
    hook_blockers,
)


def _package():
    return next(package for package in build_content_packages() if package.format == "SHORT_FORM" and package.content_family != "FINANCIAL_ROI")


def test_generic_intro_is_rejected_as_a_weak_hook():
    package = replace(_package(), hook="Start with the evidence behind this opportunity.")
    assert any("BLOCKED_WEAK_HOOK" in blocker for blocker in hook_blockers(package))


def test_category_hook_requires_a_real_product_asset(tmp_path: Path, monkeypatch):
    package = _package()
    monkeypatch.setenv("GAMEFI_SHORT_ASSET_ROOT", str(tmp_path))
    assert any(BLOCKED_MISSING_ASSETS in blocker for blocker in creative_preflight(package))
    asset_dir = tmp_path / (package.opportunity_id or "gamcryp")
    asset_dir.mkdir()
    (asset_dir / "official-product-ui.png").write_bytes(b"approved fixture" * 20)
    assert asset_plan(package).status == ASSETS_READY
    assert not any(BLOCKED_MISSING_ASSETS in blocker for blocker in creative_preflight(package))


def test_frame_qa_requires_five_distinct_extractable_frames(tmp_path: Path):
    video = tmp_path / "proof.mp4"
    video.write_bytes(b"video")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[0] == "ffprobe":
            return CompletedProcess(command, 0, stdout="10.0", stderr="")
        Path(command[-1]).write_bytes(bytes([len(calls)]) * (100 + len(calls)))
        return CompletedProcess(command, 0, stdout="", stderr="")

    result = frame_qa(video, tmp_path / "frames", runner=runner)
    assert result["status"] == "PASSED"
    assert len(result["frames"]) == 5
