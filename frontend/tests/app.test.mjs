import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  ApiError,
  analyticsMeasurementId,
  buildRankingsPath,
  curatedRankingQuery,
  formatBreakEven,
  formatMoney,
  formatRatio,
  formatUpdatedAge,
  initializeAnalytics,
  opportunityTypeLabel,
  renderAnalyticsConsentBanner,
  renderCatalogStats,
  renderDestinationButton,
  renderError,
  renderFreshnessAlert,
  renderHistory,
  renderHomeShell,
  renderOpportunityDetail,
  renderRankingsTable,
  renderScoreBadge,
  renderSponsoredPlacements,
  renderStrategySignals,
  renderStrategyDetail,
  resetAnalyticsForTests,
  setAnalyticsConsent,
  trackAnalyticsEvent,
} from "../assets/app.js";

test("rankings rendering includes card metrics and stored API values", () => {
  const html = renderRankingsTable(rankingPayload());

  assert.match(html, /DeFi Kingdoms/);
  assert.match(html, /DFK Jeweler/);
  assert.match(html, /Estimated starting capital/);
  assert.match(html, /Estimated net\/day/);
  assert.match(html, /30-day modeled ROI/);
  assert.match(html, /Current break-even/);
  assert.match(html, /82 High/);
  assert.match(html, /79 Very High/);
  assert.match(html, /250.00 USD/);
  assert.match(html, /0.4885 USD/);
  assert.match(html, /0.05862/);
  assert.match(html, /\$250/);
  assert.match(html, /5.86%/);
  assert.match(html, /Profitable now/);
  assert.match(html, /Very high risk/);
  assert.match(html, /Updated /);
  assert.doesNotMatch(html, /Updated 2026-08-16 12:00 UTC/);
  assert.match(html, /\/go\/defi-kingdoms-play/);
  assert.match(html, /source_page=rankings/);
  assert.match(html, /placement=strategy_card/);
  assert.match(html, /ranking-card-grid/);
  assert.doesNotMatch(html, /<table/);
  assert.doesNotMatch(html, /<tr/);
});

test("home renders results as cards before filters without table ranking markup", () => {
  const html = renderHomeShell([{ game_id: "defi-kingdoms", name: "DeFi Kingdoms", economy_types: ["locked-yield-reward"] }], rankingPayload(), [
    opportunityPayload(),
  ]);

  assert.match(html, /GamCryp public beta/);
  assert.match(html, /Find Web3 earning opportunities/);
  assert.match(html, /Risk and confidence separated/);
  assert.match(html, /Top modeled opportunity right now/);
  assert.match(html, /Ranked by modeled 30D ROI, then confidence, risk, and recency/);
  assert.match(html, /When rewards and exits can be priced reproducibly/);
  assert.match(html, /Reviewed opportunities/);
  assert.match(html, /Modeled strategies/);
  assert.match(html, /Opportunity types/);
  assert.match(html, /ROI not measured/);
  assert.match(html, /ranking-card-grid/);
  assert.match(html, /finder-results/);
  assert.match(html, /filter-panel/);
  assert.doesNotMatch(html, /<table/);
});

test("catalog stats summarize V1 coverage without financial recomputation", () => {
  const html = renderCatalogStats(
    { items: rankingPayload().items, page: { total: 10 } },
    [
      { opportunity_type: "GAME", strategy_count: 3 },
      { opportunity_type: "DEPIN_NODE", strategy_count: 0 },
      { opportunity_type: "POINTS", strategy_count: 0 },
    ],
  );

  assert.match(html, /Reviewed opportunities/);
  assert.match(html, />3</);
  assert.match(html, /Modeled strategies/);
  assert.match(html, />10</);
  assert.match(html, /DePIN \/ Nodes, Games, Points programs/);
  assert.doesNotMatch(html, /DEPIN_NODE|DEPIN NODE/);
  assert.match(html, /2 explicit/);
  assert.doesNotMatch(html, /30D ROI|Net\/day|Break-even/);
});

test("static shell uses the official GamCryp logo asset without placeholder markup", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

  assert.match(html, /GamCryp \| Web3 Opportunity Intelligence/);
  assert.match(html, /<img class="brand-logo" src="\/assets\/brand\/gamcryp-logo\.png" alt="GamCryp">/);
  assert.match(html, /brand-lockup/);
  assert.match(html, /mailto:info@gamcryp.com/);
  assert.match(html, /https:\/\/www.youtube.com\/@GamCryp/);
  assert.match(html, /gaMeasurementId: null/);
  assert.doesNotMatch(html, /gamcryp@gmail.com/);
  assert.doesNotMatch(html, /googletagmanager\.com|gtag\/js/);
  assert.doesNotMatch(html, /data-logo-placeholder/);
  assert.doesNotMatch(html, /brand-mark/);
});

test("GamCryp brand stylesheet uses dark navy base and restrained accent palette", () => {
  const css = readFileSync(new URL("../assets/styles.css", import.meta.url), "utf8");

  assert.match(css, /--bg:\s*#020711/);
  assert.match(css, /--cyan:\s*#20f6ff/);
  assert.match(css, /--blue:\s*#2682ff/);
  assert.match(css, /--violet:\s*#9b4dff/);
  assert.match(css, /\.brand-logo\s*{/);
  assert.match(css, /height:\s*auto/);
  assert.match(css, /object-fit:\s*contain/);
  assert.match(css, /overflow-x:\s*hidden/);
  assert.match(css, /\.badge\s*{[\s\S]*white-space:\s*nowrap/);
  assert.match(css, /\.badge\s*{[\s\S]*word-break:\s*keep-all/);
  assert.doesNotMatch(css, /#f6f7f2|#fff5e6|#e9f5ed|#edf4fb/);
});

test("finder filters build supported rankings query only", () => {
  const path = buildRankingsPath({
    capitalMax: "20.00",
    riskMax: "50",
    confidenceMin: "70",
    gameId: "farmers-world",
    opportunityType: "GAME",
    economyType: "resource-production",
    playtime: "unsupported",
  });

  assert.equal(
    path,
    "/rankings?capital_max=20.00&confidence_min=70&risk_max=50&game_id=farmers-world&opportunity_type=GAME&economy_type=resource-production",
  );
  assert.doesNotMatch(path, /playtime/);
});

test("curated ranking landing pages keep organic filters and ignore tracking params", () => {
  assert.equal(curatedRankingQuery("/rankings/under-25", "?utm_source=chatgpt"), "?capital_max=25");
  assert.equal(
    curatedRankingQuery("/rankings/gamefi", "?utm_source=perplexity&risk_max=80"),
    "?opportunity_type=GAME&risk_max=80",
  );
});

test("strategy detail renders capital, earnings, scores, classification, warnings, and versions", () => {
  const html = renderStrategyDetail(strategyPayload(), historyPayload([snapshotPayload(), secondSnapshot()]));

  assert.match(html, /dfk-crystalvale-jeweler-cjewel-max-lock/);
  assert.match(html, /Capital Breakdown/);
  assert.match(html, /Estimated starting capital/);
  assert.match(html, /Sunk cost is modeled as non-recoverable/);
  assert.match(html, /Earnings and Costs/);
  assert.match(html, /Return Metrics/);
  assert.match(html, /Exit-adjusted P&amp;L/);
  assert.match(html, /Confidence/);
  assert.match(html, /Risk/);
  assert.match(html, /LIVE \/ CONFIG \/ DERIVED/);
  assert.match(html, /Adapter contract/);
  assert.match(html, /roi-core-v1/);
  assert.match(html, /2 snapshots/);
  assert.match(html, /0.05862/);
  assert.match(html, /5.86%/);
  assert.match(html, /Start/);
  assert.doesNotMatch(html, /5.862%/);
});

test("opportunity detail shows unavailable ROI in public language without inventing zero", () => {
  const html = renderOpportunityDetail(opportunityPayload());

  assert.match(html, /Grass/);
  assert.match(html, /DePIN \/ Nodes/);
  assert.match(html, /Earn rewards by running software or providing network/);
  assert.match(html, /ROI not measurable yet/);
  assert.match(html, /Points cannot currently be converted to cash reliably/);
  assert.match(html, /Reward type/);
  assert.match(html, /Grass Points/);
  assert.match(html, /\/go\/grass-official/);
  assert.doesNotMatch(html, /DEPIN_NODE|PARTIAL|Financial ROI unavailable/);
  assert.doesNotMatch(html, />0<\/|0\.00/);
});

test("risk and confidence badges preserve unavailable scores", () => {
  const unavailable = {
    available: false,
    score: null,
    label: null,
    unavailable_factors: [{ factor: "score", reason: "No persisted score exists." }],
  };

  assert.match(renderScoreBadge(unavailable, "confidence"), /unavailable/i);
});

test("unavailable and null ratio values do not become zero", () => {
  const html = formatRatio({ value: null, status: "not_computable", reason: "No positive net earnings." });

  assert.match(html, /No positive net earnings/);
  assert.doesNotMatch(html, />0%/);
});

test("stale freshness and low confidence produce a visible warning", () => {
  const snapshot = snapshotPayload();
  snapshot.freshness.overall_status = "stale";
  snapshot.confidence.label = "LOW";

  const html = renderFreshnessAlert(snapshot);

  assert.match(html, /Freshness status is stale/);
  assert.match(html, /Confidence is LOW/);
});

test("error state distinguishes not found from API unavailable", () => {
  assert.match(renderError(new ApiError(404, "Unknown strategy")), /Not found/);
  assert.match(renderError(new Error("Database unavailable")), /Data unavailable/);
});

test("history no-history state is explicit", () => {
  const html = renderHistory(historyPayload([snapshotPayload()]));

  assert.match(html, /Insufficient history/);
  assert.doesNotMatch(html, /snapshots<\/span>/);
});

test("financial formatting preserves exact API Decimal strings", () => {
  assert.match(formatRatio({ value: "0.05862", status: "available", reason: null }), /5.86%/);
  assert.match(formatRatio({ value: "0.84", status: "available", reason: null }), /84%/);
  assert.match(formatRatio({ value: "0.006465812345", status: "available", reason: null }), /0.65%/);
  assert.match(formatRatio({ value: "-0.0012219", status: "available", reason: null }), /-0.12%/);
  assert.match(formatMoney({ amount: "7.371741749984404665", currency: "USD" }), /\$7.37/);
  assert.match(formatMoney({ amount: "0.0317954339244676", currency: "USD" }), /\$0.03/);
  assert.match(formatMoney({ amount: "0.0317954339244676", currency: "USD" }), /0.0317954339244676 USD/);
  assert.match(formatMoney({ amount: "0.0015888099956", currency: "USD" }, { perDay: true }), /\$0.0016\/day/);
  assert.match(formatMoney({ amount: "-3.51E-7", currency: "USD" }, { perDay: true }), /loss &lt; \$0.0001\/day/);
  assert.match(formatBreakEven({ days: "511.7707", status: "available", reason: null }), /512 days/);
  assert.match(formatBreakEven({ days: "4639.788", status: "available", reason: null }), /4,640 days/);
  assert.match(
    formatBreakEven({ days: null, status: "not_computable", reason: "No positive net earnings." }),
    /Not profitable/,
  );
  assert.equal(formatUpdatedAge("2026-08-16T11:36:00Z", new Date("2026-08-16T12:00:00Z")), "Updated 24m ago");
  assert.equal(formatUpdatedAge("2026-08-16T10:00:00Z", new Date("2026-08-16T12:00:00Z")), "Updated 2h ago");
});

test("negative return and warning signals are explicit", () => {
  const snapshot = snapshotPayload();
  snapshot.earnings.net_earnings_day.amount = "-3.51E-7";
  snapshot.roi.roi_total_30d.value = "-0.0012219";
  snapshot.confidence.label = "LOW";
  snapshot.risk.label = "VERY HIGH";

  const html = renderStrategySignals(snapshot);

  assert.match(html, /Unprofitable now/);
  assert.match(html, /Low confidence/);
  assert.match(html, /Very high risk/);
});

test("long strategy names stay in card structure with CTA behavior", () => {
  const payload = rankingPayload();
  payload.items[0].strategy.name =
    "Extremely Long Strategy Name With Many Capital And Reward Assumptions That Must Remain Readable In A Card";

  const html = renderRankingsTable(payload);

  assert.match(html, /ranking-card/);
  assert.match(html, /View strategy/);
  assert.match(html, /Start/);
  assert.match(html, /\/go\/defi-kingdoms-play/);
  assert.doesNotMatch(html, /<table/);
});

test("public CTA never renders None and preserves /go route", () => {
  const html = renderDestinationButton(destinationPayload("grass-official"), "Open", {
    sourcePage: "opportunity_watchlist",
    placement: "opportunity_card",
  });

  assert.match(html, /href="\/go\/grass-official\?source_page=opportunity_watchlist&amp;placement=opportunity_card"/);
  assert.match(html, /data-analytics-link="outbound"/);
  assert.doesNotMatch(html, />None<|Open\s*\|\s*None|Start\s*\|\s*None/);
});

test("public taxonomy helper does not expose backend enum names", () => {
  assert.equal(opportunityTypeLabel("GAME"), "Games");
  assert.equal(opportunityTypeLabel("DEPIN_NODE"), "DePIN / Nodes");
  assert.equal(opportunityTypeLabel("POINTS"), "Points programs");
});

test("analytics is absent without measurement id and gated by consent", () => {
  resetAnalyticsForTests();
  const storage = fakeStorage();
  const context = fakeAnalyticsContext(null, storage);

  assert.equal(analyticsMeasurementId(context.win), "");
  assert.equal(renderAnalyticsConsentBanner(context.win), "");
  assert.equal(initializeAnalytics(context), false);
  assert.equal(trackAnalyticsEvent("opportunity_view", { opportunity_id: "grass" }, context), false);
  assert.equal(context.doc.scripts.length, 0);
});

test("reject consent prevents GA initialization", () => {
  resetAnalyticsForTests();
  const storage = fakeStorage();
  const context = fakeAnalyticsContext("G-TEST1234", storage);

  assert.match(renderAnalyticsConsentBanner(context.win), /Accept analytics/);
  assert.equal(setAnalyticsConsent("rejected", context), true);
  assert.equal(initializeAnalytics(context), false);
  assert.equal(trackAnalyticsEvent("strategy_view", { strategy_id: "dfk" }, context), false);
  assert.equal(context.doc.scripts.length, 0);
});

test("accept consent initializes GA once and sends safe engagement events", () => {
  resetAnalyticsForTests();
  const storage = fakeStorage();
  const context = fakeAnalyticsContext("G-TEST1234", storage);

  assert.equal(setAnalyticsConsent("accepted", context), true);
  assert.equal(initializeAnalytics(context), true);
  assert.equal(initializeAnalytics(context), true);
  assert.equal(context.doc.scripts.length, 1);

  assert.equal(
    trackAnalyticsEvent(
      "start_click",
      {
        opportunity_id: "grass",
        strategy_id: null,
        opportunity_type: "DEPIN_NODE",
        placement: "opportunity_card",
        referral_status: "none",
        raw_financial_payload: "do-not-send",
      },
      context,
    ),
    true,
  );
  const event = context.win.dataLayer.find((entry) => entry[0] === "event" && entry[1] === "start_click");
  assert.equal(event[2].opportunity_id, "grass");
  assert.equal(event[2].placement, "opportunity_card");
  assert.equal(event[2].raw_financial_payload, undefined);
});

test("analytics event module does not throw when GA is unavailable", () => {
  resetAnalyticsForTests();
  assert.doesNotThrow(() => trackAnalyticsEvent("outbound_click", { opportunity_id: "grass" }, { win: null, doc: null }));
});

test("clean ranking cards remove redundant fresh and no-warning badges", () => {
  const payload = rankingPayload();
  payload.items[0].latest_snapshot.warnings = [];

  const html = renderRankingsTable(payload);

  assert.doesNotMatch(html, /No warnings/);
  assert.doesNotMatch(html, />fresh</i);
});

test("sponsored placements render separately from organic ranking cards", () => {
  const html = renderSponsoredPlacements([
    {
      placement_id: "sponsored-1",
      opportunity_id: "grass",
      strategy_id: null,
      surface: "rankings",
      status: "ACTIVE",
      label: "Sponsored opportunity",
      disclosure_text: "Paid placement. Does not affect organic rankings.",
    },
  ]);

  assert.match(html, /Sponsored opportunity/);
  assert.match(html, /Commercial/);
  assert.doesNotMatch(html, /ranking-card/);
});

function rankingPayload() {
  return {
    items: [
      {
        rank: 1,
        strategy: {
          strategy_id: "dfk-crystalvale-jeweler-cjewel-max-lock",
          strategy_version: "v1",
          game_id: "defi-kingdoms",
          game_name: "DeFi Kingdoms",
          name: "DFK Jeweler cJEWEL Max Lock",
          chain: "dfk-chain",
          economy_type: "locked-yield-reward",
          description: "Lock strategy.",
          primary_destination: destinationPayload("defi-kingdoms-play"),
        },
        latest_snapshot: snapshotPayload(),
      },
    ],
    page: { limit: 50, offset: 0, total: 1 },
    ordering: ["roi_total_30d desc"],
  };
}

function strategyPayload() {
  return {
    strategy_id: "dfk-crystalvale-jeweler-cjewel-max-lock",
    strategy_version: "v1",
    opportunity_id: "defi-kingdoms",
    opportunity_type: "GAME",
    game_id: "defi-kingdoms",
    game_name: "DeFi Kingdoms",
    name: "DFK Jeweler cJEWEL Max Lock",
    chain: "dfk-chain",
    economy_type: "locked-yield-reward",
    description: "cJEWEL max-lock strategy.",
    primary_destination: destinationPayload("defi-kingdoms-play"),
    latest_snapshot: snapshotPayload(),
  };
}

function opportunityPayload() {
  return {
    opportunity_id: "grass",
    opportunity_type: "DEPIN_NODE",
    name: "Grass",
    status: "candidate",
    platforms: ["browser-extension"],
    chains: ["solana"],
    economy_types: ["bandwidth-contribution", "points-program"],
    reward_asset_or_points_type: ["Grass Points"],
    value_realization_status: "non_transferable_points",
    data_feasibility_status: "PARTIAL",
    strategy_count: 0,
    legacy_game_id: null,
    feasibility_summary: "Points are not a reproducible financial ROI input.",
    official_source_references: [{ label: "Grass terms", url: "https://www.grass.io/terms-and-conditions/" }],
    outbound_destinations: [destinationPayload("grass-official")],
    primary_destination: destinationPayload("grass-official"),
    strategies: [],
  };
}

function destinationPayload(slug) {
  return {
    destination_id: `dest-${slug}`,
    destination_slug: slug,
    opportunity_id: slug === "grass-official" ? "grass" : "defi-kingdoms",
    opportunity_type: slug === "grass-official" ? "DEPIN_NODE" : "GAME",
    game_id: slug === "grass-official" ? null : "defi-kingdoms",
    strategy_id: null,
    destination_type: "official_site",
    label: "Open official site",
    redirect_url: `/go/${slug}`,
    official_url: "https://example.com/",
    referral_url: null,
    referral_code: null,
    status: "active",
    is_affiliate: false,
    affiliate_program: null,
    commercial_relationship: "none",
    disclosure_text: "Official outbound link. No affiliate relationship is configured.",
    referral_status: "NONE",
    source_reference: { label: "Official site", url: "https://example.com/" },
    reviewed_at: "2026-08-23T00:00:00Z",
    verification_status: "verified",
    allowed_surfaces: ["web", "api", "redirect"],
  };
}

function fakeStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
  };
}

function fakeAnalyticsContext(measurementId, storage) {
  const doc = {
    scripts: [],
    head: {
      appendChild(script) {
        doc.scripts.push(script);
      },
    },
    createElement(tag) {
      return { tag, dataset: {} };
    },
    querySelector(selector) {
      const match = selector.match(/script\[data-gamcryp-ga="([^"]+)"\]/);
      if (!match) {
        return null;
      }
      return doc.scripts.find((script) => script.dataset.gamcrypGa === match[1]) || null;
    },
  };
  const win = {
    GAMCRYP_PUBLIC_CONFIG: {
      gaMeasurementId: measurementId,
    },
    localStorage: storage,
    dataLayer: [],
  };
  return { win, doc, storage };
}

function historyPayload(items) {
  return {
    items,
    page: { limit: 50, offset: 0, total: items.length },
  };
}

function secondSnapshot() {
  const snapshot = snapshotPayload();
  snapshot.snapshot_id = "snapshot-2";
  snapshot.calculated_at = "2026-08-16T13:00:00Z";
  snapshot.roi.roi_total_30d.value = "0.06000";
  return snapshot;
}

function snapshotPayload() {
  return {
    snapshot_id: "snapshot-1",
    strategy_id: "dfk-crystalvale-jeweler-cjewel-max-lock",
    strategy_version: "v1",
    opportunity_id: "defi-kingdoms",
    opportunity_type: "GAME",
    game_id: "defi-kingdoms",
    game_name: "DeFi Kingdoms",
    chain: "dfk-chain",
    economy_type: "locked-yield-reward",
    calculated_at: "2026-08-16T12:00:00Z",
    capital: {
      total_capital: { amount: "250.00", currency: "USD" },
      sunk_cost: { amount: "0", currency: "USD" },
      recoverable_capital: { amount: "125.00", currency: "USD" },
      capital_at_risk: { amount: "250.00", currency: "USD" },
    },
    earnings: {
      gross_nominal_earnings_day: { amount: "0.50", currency: "USD" },
      realizable_earnings_day: { amount: "0.4985", currency: "USD" },
      operating_cost_day: { amount: "0", currency: "USD" },
      transaction_cost_day: { amount: "0.01", currency: "USD" },
      other_cost_day: { amount: "0", currency: "USD" },
      net_earnings_day: { amount: "0.4885", currency: "USD" },
    },
    roi: {
      break_even: {
        basis: "total_capital",
        recovery_target: { amount: "250.00", currency: "USD" },
        days: "511.7707",
        status: "available",
        reason: null,
      },
      roi_total_7d: { value: "0.013678", status: "available", reason: null },
      roi_total_30d: { value: "0.05862", status: "available", reason: null },
      roi_total_90d: { value: "0.17586", status: "available", reason: null },
      roi_risk_7d: { value: "0.013678", status: "available", reason: null },
      roi_risk_30d: { value: "0.05862", status: "available", reason: null },
      roi_risk_90d: { value: "0.17586", status: "available", reason: null },
      exit_adjusted_pnl: { amount: "-125.00", currency: "USD" },
    },
    confidence: {
      available: true,
      score: 82,
      label: "HIGH",
      methodology_version: "risk-confidence-v1",
      contributions: [{ factor: "valuation_quality", points: 6, reason: "Executable quote available.", evidence: { source: "quote" } }],
      unavailable_factors: [],
    },
    risk: {
      available: true,
      score: 79,
      label: "VERY HIGH",
      methodology_version: "risk-confidence-v1",
      contributions: [{ factor: "lock_exit_penalty", points: 35, reason: "Long lock and exit penalty.", evidence: { lock_days: 1095 } }],
      unavailable_factors: [],
    },
    warnings: [{ code: "long_lock", message: "Long lock period.", severity: "warning" }],
    freshness: {
      overall_status: "fresh",
      calculated_at: "2026-08-16T12:00:00Z",
      status_counts: { fresh: 5, stale: 0, invalid: 0, missing: 0 },
      input_count: 5,
    },
    versions: {
      adapter_contract_version: "adapter-contract-v1",
      model_version: "roi-core-v1",
      scoring_methodology_version: "risk-confidence-v1",
    },
    uncertainty_ranges: [],
    classification_summary: {
      counts: { LIVE: 2, CONFIG: 3, DERIVED: 4 },
      metrics: {
        "dfk.reward": "LIVE",
        "dfk.lock_days": "CONFIG",
        "dfk.realizable_value": "DERIVED",
      },
    },
  };
}
