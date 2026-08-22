import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  ApiError,
  buildRankingsPath,
  formatBreakEven,
  formatMoney,
  formatRatio,
  renderError,
  renderFreshnessAlert,
  renderHistory,
  renderHomeShell,
  renderOpportunityDetail,
  renderRankingsTable,
  renderScoreBadge,
  renderStrategySignals,
  renderStrategyDetail,
} from "../assets/app.js";

test("rankings rendering includes card metrics and stored API values", () => {
  const html = renderRankingsTable(rankingPayload());

  assert.match(html, /DeFi Kingdoms/);
  assert.match(html, /DFK Jeweler/);
  assert.match(html, /Capital/);
  assert.match(html, /Net\/day/);
  assert.match(html, /30D ROI/);
  assert.match(html, /Break-even/);
  assert.match(html, /82 HIGH/);
  assert.match(html, /79 VERY HIGH/);
  assert.match(html, /250.00 USD/);
  assert.match(html, /0.4885 USD/);
  assert.match(html, /0.05862/);
  assert.match(html, /\$250/);
  assert.match(html, /5.86%/);
  assert.match(html, /Positive return/);
  assert.match(html, /Very high risk warning/);
  assert.match(html, /Updated 2026-08-16 12:00 UTC/);
  assert.match(html, /\/go\/defi-kingdoms-play/);
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
  assert.match(html, /Top current modeled result/);
  assert.match(html, /ranking-card-grid/);
  assert.match(html, /finder-results/);
  assert.doesNotMatch(html, /<table/);
});

test("static shell uses GamCryp brand lockup without a fabricated logo image", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

  assert.match(html, /GamCryp \| Web3 Opportunity Intelligence/);
  assert.match(html, /brand-lockup/);
  assert.match(html, /data-logo-placeholder="\/assets\/brand\/gamcryp-logo\.png"/);
  assert.doesNotMatch(html, /brand-mark/);
  assert.doesNotMatch(html, /<img[^>]+gamcryp/i);
});

test("GamCryp brand stylesheet uses dark navy base and restrained accent palette", () => {
  const css = readFileSync(new URL("../assets/styles.css", import.meta.url), "utf8");

  assert.match(css, /--bg:\s*#020711/);
  assert.match(css, /--cyan:\s*#20f6ff/);
  assert.match(css, /--blue:\s*#2682ff/);
  assert.match(css, /--violet:\s*#9b4dff/);
  assert.match(css, /overflow-x:\s*hidden/);
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

test("strategy detail renders capital, earnings, scores, classification, warnings, and versions", () => {
  const html = renderStrategyDetail(strategyPayload(), historyPayload([snapshotPayload(), secondSnapshot()]));

  assert.match(html, /dfk-crystalvale-jeweler-cjewel-max-lock/);
  assert.match(html, /Capital Breakdown/);
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

test("opportunity detail shows unavailable financial ROI without inventing zero", () => {
  const html = renderOpportunityDetail(opportunityPayload());

  assert.match(html, /Grass/);
  assert.match(html, /Financial ROI unavailable/);
  assert.match(html, /Reward type/);
  assert.match(html, /Non Transferable Points/);
  assert.match(html, /\/go\/grass-official/);
  assert.doesNotMatch(html, />0<\/|0\.00/);
});

test("risk and confidence badges preserve unavailable scores", () => {
  const unavailable = {
    available: false,
    score: null,
    label: null,
    unavailable_factors: [{ factor: "score", reason: "No persisted score exists." }],
  };

  assert.match(renderScoreBadge(unavailable, "confidence"), /Unavailable/);
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
});

test("negative return and warning signals are explicit", () => {
  const snapshot = snapshotPayload();
  snapshot.earnings.net_earnings_day.amount = "-3.51E-7";
  snapshot.roi.roi_total_30d.value = "-0.0012219";
  snapshot.confidence.label = "LOW";
  snapshot.risk.label = "VERY HIGH";

  const html = renderStrategySignals(snapshot);

  assert.match(html, /Negative return/);
  assert.match(html, /Low confidence warning/);
  assert.match(html, /Very high risk warning/);
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
    source_reference: { label: "Official site", url: "https://example.com/" },
    reviewed_at: "2026-08-23T00:00:00Z",
    verification_status: "verified",
    allowed_surfaces: ["web", "api", "redirect"],
  };
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
