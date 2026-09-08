from __future__ import annotations

import json
from pathlib import Path

from app.distribution.content_pack import ContentPackLite
from app.distribution.x_enrichment import XOfficialAccountRegistry, enrich_own_post, generate_fallback_card, hashtags_for_pack


ROOT = Path(__file__).resolve().parents[2]


def _pack():
    payload = json.loads((ROOT / "distribution/content_packs/learning_batch_001.json").read_text(encoding="utf-8"))
    return ContentPackLite.model_validate(payload["packs"][0])


def test_verified_handle_only_from_explicit_registry(tmp_path: Path):
    pack = _pack()
    registry = tmp_path / "accounts.json"
    registry.write_text(json.dumps({"accounts": [{"opportunity_id": pack.source.opportunity_id, "handle": "@OfficialApp", "official_source_url": "https://example.org/about", "verified": True}]}), encoding="utf-8")
    enriched = enrich_own_post(pack, pack.editorial.x_post, registry=XOfficialAccountRegistry(registry))
    assert enriched.official_handle == "@OfficialApp"
    # The canonical post may already consume the X limit; the verified handle
    # remains stored in enrichment metadata rather than being guessed or
    # forcing the source URL/claims out of the post.


def test_unverified_handle_is_omitted_and_hashtags_are_bounded(tmp_path: Path):
    pack = _pack()
    registry = tmp_path / "accounts.json"
    registry.write_text(json.dumps({"accounts": [{"opportunity_id": pack.source.opportunity_id, "handle": "@Guessed", "official_source_url": "https://example.org", "verified": False}]}), encoding="utf-8")
    enriched = enrich_own_post(pack, pack.editorial.x_post, registry=XOfficialAccountRegistry(registry))
    assert enriched.official_handle is None
    assert "@Guessed" not in enriched.final_copy
    assert len(hashtags_for_pack(pack)) <= 13


def test_missing_external_media_falls_back_to_verified_metadata(tmp_path: Path):
    pack = _pack()
    asset = generate_fallback_card(pack, tmp_path)
    text = Path(asset.path).read_text(encoding="utf-8")
    assert asset.kind == "verified_fallback_card"
    assert pack.facts.project_name in text
    assert pack.facts.major_catch[:20] in text
    assert "random-gameplay" not in text
