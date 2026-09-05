from __future__ import annotations

from test_api_v1 import _seeded_client


def test_guidance_is_optional_and_seeded_only_for_evidence_backed_opportunities(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "guidance-api.db")

    dfk = client.get("/api/v1/opportunities/defi-kingdoms").json()
    storj = client.get("/api/v1/opportunities/storj-storage-node").json()
    grass = client.get("/api/v1/opportunities/grass").json()

    assert set(dfk["guidance"]) == {"how_to_start", "what_you_need", "how_you_earn", "how_to_exit_or_claim"}
    assert all(dfk["guidance"].values())
    assert all(storj["guidance"].values())
    assert grass["guidance"] is None


def test_server_opportunity_detail_renders_guidance_without_null_placeholders(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "guidance-web.db")

    for opportunity_id in ("defi-kingdoms", "storj-storage-node"):
        html = client.get(f"/opportunities/{opportunity_id}").text
        assert "How it works" in html
        assert all(label in html for label in ("How to start", "What you need", "How you earn", "How to claim or exit"))
        assert "None" not in html
        assert "undefined" not in html

    assert "How it works" not in client.get("/opportunities/grass").text
