import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  ApiError,
  analyticsMeasurementId,
  applyCuratedRankingConstraints,
  buildRankingsPath,
  curatedRankingQuery,
  formatBreakEven,
  formatMoney,
  formatRatio,
  formatUpdatedAge,
  hasConsentGatedAnalytics,
  initializeAnalytics,
  initializeErrorTracking,
  initializeProductAnalytics,
  opportunityTypeLabel,
  renderAnalyticsConsentBanner,
  renderCatalogStats,
  renderDestinationButton,
  renderError,
  renderFreshnessAlert,
  renderGameDetail,
  renderHistory,
  renderHomeAnswerBlock,
  renderHomeShell,
  renderOpportunityAnswerBlock,
  renderOpportunityCard,
  renderOpportunityDetail,
  renderOpportunityGuidance,
  renderUnavailableRoiExplanation,
  renderRankingsAnswerBlock,
  renderRankingsPage,
  renderRankingsTable,
  renderStrategyAnswerBlock,
  renderScoreBadge,
  renderSponsoredPlacements,
  renderStrategySignals,
  renderStrategyDetail,
  resetAnalyticsForTests,
  sanitizeBrowserSentryEvent,
  sentryFrontendDsn,
  setAnalyticsConsent,
  trackAnalyticsEvent,
  trackProductAnalyticsEvent,
} from "../assets/app.js";

test("rankings rendering includes card metrics and stored API values", () => {
  const html = renderRankingsTable(rankingPayload());

  assert.match(html, /DeFi Kingdoms/);
  assert.match(html, /DFK Jeweler/);
  assert.match(html, /Starting capital/);
  assert.match(html, /Net earning\/day/);
  assert.match(html, /30-day ROI/);
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
  assert.doesNotMatch(html, /<p class="muted">v1 \| locked-yield-reward<\/p>/);
});

test("rankings page exposes only published curated links", () => {
  const html = renderRankingsPage(rankingPayload());

  assert.match(html, /Best passive GameFi ROI strategies/);
  assert.match(html, /best-depin-under-100/);
  assert.match(html, /pc-depin/);
  assert.match(html, /no-hardware-depin/);
  assert.doesNotMatch(html, /phone-depin/);
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

test("answer-ready blocks expose stored values without changing calculations", () => {
  const rankings = rankingPayload();
  const strategy = strategyPayload();
  const opportunity = { ...opportunityPayload(), strategies: [strategy] };

  const home = renderHomeAnswerBlock(rankings, [opportunityPayload()]);
  const ranking = renderRankingsAnswerBlock(rankings, { title: "GameFi strategies under $100 capital", filters: "opportunity_type=GAME&capital_max=100" });
  const opportunityHtml = renderOpportunityAnswerBlock(opportunity);
  const strategyHtml = renderStrategyAnswerBlock(strategy, strategy.latest_snapshot);

  assert.match(home, /Quick overview/);
  assert.match(ranking, /Quick comparison/);
  assert.match(ranking, /Capital up to \$100/);
  assert.match(opportunityHtml, /Quick opportunity summary/);
  assert.match(strategyHtml, /Quick strategy summary/);
  assert.match(strategyHtml, /Estimated gross earnings\/day/);
  assert.match(strategyHtml, /Required time\/effort/);
  assert.match(strategyHtml, /Major assumptions/);
  assert.match(strategyHtml, /5\.86%/);
  assert.doesNotMatch(strategyHtml, /0\.05862 30-day ROI/);
  assert.doesNotMatch(opportunityHtml, /DEPIN_NODE|PARTIAL|NONE/);
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
  assert.match(html, /https:\/\/x.com\/GamCryp/);
  assert.match(html, /mailto:info@gamcryp.com/);
  assert.match(html, />info@gamcryp.com</);
  assert.match(html, /https:\/\/www.youtube.com\/@GamCryp/);
  assert.match(html, /gaMeasurementId: null/);
  assert.match(html, /posthogProjectApiKey: null/);
  assert.match(html, /sentryFrontendDsn: null/);
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
  assert.match(css, /\.badge\s*{[\s\S]*min-height:\s*30px/);
  assert.match(css, /\.badge\s*{[\s\S]*padding:\s*5px 10px/);
  assert.match(css, /\.badge\s*{[\s\S]*line-height:\s*1\.22/);
  assert.match(css, /\.badge\s*{[\s\S]*white-space:\s*nowrap/);
  assert.match(css, /\.badge\s*{[\s\S]*word-break:\s*keep-all/);
  assert.match(css, /\.ranking-card-grid\s*{[\s\S]*minmax\(min\(100%, 340px\), 1fr\)/);
  assert.match(css, /\.opportunity-grid\s*{[\s\S]*minmax\(min\(100%, 300px\), 1fr\)/);
  assert.match(css, /\.opportunity-facts\s*{[\s\S]*grid-template-columns:\s*1fr/);
  assert.match(css, /\.watchlist-note\s*{[\s\S]*line-height:\s*1\.42/);
  assert.match(css, /\.button,\r?\n\.secondary-button\s*{[\s\S]*justify-content:\s*center/);
  assert.match(css, /\.answer-card\s*{/);
  assert.match(css, /\.answer-grid\s*{[\s\S]*repeat\(3, minmax\(0, 1fr\)\)/);
  assert.match(css, /@media \(max-width: 900px\)[\s\S]*\.answer-grid\s*{[\s\S]*grid-template-columns:\s*1fr/);
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
  assert.equal(
    curatedRankingQuery("/rankings/gamefi-under-100", "?utm_campaign=ai&confidence_min=50"),
    "?opportunity_type=GAME&capital_max=100&confidence_min=50",
  );
  assert.equal(
    curatedRankingQuery("/rankings/best-passive-gamefi", "?utm_source=chatgpt&risk_max=90"),
    "?opportunity_type=GAME&economy_type=locked-yield-reward&risk_max=90",
  );
  assert.equal(
    curatedRankingQuery("/rankings/best-depin-under-100", "?risk_max=50"),
    "?opportunity_type=DEPIN_NODE&capital_max=100&risk_max=50",
  );
});

test("curated DePIN page constraints filter by authoritative opportunity platforms", () => {
  const rankings = {
    items: [
      { rank: 1, strategy: { opportunity_id: "storj-storage-node" } },
      { rank: 2, strategy: { opportunity_id: "geodnet" } },
      { rank: 3, strategy: { opportunity_id: "dimo" } },
      { rank: 4, strategy: { opportunity_id: "mysterium-network-node" } },
    ],
    page: { limit: 100, offset: 0, total: 4 },
  };
  const opportunities = [
    { opportunity_id: "storj-storage-node", platforms: ["desktop", "server"] },
    { opportunity_id: "geodnet", platforms: ["hardware-node"] },
    { opportunity_id: "dimo", platforms: ["mobile", "web"] },
    { opportunity_id: "mysterium-network-node", platforms: ["desktop"] },
  ];

  const pc = applyCuratedRankingConstraints(rankings, opportunities, "/rankings/pc-depin");
  const noHardware = applyCuratedRankingConstraints(rankings, opportunities, "/rankings/no-hardware-depin");

  assert.deepEqual(pc.items.map((item) => item.strategy.opportunity_id), ["storj-storage-node", "mysterium-network-node"]);
  assert.deepEqual(pc.items.map((item) => item.rank), [1, 2]);
  assert.equal(pc.page.total, 2);
  assert.deepEqual(noHardware.items.map((item) => item.strategy.opportunity_id), [
    "storj-storage-node",
    "dimo",
    "mysterium-network-node",
  ]);
  assert.deepEqual(noHardware.items.map((item) => item.rank), [1, 2, 3]);
  assert.equal(noHardware.page.total, 3);
});

test("strategy detail renders capital, earnings, scores, classification, warnings, and versions", () => {
  const html = renderStrategyDetail(strategyPayload(), historyPayload([snapshotPayload(), secondSnapshot()]));

  assert.match(html, /dfk-crystalvale-jeweler-cjewel-max-lock/);
  assert.match(html, /Capital Breakdown/);
  assert.match(html, /Starting capital/);
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
  assert.match(html, /Open project/);
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
  assert.doesNotMatch(html, /\$0(?:\.00)?|>0(?:\.00)?%/);
});

test("structured unavailable ROI explains evidence gaps without leaking nulls", () => {
  const opportunity = {
    ...opportunityPayload(),
    roi_unavailable: {
      reason: "Rewards have no reproducible monetary route.",
      missing_evidence: ["Transferable claim route", null],
      modeling_requirements: ["Published settlement value"],
    },
  };
  const html = renderOpportunityDetail(opportunity);
  const explanation = renderUnavailableRoiExplanation(opportunity);

  assert.match(html, /Why ROI is unavailable/);
  assert.match(html, /Rewards have no reproducible monetary route/);
  assert.match(html, /What is missing/);
  assert.match(html, /What would make it modelable/);
  assert.match(explanation, /Transferable claim route/);
  assert.doesNotMatch(explanation, /null|undefined|None/);
  assert.doesNotMatch(html, /\$0(?:\.00)?|>0(?:\.00)?%/);
});

test("structured unavailable ROI omits empty explanation sections and stays concise in cards", () => {
  const opportunity = { ...opportunityPayload(), roi_unavailable: { reason: "Account eligibility is not reproducible." } };
  const detail = renderUnavailableRoiExplanation(opportunity);
  const card = renderOpportunityCard(opportunity);

  assert.match(detail, /Account eligibility is not reproducible/);
  assert.doesNotMatch(detail, /What is missing|What would make it modelable/);
  assert.match(card, /Account eligibility is not reproducible/);
  assert.match(card, /ROI status/);
  assert.doesNotMatch(card, /Opportunity type/);
  assert.ok(visibleText(card).length < 900);
});

test("opportunity guidance renders complete, partial, and empty structures safely", () => {
  const complete = renderOpportunityGuidance({
    how_to_start: ["Start here"],
    what_you_need: ["Required item"],
    how_you_earn: ["Earn this"],
    how_to_exit_or_claim: ["Claim here"],
  });
  assert.match(complete, /How it works/);
  assert.match(complete, /How to start/);
  assert.match(complete, /What you need/);
  assert.match(complete, /How you earn/);
  assert.match(complete, /How to claim or exit/);

  const partial = renderOpportunityGuidance({ how_to_start: ["Start here"], what_you_need: [], how_you_earn: null });
  assert.match(partial, /How to start/);
  assert.doesNotMatch(partial, /What you need|How you earn|How to claim or exit/);
  assert.equal(renderOpportunityGuidance(null), "");
  assert.equal(renderOpportunityGuidance({ how_to_start: [null, ""], what_you_need: [] }), "");
  assert.doesNotMatch(complete, /undefined|null/);
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

  assert.match(html, /At least two stored snapshots are needed/);
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
  assert.equal(formatUpdatedAge("2026-07-01T12:00:00.000000+00:00", new Date("2026-08-16T12:00:00Z")), "Updated Jul 1, 2026 12:00 UTC");
});

test("strategy detail keeps visible precision readable while preserving exact values", () => {
  const strategy = strategyPayload();
  const snapshot = strategy.latest_snapshot;
  snapshot.calculated_at = "2026-08-16T12:00:00.000000+00:00";
  snapshot.earnings.net_earnings_day.amount = "0.488500000000000000";
  snapshot.roi.break_even.days = "511.7707000000";
  snapshot.roi.roi_total_30d.value = "0.0586200000000000";
  snapshot.risk.contributions[0].evidence = {
    observed_at: "2026-08-16T12:00:00.000000+00:00",
    slippage_ratio: "12.384728391",
    nested: { exact_input: "0.488500000000000000" },
  };
  snapshot.uncertainty_ranges = [
    {
      metric: "example.expected_reward_day",
      values: {
        low_metric: "0.488500000000000000",
        base_metric: "12.384728391",
        high_metric: "0.0000000351",
      },
      unit: "USD/day",
    },
  ];

  const html = renderStrategyDetail(strategy, historyPayload([snapshot, secondSnapshot()]));
  const visible = visibleText(html);

  assert.match(visible, /Aug 16, 2026 12:00 UTC/);
  assert.match(visible, /\$0\.49\/day/);
  assert.match(visible, /5\.86%/);
  assert.match(visible, /512 days/);
  assert.match(visible, /12\.38/);
  assert.match(visible, /< 0\.0001/);
  assert.doesNotMatch(visible, /0\.488500000000000000/);
  assert.doesNotMatch(visible, /0\.0586200000000000/);
  assert.doesNotMatch(visible, /511\.7707000000/);
  assert.doesNotMatch(visible, /2026-08-16T12:00:00\.000000\+00:00/);
  assert.match(html, /title="Exact value: 0\.488500000000000000"/);
  assert.match(html, /title="Exact ratio: 0\.0586200000000000"/);
  assert.match(html, /title="Exact days: 511\.7707000000"/);
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
  assert.match(html, /Open project/);
  assert.match(html, /\/go\/defi-kingdoms-play/);
  assert.doesNotMatch(html, /<table/);
});

test("ranking cards distinguish repeated opportunities from their child strategies", () => {
  const payload = rankingPayload();
  const second = structuredClone(payload.items[0]);
  second.rank = 2;
  second.strategy = { ...second.strategy, opportunity_id: "defi-kingdoms", strategy_id: "dfk-alt", name: "DFK Alternative Approach" };
  payload.items.push(second);
  payload.page.total = 2;

  const html = renderRankingsTable(payload);

  assert.equal((html.match(/class="ranking-parent"/g) || []).length, 2);
  assert.match(html, /Opportunity/);
  assert.match(html, /DFK Jeweler cJEWEL Max Lock/);
  assert.match(html, /DFK Alternative Approach/);
  assert.match(html, /href="\/opportunities\/defi-kingdoms"/);
  assert.match(html, /Ranked strategies/);
});

test("opportunity strategy list uses an explicit child-strategy heading", () => {
  const html = renderGameDetail(gamePayload(strategyPayload()));
  assert.match(html, /Strategies in this game/);
  assert.match(html, /Opportunity/);
  assert.match(html, /href="\/opportunities\/defi-kingdoms"/);
});


test("legacy game detail CTA uses risk-aware wording without changing link behavior", () => {
  const highRiskGame = gamePayload(strategyPayload());
  const highRiskHtml = renderGameDetail(highRiskGame);

  assert.match(highRiskHtml, /Open project/);
  assert.match(highRiskHtml, /High-risk strategy\. Opening the project is not a recommendation; review the assumptions first\./);
  assert.match(highRiskHtml, /href="\/go\/defi-kingdoms-play\?source_page=game_detail&amp;placement=primary_cta"/);
  assert.match(highRiskHtml, /target="_blank"/);
  assert.match(highRiskHtml, /rel="noopener noreferrer"/);
  assert.match(highRiskHtml, /<a class="secondary-button" href="\/opportunities\/defi-kingdoms" data-link>Opportunity record<\/a>/);
  assert.doesNotMatch(highRiskHtml, /<a class="secondary-button" href="\/opportunities\/defi-kingdoms"[^>]*target="_blank"/);

  const normalSnapshot = snapshotPayload();
  normalSnapshot.risk.score = 20;
  normalSnapshot.risk.label = "LOW";
  const normalHtml = renderGameDetail(gamePayload({ ...strategyPayload(), latest_snapshot: normalSnapshot }));

  assert.match(normalHtml, />\s*Start\s*</);
  assert.doesNotMatch(normalHtml, /High-risk strategy/);
});

test("public CTA never renders None and preserves /go route", () => {
  const html = renderDestinationButton(destinationPayload("grass-official"), "Open", {
    sourcePage: "opportunity_watchlist",
    placement: "opportunity_card",
  });

  assert.match(html, /href="\/go\/grass-official\?source_page=opportunity_watchlist&amp;placement=opportunity_card"/);
  assert.match(html, /data-analytics-link="outbound"/);
  assert.match(html, /data-destination-slug="grass-official"/);
  assert.match(html, /data-target-url-kind="official"/);
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
  assert.equal(hasConsentGatedAnalytics(context.win), false);
  assert.equal(renderAnalyticsConsentBanner(context.win), "");
  assert.equal(initializeAnalytics(context), false);
  assert.equal(initializeProductAnalytics(context), false);
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

test("PostHog product analytics is consent gated, explicit, and privacy safe", () => {
  resetAnalyticsForTests();
  const storage = fakeStorage();
  const sent = [];
  const context = fakeAnalyticsContext("G-TEST1234", storage, {
    posthogProjectApiKey: "phc_test_key",
    posthogHost: "https://us.i.posthog.com",
  });
  context.win.location = { pathname: "/rankings/gamefi-under-50", search: "?utm_source=x&utm_medium=social" };
  context.win.navigator = { sendBeacon: (url, body) => sent.push({ url, payload: JSON.parse(body) }) > 0 };
  context.idGenerator = () => "stable-id";

  assert.match(renderAnalyticsConsentBanner(context.win), /Accept analytics/);
  assert.equal(trackProductAnalyticsEvent("ranking_view", { ranking_slug: "gamefi-under-50" }, context), false);
  assert.equal(setAnalyticsConsent("accepted", context), true);
  assert.equal(initializeProductAnalytics(context), true);
  assert.equal(
    trackProductAnalyticsEvent(
      "ranking_view",
      {
        ranking_slug: "gamefi-under-50",
        snapshot_id: "snapshot-1",
        snapshot_timestamp: "2026-08-16T12:00:00Z",
        raw_financial_payload: "do-not-send",
        wallet_address: "do-not-send",
      },
      context,
    ),
    true,
  );

  assert.equal(sent.length, 1);
  assert.equal(sent[0].url, "https://us.i.posthog.com/capture/");
  assert.equal(sent[0].payload.event, "ranking_view");
  assert.equal(sent[0].payload.distinct_id, "visitor:stable-id");
  assert.equal(sent[0].payload.properties.ranking_slug, "gamefi-under-50");
  assert.equal(sent[0].payload.properties.snapshot_id, "snapshot-1");
  assert.equal(sent[0].payload.properties.snapshot_timestamp, "2026-08-16T12:00:00Z");
  assert.equal(sent[0].payload.properties.utm_source, "x");
  assert.equal(sent[0].payload.properties.utm_medium, "social");
  assert.equal(sent[0].payload.properties.raw_financial_payload, undefined);
  assert.equal(sent[0].payload.properties.wallet_address, undefined);
  assert.equal(sent[0].payload.properties.$process_person_profile, false);
});

test("outbound CTAs expose referral versus official fallback metadata without changing /go", () => {
  const officialHtml = renderDestinationButton(destinationPayload("grass-official"), "Open", {
    sourcePage: "opportunity_watchlist",
    placement: "opportunity_card",
  });
  const referralDestination = {
    ...destinationPayload("partner-play"),
    referral_url: "https://example.com/ref",
    referral_status: "ACTIVE",
    is_affiliate: true,
    commercial_relationship: "affiliate",
  };
  const referralHtml = renderDestinationButton(referralDestination, "Start", {
    sourcePage: "rankings",
    placement: "strategy_card",
  });

  assert.match(officialHtml, /href="\/go\/grass-official\?source_page=opportunity_watchlist&amp;placement=opportunity_card"/);
  assert.match(officialHtml, /data-target-url-kind="official"/);
  assert.match(referralHtml, /href="\/go\/partner-play\?source_page=rankings&amp;placement=strategy_card"/);
  assert.match(referralHtml, /data-target-url-kind="referral"/);
  assert.match(referralHtml, /data-is-affiliate="true"/);
});

test("Sentry browser initialization is optional and sanitizes sensitive event fields", () => {
  resetAnalyticsForTests();
  const inert = fakeAnalyticsContext(null, fakeStorage());
  assert.equal(sentryFrontendDsn(inert.win), "");
  assert.equal(initializeErrorTracking(inert), false);

  const storage = fakeStorage();
  const context = fakeAnalyticsContext(null, storage, {
    sentryFrontendDsn: "https://public@example.ingest.sentry.io/123",
    sentryEnvironment: "production",
    sentryRelease: "abc123",
    sentryTracesSampleRate: 0.01,
  });
  const initCalls = [];
  context.win.Sentry = {
    browserTracingIntegration: () => "browser-tracing",
    init: (options) => initCalls.push(options),
  };
  assert.equal(initializeErrorTracking(context), true);
  assert.equal(initCalls.length, 1);
  assert.equal(initCalls[0].dsn, "https://public@example.ingest.sentry.io/123");
  assert.equal(initCalls[0].sendDefaultPii, false);
  assert.equal(initCalls[0].replaysSessionSampleRate, 0);
  assert.equal(initCalls[0].replaysOnErrorSampleRate, 0);
  assert.deepEqual(initCalls[0].integrations, ["browser-tracing"]);

  const event = sanitizeBrowserSentryEvent({
    request: {
      url: "https://gamcryp.com/strategies/demo?token=secret",
      data: { password: "secret" },
      cookies: "session=secret",
      headers: { Authorization: "Bearer secret", "User-Agent": "test" },
    },
    user: { email: "user@example.com", id: "public-id", ip_address: "127.0.0.1" },
    extra: { api_key: "secret", safe: "ok" },
  });

  assert.equal(event.request.url, "https://gamcryp.com/strategies/demo");
  assert.equal(event.request.data, undefined);
  assert.equal(event.request.cookies, undefined);
  assert.equal(event.request.headers.Authorization, "[Filtered]");
  assert.equal(event.request.headers["User-Agent"], "test");
  assert.deepEqual(event.user, { id: "public-id" });
  assert.equal(event.extra.api_key, "[Filtered]");
  assert.equal(event.extra.safe, "ok");
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

function visibleText(html) {
  return String(html)
    .replace(/<[^>]*>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function gamePayload(strategy = strategyPayload()) {
  return {
    game_id: "defi-kingdoms",
    opportunity_id: "defi-kingdoms",
    opportunity_type: "GAME",
    name: "DeFi Kingdoms",
    chains: ["dfk-chain"],
    economy_types: ["locked-yield-reward"],
    status: "active",
    strategy_count: 1,
    primary_destination: destinationPayload("defi-kingdoms-play"),
    strategies: [strategy],
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

function fakeAnalyticsContext(measurementId, storage, configOverrides = {}) {
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
      const gaMatch = selector.match(/script\[data-gamcryp-ga="([^\"]+)"\]/);
      if (gaMatch) {
        return doc.scripts.find((script) => script.dataset.gamcrypGa === gaMatch[1]) || null;
      }
      if (selector === "script[data-gamcryp-sentry='browser']") {
        return doc.scripts.find((script) => script.dataset.gamcrypSentry === "browser") || null;
      }
      return null;
    },
  };
  const win = {
    GAMCRYP_PUBLIC_CONFIG: {
      gaMeasurementId: measurementId,
      posthogProjectApiKey: null,
      posthogHost: "https://us.i.posthog.com",
      sentryFrontendDsn: null,
      sentryEnvironment: "test",
      sentryRelease: null,
      sentryTracesSampleRate: 0.02,
      ...configOverrides,
    },
    localStorage: storage,
    dataLayer: [],
    location: { pathname: "/", search: "" },
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
