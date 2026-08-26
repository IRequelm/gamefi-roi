from __future__ import annotations

import json
import re
from datetime import timedelta
from html.parser import HTMLParser
from xml.etree import ElementTree

import httpx
import pytest

from app.search.canonical import canonical_page_inventory
from app.search.indexnow import INDEXNOW_ENDPOINT, IndexNowClient, IndexNowError
from app.storage.monetization import MonetizationRepository
from app.strategies.catalog import list_opportunities
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_api_v1 import NOW, _seed_snapshots_and_scores, _seeded_client


def test_strategy_page_contains_meaningful_server_rendered_content(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-strategy.db")

    response = client.get(f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}")

    assert response.status_code == 200
    html = response.text
    assert "<title>" in html
    assert DFK_CJEWEL_MAX_LOCK_V1.name in html
    assert "30-day ROI" in html
    assert "Risk and Confidence" in html
    assert f'<link rel="canonical" href="http://localhost:8000/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}">' in html
    assert '<a class="button cta" href="/go/defi-kingdoms-play"' in html
    assert 'data-analytics-link="outbound"' in html
    assert '"@type":"WebPage"' in html


def test_unavailable_points_roi_is_crawlable_and_not_zero(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-unavailable.db")

    response = client.get("/opportunities/grass")

    assert response.status_code == 200
    html = response.text
    assert "Grass" in html
    assert "ROI not measurable yet" in html
    assert "Points cannot currently be converted to cash reliably" in html
    assert "DePIN / Nodes" in html
    assert "DEPIN_NODE" not in html
    assert "$0" not in html
    assert "Points" in html or "POINTS" in html


def test_metadata_uses_configurable_canonical_host(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://gamcryp.example")
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-host.db")

    response = client.get("/rankings")

    assert response.status_code == 200
    html = response.text
    assert '<link rel="canonical" href="https://gamcryp.example/rankings">' in html
    assert '<meta property="og:url" content="https://gamcryp.example/rankings">' in html
    assert '<meta name="twitter:title" content="Web3 ROI Rankings, Risk &amp; Confidence | GamCryp">' in html


def test_query_permutations_are_noindex_and_canonicalized(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-query.db")

    response = client.get("/rankings?capital_max=25")

    assert response.status_code == 200
    assert '<meta name="robots" content="noindex,follow">' in response.text
    assert '<link rel="canonical" href="http://localhost:8000/rankings">' in response.text


def test_curated_landing_page_is_indexable(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-curated.db")

    response = client.get("/rankings/under-25")

    assert response.status_code == 200
    assert '<meta name="robots" content="index,follow">' in response.text
    assert "Web3 strategies under $25 capital" in response.text
    assert SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.name in response.text


def test_robots_disallows_api_go_and_query_traps_without_blocking_ai_search_bots(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-robots.db")

    response = client.get("/robots.txt")

    assert response.status_code == 200
    body = response.text
    assert "Disallow: /api/" in body
    assert "Disallow: /go/" in body
    assert "Disallow: /*?*" in body
    assert "Sitemap: http://localhost:8000/sitemap.xml" in body
    assert "User-agent: OAI-SearchBot\nDisallow: /" not in body
    assert "User-agent: PerplexityBot\nDisallow: /" not in body
    assert "User-agent: Googlebot\nDisallow: /" not in body
    assert "User-agent: Bingbot\nDisallow: /" not in body


def test_sitemap_contains_only_absolute_canonical_public_urls(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-sitemap.db")

    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    root = ElementTree.fromstring(response.text)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [item.text for item in root.findall(".//sm:loc", namespace)]
    assert "http://localhost:8000/" in locs
    assert "http://localhost:8000/rankings" in locs
    assert f"http://localhost:8000/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}" in locs
    assert all(url is not None and url.startswith("http://localhost:8000/") for url in locs)
    assert all("/api/" not in url and "/go/" not in url and "?" not in url for url in locs if url is not None)
    lastmods = [item.text for item in root.findall(".//sm:lastmod", namespace)]
    assert "2026-08-16" in lastmods


def test_json_ld_payloads_are_parseable_and_truthful(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-jsonld.db")

    response = client.get("/")

    payloads = _json_ld_payloads(response.text)
    types = {payload["@type"] for payload in payloads}
    assert {"Organization", "WebSite", "WebPage"} <= types
    assert "Product" not in types
    assert "Review" not in types
    assert any(payload.get("url") == "http://localhost:8000" for payload in payloads)


def test_public_links_are_crawlable_anchors_for_all_opportunities(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-links.db")

    response = client.get("/opportunities")

    anchors = set(_anchors(response.text))
    expected = {f"/opportunities/{opportunity.opportunity_id}" for opportunity in list_opportunities()}
    assert expected <= anchors
    assert "/rankings" in _anchors(client.get("/").text)
    assert "/methodology" in _anchors(client.get("/").text)


def test_go_redirect_is_disallowed_and_not_indexable_public_content(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-go.db")

    robots = client.get("/robots.txt").text
    response = client.get("/go/defi-kingdoms-play", follow_redirects=False)

    assert "Disallow: /go/" in robots
    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert response.headers["location"] == "https://defikingdoms.com/"


def test_inbound_acquisition_attribution_is_privacy_minimal(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-attribution.db")

    response = client.get(
        "/?utm_source=chatgpt.com&utm_medium=search&utm_campaign=g16",
        headers={"referer": "https://chatgpt.com/share/test", "x-gamcryp-session": "coarse-1"},
    )

    assert response.status_code == 200
    visits = MonetizationRepository(engine).landing_visits(landing_path="/")
    assert len(visits) == 1
    assert visits[0].channel == "chatgpt"
    assert visits[0].utm_source == "chatgpt.com"
    assert visits[0].utm_medium == "search"
    assert visits[0].utm_campaign == "g16"
    assert visits[0].referrer_domain == "chatgpt.com"
    assert visits[0].coarse_session_id == "coarse-1"


def test_inbound_events_do_not_change_organic_ranking_or_scores(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-integrity.db")
    before = client.get("/api/v1/rankings").json()["items"]

    client.get("/rankings?utm_source=reddit&utm_campaign=launch")
    client.get("/opportunities/grass?utm_source=perplexity")

    after = client.get("/api/v1/rankings").json()["items"]
    assert _organic_signature(before) == _organic_signature(after)
    assert len(MonetizationRepository(engine).landing_visits()) == 2


def test_indexnow_filters_to_canonical_public_urls_and_posts_official_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://gamcryp.example")
    monkeypatch.setenv("GAMEFI_INDEXNOW_KEY", "indexnow-key")
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-indexnow.db")
    settings = client.app.dependency_overrides  # keeps client alive while settings cache is seeded
    assert settings == {}
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append({"url": str(request.url), "json": json.loads(request.content.decode("utf-8"))})
        return httpx.Response(202)

    from app.config.settings import get_settings

    result = IndexNowClient(
        settings=get_settings(),
        engine=engine,
        transport=httpx.MockTransport(handler),
    ).submit_urls(
        [
            "https://gamcryp.example/",
            f"https://gamcryp.example/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
            "https://gamcryp.example/go/defi-kingdoms-play",
            "https://other.example/rankings",
            "https://gamcryp.example/rankings?capital_max=25",
        ]
    )

    assert result.status_code == 202
    assert result.submitted_urls == (
        "https://gamcryp.example/",
        f"https://gamcryp.example/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}",
    )
    assert captured[0]["url"] == INDEXNOW_ENDPOINT
    assert captured[0]["json"]["host"] == "gamcryp.example"
    assert captured[0]["json"]["key"] == "indexnow-key"
    assert captured[0]["json"]["urlList"] == list(result.submitted_urls)


def test_indexnow_failure_redacts_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GAMEFI_PUBLIC_BASE_URL", "https://gamcryp.example")
    monkeypatch.setenv("GAMEFI_INDEXNOW_KEY", "secret-indexnow-key")
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-indexnow-failure.db")
    assert client.get("/").status_code == 200

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="secret-indexnow-key rejected")

    from app.config.settings import get_settings

    with pytest.raises(IndexNowError) as exc:
        IndexNowClient(
            settings=get_settings(),
            engine=engine,
            transport=httpx.MockTransport(handler),
            max_retries=0,
        ).submit_urls(["https://gamcryp.example/"])

    assert "secret-indexnow-key" not in str(exc.value)


def test_canonical_inventory_has_no_api_go_or_query_urls(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-inventory.db")
    assert client.get("/").status_code == 200

    paths = [page.path for page in canonical_page_inventory(engine)]

    assert "/" in paths
    assert "/rankings" in paths
    assert "/rankings/gamefi" in paths
    assert all(not path.startswith(("/api", "/go")) and "?" not in path for path in paths)


def test_history_lastmod_updates_with_new_snapshot_window(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-lastmod.db")
    _seed_snapshots_and_scores(engine, calculated_at=NOW + timedelta(hours=2))

    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "2026-08-16" in response.text
    assert f"strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}" in response.text
    history = client.get(f"/api/v1/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}/history").json()["items"]
    assert len(history) == 2


def _json_ld_payloads(html: str) -> list[dict]:
    scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.DOTALL)
    return [json.loads(script) for script in scripts]


def _anchors(html: str) -> list[str]:
    parser = _AnchorParser()
    parser.feed(html)
    return parser.hrefs


def _organic_signature(items: list[dict]) -> list[tuple]:
    return [
        (
            item["strategy"]["strategy_id"],
            item["latest_snapshot"]["roi"]["roi_total_30d"]["value"],
            item["latest_snapshot"]["confidence"]["score"],
            item["latest_snapshot"]["risk"]["score"],
        )
        for item in items
    ]


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)
