from __future__ import annotations

import json
import re
from datetime import timedelta
from html.parser import HTMLParser
from xml.etree import ElementTree

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
import pytest

from app.search.canonical import canonical_page_inventory
from app.search.indexnow import INDEXNOW_ENDPOINT, IndexNowClient, IndexNowError
from app.storage.models import StrategySnapshotRecord
from app.storage.monetization import MonetizationRepository
from app.strategies.catalog import list_opportunities
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from app.web.seo import format_datetime
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
    assert 'data-ai-answer-block="true"' in html
    assert "Quick strategy summary" in html
    assert "Plain-language summary" in html
    assert "Expected return" in html
    assert "High-risk strategy. Opening the project is not a recommendation; review the assumptions first." in html
    assert "Technical snapshot details" in html
    assert "Aug 16, 2026 12:00 UTC" in html
    assert "Estimated gross earnings/day" in html
    assert "Required time/effort" in html
    assert "Major assumptions" in html
    assert f'<link rel="canonical" href="https://gamcryp.com/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}">' in html
    assert '<a class="button cta" href="/go/defi-kingdoms-play" target="_blank" rel="noopener noreferrer"' in html
    assert ">Open project" in html
    assert 'data-analytics-link="outbound"' in html
    assert '"@type":"WebPage"' in html


def test_methodology_page_explains_modeling_and_trust_boundaries(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-methodology.db")

    response = client.get("/methodology")

    assert response.status_code == 200
    html = response.text
    assert "Modeled ROI" in html
    assert "ROI unavailable" in html
    assert "does not invent a financial ROI number" in html
    assert "Risk describes" in html
    assert "Confidence describes" in html
    assert "Freshness describes" in html
    assert "Commercial independence" in html
    assert "do not affect ROI, Risk, Confidence, or organic ranking" in html
    assert "not investment advice" in html
    assert "None" not in html
    assert "undefined" not in html


def test_server_timestamp_formatter_uses_readable_utc_without_fractional_noise() -> None:
    assert format_datetime("2026-08-16T12:00:00.000000+00:00") == "Aug 16, 2026 12:00 UTC"
    assert format_datetime("2026-08-16T12:00:00Z") == "Aug 16, 2026 12:00 UTC"


def test_server_rendered_external_links_open_new_tab_and_internal_links_stay_same_tab(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-link-behavior.db")

    opportunity_html = client.get("/opportunities/grass").text
    strategy_html = client.get(f"/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}").text
    html = opportunity_html + strategy_html

    external_anchors = re.findall(r'<a\b[^>]*href="https?://[^"]+"[^>]*>', html)
    assert external_anchors
    for anchor in external_anchors:
        assert 'target="_blank"' in anchor
        assert 'rel="noopener noreferrer"' in anchor

    assert '<a href="https://www.grass.io/terms-and-conditions/" target="_blank" rel="noopener noreferrer">' in opportunity_html
    assert '<a class="button cta" href="/go/defi-kingdoms-play" target="_blank" rel="noopener noreferrer"' in strategy_html
    assert '<a class="secondary-button" href="/opportunities/defi-kingdoms">Parent opportunity</a>' in strategy_html
    for anchor in re.findall(r'<a\b[^>]*href="/(?!go/)[^"]+"[^>]*>', html):
        assert 'target="_blank"' not in anchor


def test_unavailable_points_roi_is_crawlable_and_not_zero(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-unavailable.db")

    response = client.get("/opportunities/grass")

    assert response.status_code == 200
    html = response.text
    assert "Grass" in html
    assert "ROI not measurable yet" in html
    assert "Points cannot currently be converted to cash reliably" in html
    assert "Quick opportunity summary" in html
    assert "Value route" in html
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
    assert '<link rel="canonical" href="https://gamcryp.com/rankings">' in response.text


def test_curated_landing_page_is_indexable(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-curated.db")

    response = client.get("/rankings/under-25")

    assert response.status_code == 200
    assert '<meta name="robots" content="index,follow">' in response.text
    assert "Web3 strategies under $25 capital" in response.text
    assert "Quick comparison" in response.text
    assert "Evidence-linked" in response.text
    assert SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1.name in response.text


def test_best_passive_gamefi_landing_page_is_publishable(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-passive-gamefi.db")

    response = client.get("/rankings/best-passive-gamefi")
    paths = [page.path for page in canonical_page_inventory(engine)]

    assert response.status_code == 200
    html = response.text
    assert '<meta name="robots" content="index,follow">' in html
    assert "Best passive GameFi ROI strategies" in html
    assert "Quick comparison" in html
    assert DFK_CJEWEL_MAX_LOCK_V1.name in html
    assert FARMERS_WORLD_AXE_WOOD_V1.name not in html
    assert "/rankings/best-passive-gamefi" in paths


def test_curated_ranking_pages_read_latest_snapshot_data(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-snapshot-source.db")
    with Session(engine) as session:
        record = session.scalar(
            select(StrategySnapshotRecord).where(
                StrategySnapshotRecord.strategy_id == DFK_CJEWEL_MAX_LOCK_V1.strategy_id
            )
        )
        assert record is not None
        capital = dict(record.capital_metrics_json)
        capital["total_capital"] = {"amount": "777.77", "currency": "USD"}
        record.capital_metrics_json = capital
        roi_outputs = dict(record.roi_outputs_json)
        roi_total_30d = dict(roi_outputs["roi_total_30d"])
        roi_total_30d["value"] = "0.1234"
        roi_outputs["roi_total_30d"] = roi_total_30d
        record.roi_outputs_json = roi_outputs
        session.commit()

    response = client.get("/rankings/best-passive-gamefi")

    assert response.status_code == 200
    assert 'title="777.77 USD"' in response.text
    assert "12.34%" in response.text


def test_itemlist_json_ld_matches_visible_ranking_order(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-itemlist.db")

    response = client.get("/rankings/gamefi-under-100")

    assert response.status_code == 200
    visible_strategy_ids = _visible_strategy_ids(response.text)
    payloads = _json_ld_payloads(response.text)
    itemlist = next(payload for payload in payloads if payload.get("@type") == "ItemList")
    elements = itemlist["itemListElement"]

    assert itemlist["numberOfItems"] == len(visible_strategy_ids)
    assert [element["position"] for element in elements] == list(range(1, len(elements) + 1))
    assert [element["url"] for element in elements] == [
        f"https://gamcryp.com/strategies/{strategy_id}" for strategy_id in visible_strategy_ids
    ]
    visible_entries = json.dumps(itemlist["itemListElement"])
    assert "250.00" not in visible_entries
    assert "$" not in visible_entries


def test_depin_curated_pages_publish_only_when_authoritative_data_qualifies(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-thin-pages.db")
    published_slugs = (
        "best-depin-under-100",
        "pc-depin",
        "no-hardware-depin",
    )
    blocked_slugs = ("phone-depin",)

    sitemap = client.get("/sitemap.xml").text
    inventory_paths = {page.path for page in canonical_page_inventory(engine)}

    for slug in published_slugs:
        response = client.get(f"/rankings/{slug}")
        assert response.status_code == 200
        assert '<meta name="robots" content="index,follow">' in response.text
        assert "Quick comparison" in response.text
        assert f"/rankings/{slug}" in inventory_paths
        assert f"/rankings/{slug}" in sitemap

    for slug in blocked_slugs:
        assert client.get(f"/rankings/{slug}").status_code == 404
        assert f"/rankings/{slug}" not in inventory_paths
        assert f"/rankings/{slug}" not in sitemap

def test_robots_disallows_api_go_and_query_traps_without_blocking_ai_search_bots(monkeypatch, tmp_path) -> None:
    client, _engine = _seeded_client(monkeypatch, tmp_path, "seo-robots.db")

    response = client.get("/robots.txt")

    assert response.status_code == 200
    body = response.text
    assert "Disallow: /api/" in body
    assert "Disallow: /go/" in body
    assert "Disallow: /*?*" in body
    assert "Sitemap: https://gamcryp.com/sitemap.xml" in body
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
    assert "https://gamcryp.com/" in locs
    assert "https://gamcryp.com/rankings" in locs
    assert f"https://gamcryp.com/strategies/{DFK_CJEWEL_MAX_LOCK_V1.strategy_id}" in locs
    assert all(url is not None and url.startswith("https://gamcryp.com/") for url in locs)
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
    assert "Dataset" not in types
    assert "ItemList" not in types
    assert any(payload.get("url") == "https://gamcryp.com" for payload in payloads)


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


def test_direct_landing_visit_is_recorded_without_user_tracking(monkeypatch, tmp_path) -> None:
    client, engine = _seeded_client(monkeypatch, tmp_path, "seo-direct-attribution.db")

    response = client.get("/")

    assert response.status_code == 200
    visits = MonetizationRepository(engine).landing_visits(landing_path="/")
    assert len(visits) == 1
    assert visits[0].channel == "direct"
    assert visits[0].utm_source is None
    assert visits[0].referrer_domain is None
    assert visits[0].coarse_session_id is None


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
    assert "/rankings/gamefi-under-100" in paths
    assert "/rankings/highest-roi-gamefi" in paths
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


def _visible_strategy_ids(html: str) -> list[str]:
    return re.findall(r'<h3><a class="strategy-link" href="/strategies/([^"]+)">', html)

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
