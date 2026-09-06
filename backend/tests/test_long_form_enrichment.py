from __future__ import annotations

import json
from pathlib import Path

from app.content_enrichment.long_form import build_long_form_enrichment, write_long_form_enrichment


def test_enrichment_selects_thirty_five_deterministic_candidates_without_fabrication() -> None:
    first = build_long_form_enrichment()
    second = build_long_form_enrichment()

    assert len(first) == 35
    assert [item.opportunity_id for item in first] == [item.opportunity_id for item in second]
    assert all(item.canonical_source_set for item in first)
    assert all(item.word_budget_estimate >= 0 for item in first)
    assert all(not item.long_form_eligible for item in first)


def test_enrichment_artifact_has_section_level_evidence_and_truthful_summary(tmp_path: Path) -> None:
    path = tmp_path / "long-form-enrichment.json"
    payload = write_long_form_enrichment(path)
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert payload["summary"] == {"candidate_count": 35, "eligible_count": 0, "blocked_count": 35}
    assert loaded["schema_version"] == "long-form-enrichment-v1"
    assert all("sections" in candidate and "eligibility_reasons" in candidate for candidate in loaded["candidates"])
