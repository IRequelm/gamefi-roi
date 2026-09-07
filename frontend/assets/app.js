const API_BASE = "/api/v1";
const CURATED_RANKING_MIN_RESULTS = 2;
const CURATED_RANKING_FILTERS = {
  "/rankings/under-25": "capital_max=25",
  "/rankings/high-confidence": "confidence_min=80",
  "/rankings/gamefi": "opportunity_type=GAME",
  "/rankings/gamefi-under-10": "opportunity_type=GAME&capital_max=10",
  "/rankings/gamefi-under-50": "opportunity_type=GAME&capital_max=50",
  "/rankings/gamefi-under-100": "opportunity_type=GAME&capital_max=100",
  "/rankings/lowest-capital-gamefi": "opportunity_type=GAME&capital_max=25",
  "/rankings/highest-roi-gamefi": "opportunity_type=GAME",
  "/rankings/best-passive-gamefi": "opportunity_type=GAME&economy_type=locked-yield-reward",
  "/rankings/best-depin-under-100": "opportunity_type=DEPIN_NODE&capital_max=100",
  "/rankings/pc-depin": "opportunity_type=DEPIN_NODE",
  "/rankings/no-hardware-depin": "opportunity_type=DEPIN_NODE",
};
const CURATED_RANKING_TITLES = {
  "/rankings/under-25": "Web3 strategies under $25 capital",
  "/rankings/high-confidence": "High-confidence modeled Web3 strategies",
  "/rankings/gamefi": "GameFi ROI rankings",
  "/rankings/gamefi-under-10": "GameFi strategies under $10 capital",
  "/rankings/gamefi-under-50": "GameFi strategies under $50 capital",
  "/rankings/gamefi-under-100": "GameFi strategies under $100 capital",
  "/rankings/lowest-capital-gamefi": "Lowest-capital modeled GameFi strategies",
  "/rankings/highest-roi-gamefi": "Highest modeled GameFi ROI strategies",
  "/rankings/best-passive-gamefi": "Best passive GameFi ROI strategies",
  "/rankings/best-depin-under-100": "Best DePIN opportunities under $100",
  "/rankings/pc-depin": "PC DePIN earning opportunities",
  "/rankings/no-hardware-depin": "No-hardware DePIN earning opportunities",
};
const CURATED_RANKING_CONSTRAINTS = {
  "/rankings/pc-depin": { requiredPlatforms: ["desktop", "browser-extension", "cli", "docker-node"] },
  "/rankings/no-hardware-depin": {
    requiredPlatforms: ["browser-extension", "desktop", "web", "cli", "docker-node"],
    excludedPlatforms: ["hardware-node"],
  },
};
const RANKING_FILTER_KEYS = new Set([
  "capital_min",
  "capital_max",
  "confidence_min",
  "risk_max",
  "game_id",
  "opportunity_id",
  "opportunity_type",
  "chain",
  "economy_type",
]);
const ANALYTICS_CONSENT_KEY = "gamcryp.analyticsConsent.v1";
const PRODUCT_ANALYTICS_DISTINCT_ID_KEY = "gamcryp.productAnalyticsDistinctId.v1";
const SENTRY_BROWSER_SDK_URL = "https://browser.sentry-cdn.com/8.55.0/bundle.tracing.min.js";
const ANALYTICS_ALLOWED_EVENTS = new Set([
  "page_view",
  "opportunity_view",
  "strategy_view",
  "start_click",
  "outbound_click",
]);
const ANALYTICS_ALLOWED_PARAMS = new Set([
  "opportunity_id",
  "strategy_id",
  "opportunity_type",
  "placement",
  "referral_status",
  "page_path",
  "page_title",
]);
const PRODUCT_ANALYTICS_ALLOWED_EVENTS = new Set([
  "opportunity_view",
  "strategy_view",
  "ranking_view",
  "opportunity_to_strategy_click",
  "ranking_to_strategy_click",
  "internal_compare_or_next_click",
  "outbound_go_click",
  "referral_outbound_click",
  "official_fallback_outbound_click",
  "opportunity_search_used",
  "ranking_filter_used",
]);
const PRODUCT_ANALYTICS_ALLOWED_PARAMS = new Set([
  "opportunity_slug",
  "opportunity_id",
  "opportunity_type",
  "strategy_slug",
  "strategy_id",
  "ranking_slug",
  "destination_slug",
  "target_url_kind",
  "referral_status",
  "commercial_relationship",
  "is_affiliate",
  "placement",
  "source_page",
  "page_path",
  "snapshot_id",
  "snapshot_timestamp",
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "capital_min",
  "capital_max",
  "confidence_min",
  "risk_max",
  "game_id",
  "chain",
  "economy_type",
]);
const SENSITIVE_ANALYTICS_KEY_PATTERN = /(authorization|cookie|password|passwd|secret|token|api[_-]?key|credential|wallet|private|signature|body|payload)/i;
let initializedAnalyticsId = null;
let initializedProductAnalyticsKey = null;
let initializedSentryDsn = null;
let lastTrackedPage = null;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet(path, fetcher = fetch, timeoutMs = 10000) {
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  let timeoutHandle;
  try {
    const response = await Promise.race([
      fetcher(`${API_BASE}${path}`, {
        headers: { Accept: "application/json" },
        ...(controller ? { signal: controller.signal } : {}),
      }),
      new Promise((_, reject) => {
        timeoutHandle = setTimeout(() => {
          controller?.abort();
          reject(new ApiError(503, "The data service did not respond in time. Please retry."));
        }, timeoutMs);
      }),
    ]);
    clearTimeout(timeoutHandle);
    if (!response.ok) {
      let message = `API request failed with status ${response.status}`;
      try {
        const payload = await response.json();
        if (payload.detail) {
          message = payload.detail;
        }
      } catch {
        message = response.statusText || message;
      }
      throw new ApiError(response.status, message);
    }
    return response.json();
  } catch (error) {
    clearTimeout(timeoutHandle);
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(503, "The data service is temporarily unavailable. Please retry.");
  }
}

export function buildRankingsPath(filters = {}) {
  const params = new URLSearchParams();
  addParam(params, "capital_min", filters.capitalMin);
  addParam(params, "capital_max", filters.capitalMax);
  addParam(params, "confidence_min", filters.confidenceMin);
  addParam(params, "risk_max", filters.riskMax);
  addParam(params, "game_id", filters.gameId);
  addParam(params, "opportunity_id", filters.opportunityId);
  addParam(params, "opportunity_type", filters.opportunityType);
  addParam(params, "chain", filters.chain);
  addParam(params, "economy_type", filters.economyType);
  const query = params.toString();
  return `/rankings${query ? `?${query}` : ""}`;
}

export function curatedRankingQuery(path, currentSearch = "") {
  const params = new URLSearchParams(CURATED_RANKING_FILTERS[path] || "");
  const incoming = new URLSearchParams(currentSearch);
  for (const [key, value] of incoming.entries()) {
    if (RANKING_FILTER_KEYS.has(key)) {
      params.set(key, value);
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function applyCuratedRankingConstraints(rankings, opportunities = [], path = "") {
  const constraints = CURATED_RANKING_CONSTRAINTS[path];
  if (!constraints) {
    return rankings;
  }
  const opportunitiesById = new Map((opportunities || []).map((opportunity) => [opportunity.opportunity_id, opportunity]));
  const required = constraints.requiredPlatforms || [];
  const excluded = constraints.excludedPlatforms || [];
  const items = (rankings.items || [])
    .filter((item) => {
      const opportunity = opportunitiesById.get(item.strategy?.opportunity_id || item.strategy?.game_id);
      const platforms = new Set(opportunity?.platforms || []);
      if (required.length > 0 && !required.some((platform) => platforms.has(platform))) {
        return false;
      }
      if (excluded.some((platform) => platforms.has(platform))) {
        return false;
      }
      return true;
    })
    .map((item, index) => ({ ...item, rank: index + 1 }));
  return {
    ...rankings,
    items,
    page: { ...(rankings.page || {}), offset: 0, total: items.length },
  };
}

export function renderHomeShell(games = [], rankings = { items: [], page: { total: 0 } }, opportunities = [], degradedMessages = []) {
  const economyOptions = Array.from(new Set(games.flatMap((game) => game.economy_types || []))).sort();
  const opportunityTypeOptions = Array.from(new Set(opportunities.map((opportunity) => opportunity.opportunity_type))).sort();
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">GamCryp public beta</p>
        <h1>Find Web3 earning opportunities with evidence behind them.</h1>
        <p class="lede">GamCryp tracks Web3 earning opportunities. When rewards and exits can be priced reproducibly, we calculate modeled ROI. When they cannot, we show why instead of inventing a number.</p>
        <div class="hero-proof-points" aria-label="GamCryp data principles">
          <span>Modeled ROI where reproducible</span>
          <span>Risk and confidence separated</span>
          <span>Freshness stays visible</span>
        </div>
      </section>
      ${renderDegradedNotice(degradedMessages)}
      ${renderTopRankingSummary(rankings)}
      ${renderCatalogStats(rankings, opportunities)}
      <section class="finder-grid" aria-label="ROI finder">
        <div id="finder-results">
          ${renderRankingsTable(rankings, { compact: true, groupByOpportunity: true })}
        </div>
        <form class="tool-panel filter-panel" id="finder-form">
          <div class="filter-panel-head">
            <h2>Filters</h2>
            <p class="muted">Organic ranking order still comes from the API.</p>
          </div>
          <div class="form-grid">
            <div class="field">
              <label for="capital-max">Capital budget</label>
              <input id="capital-max" name="capitalMax" inputmode="decimal" placeholder="Example: 20.00">
            </div>
            <div class="field">
              <label for="risk-max">Maximum risk</label>
              <div class="range-row">
                <input id="risk-max" name="riskMax" type="range" min="0" max="100" value="100">
                <output for="risk-max" id="risk-output">100</output>
              </div>
            </div>
            <div class="field">
              <label for="confidence-min">Minimum confidence</label>
              <div class="range-row">
                <input id="confidence-min" name="confidenceMin" type="range" min="0" max="100" value="0">
                <output for="confidence-min" id="confidence-output">0</output>
              </div>
            </div>
            <div class="field">
              <label for="game-id">Game</label>
              <select id="game-id" name="gameId">
                <option value="">Any modeled game</option>
                ${games.map((game) => `<option value="${escapeHtml(game.game_id)}">${escapeHtml(game.name)}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label for="opportunity-type">Opportunity type</label>
              <select id="opportunity-type" name="opportunityType">
                <option value="">Any opportunity type</option>
                ${opportunityTypeOptions.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(opportunityTypeLabel(value))}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label for="economy-type">Economy type</label>
              <select id="economy-type" name="economyType">
                <option value="">Any modeled economy</option>
                ${economyOptions.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(labelize(value))}</option>`).join("")}
              </select>
            </div>
          </div>
          <div class="button-row">
            <button class="button" type="submit">Apply filters</button>
            <a class="secondary-button" href="/rankings" data-link>Open rankings</a>
          </div>
        </form>
      </section>
      ${renderOpportunityList(opportunities, { compact: true })}
    </div>
  `;
}

export function renderCatalogStats(rankings = { page: { total: 0 } }, opportunities = []) {
  const opportunityCount = opportunities.length;
  const modeledCount = rankings.page?.total ?? (rankings.items || []).length;
  const unavailableCount = opportunities.filter((opportunity) => !opportunity.strategy_count).length;
  const types = new Set();
  for (const opportunity of opportunities) {
    const normalized = String(opportunity.opportunity_type || "").toUpperCase();
    if (normalized === "GAME") types.add("Games");
    if (normalized === "DEPIN_NODE") {
      types.add("DePIN");
      types.add("Nodes");
    }
    if (normalized === "POINTS") types.add("Points");
  }
  return `
    <section class="catalog-stat-grid" aria-label="GamCryp V1 coverage">
      ${summaryItem("Reviewed opportunities", escapeHtml(String(opportunityCount)))}
      ${summaryItem("Modeled strategies", escapeHtml(String(modeledCount)))}
      ${summaryItem("Opportunity coverage", escapeHtml(Array.from(types).join(" · ") || "Unavailable"))}
      ${summaryItem("ROI not measured", escapeHtml(`${unavailableCount} explicit`))}
    </section>
  `;
}

export function renderTopRankingSummary(rankings = { items: [] }) {
  const top = (rankings.items || [])[0];
  if (!top) {
    return "";
  }
  const snapshot = top.latest_snapshot;
  const strategy = top.strategy;
  const strategyClickAnalytics = productClickAttributes("ranking_to_strategy_click", {
    opportunityId: strategy.opportunity_id || strategy.game_id,
    opportunityType: snapshot.opportunity_type,
    strategyId: strategy.strategy_id,
    rankingSlug: "home",
    snapshot,
    sourcePage: "home",
    placement: "top_opportunity",
  });
  return `
    <section class="top-opportunity-card" aria-label="Top ranked organic strategy">
      <div class="top-opportunity-copy">
        <span class="eyebrow">${snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh" ? "Top opportunity (stale model)" : "Top opportunity"}</span>
        <div class="card-identity">${renderOpportunityLogo(strategy.logo, snapshot.game_name, true)}<h2>${escapeHtml(snapshot.game_name)}</h2></div>
        <p><a class="strategy-link" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>${escapeHtml(strategy.name)}</a></p>
        <p class="muted">Ranked by modeled 30D ROI, then confidence, risk, and recency according to the organic ranking methodology.</p>
        ${renderStrategySignals(snapshot)}
        <p class="updated-note">${formatUpdatedAge(snapshot.calculated_at)} · Organic ranking</p>
        ${renderCtaRiskNotice(snapshot)}
      </div>
      <div class="choice-metrics">
        ${summaryItem("Estimated starting capital", formatMoney(snapshot.capital.total_capital))}
        ${summaryItem("Estimated net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        ${summaryItem("30-day modeled ROI", formatRatio(snapshot.roi.roi_total_30d))}
      </div>
      <div class="top-opportunity-actions">
        <a class="secondary-button" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link${strategyClickAnalytics}>View strategy</a>
        ${renderDestinationButton(strategy.primary_destination, ctaLabelForSnapshot(snapshot, "Start"), { sourcePage: "home", placement: "top_opportunity" })}
      </div>
    </section>
  `;
}

export function renderDegradedNotice(messages = []) {
  const unique = Array.from(new Set(messages.filter(Boolean).map(String)));
  if (!unique.length) {
    return "";
  }
  return `<section class="error-state" role="status"><strong>Some stored data is temporarily unavailable.</strong><p>${escapeHtml(unique.join(" "))} The page remains usable with the data that loaded successfully.</p></section>`;
}

export function renderRankingsAnswerBlock(rankings = { items: [], page: { total: 0 } }, options = {}) {
  const fields = [
    ["Comparison page", escapeHtml(options.title || "Strategy rankings")],
    ["Matching modeled strategies", escapeHtml(String(rankings.page?.total ?? (rankings.items || []).length))],
    ["Ranking basis", "30D ROI descending, confidence descending, risk ascending, latest calculation descending, then strategy id."],
    ["Filters", escapeHtml(filterSummary(options.filters || ""))],
    ["Last snapshot update", escapeHtml(latestSnapshotTime(rankings))],
    ["Commercial policy", "Referral, affiliate, and sponsor metadata never changes organic ranking order or analytical scores."],
  ];
  return renderAnswerBlock("Quick comparison", rankingsSummary(rankings), fields);
}

export function renderOpportunityAnswerBlock(opportunity) {
  const strategies = opportunity.strategies || [];
  const strategy = strategies.find((item) => item.latest_snapshot) || strategies[0];
  const snapshot = strategy?.latest_snapshot;
  if (strategy && snapshot) {
    const fields = strategyAnswerFields(strategy, snapshot);
    fields.unshift(["Opportunity page", escapeHtml(opportunity.name)]);
    return renderAnswerBlock("Quick opportunity summary", rankingAnswer(snapshot, strategy), fields);
  }
  const destination = opportunity.primary_destination;
  const fields = [
    ["Opportunity", escapeHtml(opportunity.name)],
    ["Opportunity type", escapeHtml(opportunityTypeLabel(opportunity.opportunity_type))],
    ["ROI status", escapeHtml(valueStatusText(opportunity.value_realization_status, opportunity.strategy_count))],
    ["Review state", escapeHtml(feasibilityLabel(opportunity.data_feasibility_status))],
    ["Reward type", escapeHtml((opportunity.reward_asset_or_points_type || []).join(", ") || "Unspecified")],
    ["Value route", escapeHtml(plainUnavailableReason(opportunity))],
    ["Modeled strategies", escapeHtml(String(opportunity.strategy_count || 0))],
    ["Reviewed outbound link", escapeHtml(destination ? `${destination.label}; ${destination.verification_status}; reviewed ${formatDateTime(destination.reviewed_at)}` : "No reviewed outbound destination.")],
  ];
  return renderAnswerBlock("Quick opportunity summary", `ROI for ${opportunity.name} is not measurable yet. ${plainUnavailableReason(opportunity)}`, fields);
}


export function renderOpportunityHumanSummary(opportunity) {
  const strategies = opportunity.strategies || [];
  const primaryStrategy = strategies.find((item) => item.latest_snapshot) || strategies[0];
  const rewardTypes = humanList(opportunity.reward_asset_or_points_type, "Reward type not specified yet");
  const access = humanList([...(opportunity.platforms || []), ...(opportunity.chains || [])], "Check the official project page for access requirements");
  const modeled = opportunity.strategy_count > 0 && primaryStrategy?.latest_snapshot;
  const items = [
    ["What it is", escapeHtml(`${opportunity.name} is tracked as ${opportunityTypeLabel(opportunity.opportunity_type).toLowerCase()}.`)],
    ["How it may earn", escapeHtml(rewardTypes)],
    ["What you need", escapeHtml(access)],
    ["Cost and return", modeled ? `Modeled in ${escapeHtml(primaryStrategy.name)}; open the strategy for current capital, costs, and ROI.` : "No financial model is published yet; see the evidence gap below."],
    ["Cash-out", modeled ? "Realizable value is modeled inside the strategy snapshot where market data supports it." : "A payout route is not modeled yet; do not treat the reward as cash."],
    ["Main catch", escapeHtml(opportunity.data_feasibility_status === "GO" ? "Review risk, confidence, and freshness before acting." : "Review the evidence and limitations before acting.")],
  ];
  return renderHumanSummary("Plain-language summary", items);
}

export function renderStrategyHumanSummary(strategy, snapshot) {
  const items = [
    ["What it is", escapeHtml(`${strategy.name} is a modeled strategy for ${strategy.game_name}.`)],
    ["How it may earn", escapeHtml(`${labelize(strategy.economy_type)} economics are converted into the generic ROI model.`)],
    ["What you need", `Estimated starting capital is ${formatMoney(snapshot.capital.total_capital)}.`],
    ["Expected return", `${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })} estimated net earnings and ${formatRatio(snapshot.roi.roi_total_30d)} modeled 30-day ROI.`],
    ["Cash-out", `Recoverable value: ${formatMoney(snapshot.capital.recoverable_capital)}. Exit-adjusted P&L: ${formatMoney(snapshot.roi.exit_adjusted_pnl)}.`],
    ["Main catch", escapeHtml(strategyRiskSummary(snapshot))],
  ];
  return renderHumanSummary("Plain-language summary", items);
}

function renderHumanSummary(title, items) {
  return `
    <section class="section-panel human-summary">
      <div class="section-header"><h2>${escapeHtml(title)}</h2></div>
      <div class="section-body human-summary-grid">
        ${items.map(([label, value]) => `<article class="human-line"><span>${escapeHtml(label)}</span><p>${value}</p></article>`).join("")}
      </div>
    </section>
  `;
}

function humanList(values = [], fallback) {
  const labels = values.map((value) => labelize(value)).filter(Boolean);
  return labels.length ? labels.join(", ") : fallback;
}

export function depinSetupLabels(opportunityOrPlatforms) {
  const opportunity = Array.isArray(opportunityOrPlatforms) ? null : opportunityOrPlatforms;
  if (opportunity && String(opportunity.opportunity_type || "").toUpperCase() !== "DEPIN_NODE") {
    return [];
  }
  const platforms = Array.isArray(opportunityOrPlatforms) ? opportunityOrPlatforms : (opportunity?.platforms || []);
  const labels = [];
  const add = (label) => { if (!labels.includes(label)) labels.push(label); };
  for (const value of platforms) {
    const normalized = String(value || "").toLowerCase();
    if (normalized === "hardware-node") add("Dedicated hardware");
    else if (["browser-extension", "extension"].includes(normalized)) add("Browser / extension");
    else if (["desktop-node", "docker-node", "node", "cli"].includes(normalized)) add("Node software");
    else if (["desktop", "pc"].includes(normalized)) add("Existing PC");
    else if (normalized === "web") add("Web-only");
  }
  return labels;
}

export function renderDepinSetupSummary(opportunity) {
  if (String(opportunity?.opportunity_type || "").toUpperCase() !== "DEPIN_NODE") {
    return "";
  }
  const labels = depinSetupLabels(opportunity);
  if (!labels.length) {
    return "";
  }
  return `<section class="section-panel depin-setup"><div class="section-header"><h2>Setup at a glance</h2></div><div class="section-body"><p>${escapeHtml(labels.join("; "))}</p></div></section>`;
}

function strategyRiskSummary(snapshot) {
  if (snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh") {
    return "The latest stored data is stale, so treat the result as outdated until a fresh snapshot appears.";
  }
  if (snapshot.risk?.available && ["HIGH", "VERY HIGH"].includes(snapshot.risk.label)) {
    return `${publicScoreLabel(snapshot.risk.label)} risk: this CTA opens the project, not a recommendation to start.`;
  }
  if (snapshot.confidence?.available && snapshot.confidence.label === "LOW") {
    return "Low confidence means the calculation depends on weaker or incomplete evidence.";
  }
  if ((snapshot.warnings || []).length) {
    return snapshot.warnings[0].message;
  }
  return "No critical warning is attached, but ROI is still an estimate rather than a promise.";
}

function isElevatedRisk(snapshot) {
  return snapshot?.risk?.available && ["HIGH", "VERY HIGH"].includes(snapshot.risk.label);
}

function ctaLabelForSnapshot(snapshot, fallback = "Start") {
  return isElevatedRisk(snapshot) ? "Open project" : fallback;
}

function renderCtaRiskNotice(snapshot) {
  if (!isElevatedRisk(snapshot)) {
    return "";
  }
  return '<p class="cta-risk-note">High-risk strategy. Opening the project is not a recommendation; review the assumptions first.</p>';
}

export function renderStrategyAnswerBlock(strategy, snapshot) {
  if (!snapshot) {
    return renderAnswerBlock("Quick strategy summary", `${strategy.name} has no successful stored calculation yet.`, [
      ["Strategy", escapeHtml(strategy.name)],
      ["Strategy version", escapeHtml(strategy.strategy_version)],
      ["Opportunity", escapeHtml(strategy.game_name)],
      ["Opportunity type", escapeHtml(opportunityTypeLabel(strategy.opportunity_type))],
      ["ROI status", "No successful stored calculation yet."],
    ]);
  }
  return renderAnswerBlock("Quick strategy summary", rankingAnswer(snapshot, strategy), strategyAnswerFields(strategy, snapshot));
}

function strategyAnswerFields(strategy, snapshot) {
  return [
    ["Opportunity", escapeHtml(strategy.game_name)],
    ["Opportunity type", escapeHtml(opportunityTypeLabel(strategy.opportunity_type))],
    ["Strategy", escapeHtml(strategy.name)],
    ["Strategy version", escapeHtml(strategy.strategy_version)],
    ["Starting capital", formatMoney(snapshot.capital.total_capital)],
    ["Estimated gross earnings/day", formatMoney(snapshot.earnings.gross_nominal_earnings_day, { perDay: true })],
    ["Estimated realizable earnings/day", formatMoney(snapshot.earnings.realizable_earnings_day, { perDay: true })],
    ["Estimated net earnings/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })],
    ["30D ROI", formatRatio(snapshot.roi.roi_total_30d)],
    ["Break-even", formatBreakEven(snapshot.roi.break_even)],
    ["Risk", escapeHtml(scoreText(snapshot.risk))],
    ["Confidence", escapeHtml(scoreText(snapshot.confidence))],
    ["Data status", escapeHtml(labelize(snapshot.freshness?.overall_status || "unknown"))],
    ["Snapshot timestamp", formatDateTime(snapshot.calculated_at)],
    ["Required time/effort", "Not separately quantified in this strategy snapshot."],
    ["Major assumptions", escapeHtml(majorAssumptions(snapshot))],
    ["Warnings", escapeHtml(warningSummary(snapshot.warnings || []))],
  ];
}

function renderAnswerBlock(title, summary, fields) {
  return `
    <section class="answer-card" data-ai-answer-block="true">
      <div class="section-header"><h2>${escapeHtml(title)}</h2><span class="badge info">Evidence-linked</span></div>
      <div class="section-body">
        <p class="answer-summary">${escapeHtml(summary)}</p>
        <dl class="answer-grid">
          ${fields.map(([label, value]) => `<div class="answer-item"><dt>${escapeHtml(label)}</dt><dd>${value}</dd></div>`).join("")}
        </dl>
      </div>
    </section>
  `;
}

function rankingsSummary(rankings = { items: [] }) {
  const top = (rankings.items || [])[0];
  if (!top) {
    return "No successful stored strategy snapshots currently match this page.";
  }
  return rankingAnswer(top.latest_snapshot, top.strategy);
}

function rankingAnswer(snapshot, strategy) {
  const stale = String(snapshot.freshness?.overall_status || "unknown").toLowerCase() !== "fresh";
  const lead = stale ? "GamCryp's model estimates" : "GamCryp models";
  const freshnessNote = stale ? " This model is stale; review the source dates before acting." : "";
  return `${lead} ${strategy.name} at ${textFromHtml(formatRatio(snapshot.roi.roi_total_30d))} 30-day ROI using ${textFromHtml(formatMoney(snapshot.capital.total_capital))} capital. Estimated net earnings are ${textFromHtml(formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}. Risk is ${scoreText(snapshot.risk)} and Confidence is ${scoreText(snapshot.confidence)}. Latest model calculation was recorded at ${formatDateTime(snapshot.calculated_at)}.${freshnessNote}`;
}

function latestSnapshotTime(rankings = { items: [] }) {
  const times = (rankings.items || [])
    .map((item) => item.latest_snapshot?.calculated_at)
    .filter(Boolean)
    .sort();
  return times.length ? formatDateTime(times[times.length - 1]) : "Unavailable";
}

function filterSummary(query) {
  const params = new URLSearchParams(query);
  if (![...params.keys()].length) {
    return "No additional filters.";
  }
  const labels = [];
  if (params.has("opportunity_type")) {
    labels.push(`Opportunity type: ${opportunityTypeLabel(params.get("opportunity_type"))}`);
  }
  if (params.has("capital_max")) {
    labels.push(`Capital up to $${params.get("capital_max")}`);
  }
  if (params.has("capital_min")) {
    labels.push(`Capital at least $${params.get("capital_min")}`);
  }
  if (params.has("confidence_min")) {
    labels.push(`Confidence at least ${params.get("confidence_min")}`);
  }
  if (params.has("risk_max")) {
    labels.push(`Risk up to ${params.get("risk_max")}`);
  }
  return labels.join("; ") || "Filtered organic strategy results.";
}

function majorAssumptions(snapshot) {
  const counts = snapshot.classification_summary?.counts || {};
  return `${counts.LIVE ?? 0} live observations, ${counts.CONFIG ?? 0} configured assumptions, and ${counts.DERIVED ?? 0} derived metrics are attached to this snapshot.`;
}

function warningSummary(warnings = []) {
  if (!warnings.length) {
    return "No warnings attached.";
  }
  return warnings.slice(0, 2).map((warning) => warning.message).join(" ");
}

function textFromHtml(html) {
  return String(html)
    .replace(/<[^>]*>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

export function renderRankingsPage(rankings, options = {}) {
  const title = options.title || "Strategy rankings";
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Organic rankings</p>
        <h1>${escapeHtml(title)}</h1>
        <p class="lede">Ranked by modeled 30-day ROI, then confidence, risk, and recency. Brand or referral metadata never changes this order.</p>
      </section>
      ${renderRankingsAnswerBlock(rankings, { title })}
      ${renderCuratedRankingLinks()}
      ${renderRankingsTable(rankings)}
      ${renderSponsoredPlacements(rankings.sponsored_placements || [])}
    </div>
  `;
}

function renderCuratedRankingLinks() {
  return `
    <section class="section-panel">
      <div class="section-header"><h2>Curated views</h2></div>
      <div class="section-body button-row">
        ${Object.entries(CURATED_RANKING_TITLES)
          .map(([path, title]) => `<a class="secondary-button" href="${escapeHtml(path)}" data-link>${escapeHtml(title)}</a>`)
          .join("")}
      </div>
    </section>
  `;
}
export function renderOpportunitiesPage(opportunitiesPage = { items: [], page: { total: 0 } }) {
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Opportunity radar</p>
        <h1>Games, nodes, and points programs under review.</h1>
        <p class="lede">GamCryp keeps modeled strategies and watchlist candidates in one taxonomy. Points-only or future-claim programs stay marked unavailable until value is lawful and reproducible.</p>
      </section>
      ${renderOpportunityList(opportunitiesPage.items || [])}
    </div>
  `;
}

export function renderOpportunityDetail(opportunity) {
  const hasStrategies = (opportunity.strategies || []).length > 0;
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">${escapeHtml(opportunityTypeLabel(opportunity.opportunity_type))}</p>
        <div class="identity-heading">${renderOpportunityLogo(opportunity.logo, opportunity.name)}<h1>${escapeHtml(opportunity.name)}</h1></div>
        <p class="lede">${escapeHtml(opportunityIntro(opportunity))}</p>
        <div class="button-row">
          ${renderDestinationButton(opportunity.primary_destination, opportunity.opportunity_type === "GAME" ? "Start" : "Open", { sourcePage: "opportunity_detail", placement: "primary_cta" })}
        </div>
      </section>
      ${renderOpportunityAnswerBlock(opportunity)}
      ${renderOpportunityHumanSummary(opportunity)}
      ${renderDepinSetupSummary(opportunity)}
      ${renderOpportunityGuidance(opportunity.guidance, opportunity)}
      <section class="game-grid">
        <div class="game-card">
          <h3>Opportunity type</h3>
          <p>${escapeHtml(opportunityTypeLabel(opportunity.opportunity_type))}</p>
          <p class="muted">${escapeHtml(opportunityTypeDescription(opportunity.opportunity_type))}</p>
        </div>
        <div class="game-card">
          <h3>ROI status</h3>
          <p>${renderValueStatus(opportunity.value_realization_status, opportunity.strategy_count)}</p>
        </div>
        <div class="game-card">
          <h3>Review state</h3>
          <p>${renderFeasibilityStatus(opportunity.data_feasibility_status)}</p>
        </div>
        <div class="game-card">
          <h3>Reward type</h3>
          <p>${escapeHtml((opportunity.reward_asset_or_points_type || []).join(", ") || "Unspecified")}</p>
        </div>
      </section>
      ${
        hasStrategies
          ? renderStrategyList(opportunity.strategies, { clickEvent: "opportunity_to_strategy_click", rankingSlug: "opportunity_detail", heading: "Strategies in this opportunity" })
          : renderUnavailableRoiExplanation(opportunity)
      }
      <section class="section-panel">
        <div class="section-header"><h2>Sources and Outbound Links</h2></div>
        <div class="section-body contributor-list">
          ${(opportunity.official_source_references || []).map((source) => `<article class="contributor"><strong>${escapeHtml(source.label)}</strong><a href="${escapeHtml(source.url)}" rel="noopener noreferrer" target="_blank">${escapeHtml(source.url)}</a></article>`).join("")}
          ${(opportunity.outbound_destinations || []).map(renderDestinationDisclosure).join("")}
        </div>
      </section>
    </div>
  `;
}

export function renderUnavailableRoiExplanation(opportunity) {
  const explanation = opportunity?.roi_unavailable;
  if (!explanation) {
    return `<section class="empty-state"><h2>ROI not measurable yet</h2><p class="muted">${escapeHtml(unavailableRoiReason(opportunity || {}))}</p></section>`;
  }
  const details = [
    ["What is missing", explanation.missing_evidence],
    ["What would make it modelable", explanation.modeling_requirements],
  ].map(([heading, items]) => {
    const values = (Array.isArray(items) ? items : []).map((item) => String(item || "").trim()).filter(Boolean);
    return values.length ? `<div class="roi-unavailable-detail"><h3>${escapeHtml(heading)}</h3><ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>` : "";
  }).join("");
  return `<section class="section-panel roi-unavailable"><div class="section-header"><h2>Why ROI is unavailable</h2></div><div class="section-body"><p class="roi-unavailable-reason">${escapeHtml(String(explanation.reason || "").trim())}</p>${details}</div></section>`;
}

export function renderOpportunityGuidance(guidance, opportunity = null) {
  const valuesFor = (items) => (Array.isArray(items) ? items : []).map((item) => String(item || "").trim()).filter(Boolean);
  const sections = [
    ["How to start", guidance?.how_to_start],
    ["What you need", guidance?.what_you_need],
    ["How you earn", guidance?.how_you_earn],
    ["How to claim or exit", guidance?.how_to_exit_or_claim],
  ].map(([heading, items]) => {
    const values = valuesFor(items);
    if (!values.length) {
      return "";
    }
    return `<article class="human-line"><h3>${escapeHtml(heading)}</h3><ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></article>`;
  }).join("");
  const fallback = !sections && opportunity ? renderEvidenceBoundGuide(opportunity) : "";
  const resourceLinks = renderOfficialGuideLinks(opportunity?.official_source_references || []);
  if (!sections && !fallback && !resourceLinks) {
    return "";
  }
  return `<section class="section-panel opportunity-guidance"><div class="section-header"><h2>Practical guide</h2><span class="badge info">Evidence-linked</span></div><div class="section-body human-summary-grid">${sections || fallback}${resourceLinks}</div></section>`;
}

function renderEvidenceBoundGuide(opportunity) {
  const sources = opportunity.official_source_references || [];
  const firstSource = sources[0]?.label || "the official project documentation";
  const platforms = humanList([...(opportunity.platforms || []), ...(opportunity.chains || [])], "Exact setup requirements are not fully structured in the current evidence.");
  const rewards = humanList(opportunity.reward_asset_or_points_type, "The reward or points type is not specified in the current evidence.");
  const realizable = opportunity.value_realization_status === "realizable";
    return [
      ["How to start", `Start with ${firstSource}; confirm current eligibility, region, and operating rules before using the project.`],
      ["What you need", platforms],
      ["How you earn", `${rewards}. The catalog does not establish a guaranteed earning rate or fixed time to first reward.`],
      ["How to claim or exit", realizable
        ? "A value route is marked as realizable, but current payout and withdrawal conditions must be checked in the official references below."
        : "A reproducible payout or claim route is not verified yet. Do not treat points or future claims as cash."],
    ].map(([heading, value]) => `<article class="human-line"><h3>${escapeHtml(heading)}</h3><p>${escapeHtml(value)}</p></article>`).join("");
}

function renderOfficialGuideLinks(sources) {
  const links = (Array.isArray(sources) ? sources : []).filter((source) => source?.url && source?.label);
  if (!links.length) {
    return "";
  }
  return `<div class="guide-resources"><h3>Official guides and references</h3><div class="guide-resource-grid">${links.map((source) => `<a class="guide-resource" href="${escapeHtml(source.url)}" rel="noopener noreferrer" target="_blank"><span>${escapeHtml(guideResourceKind(source.label, source.url))}</span><strong>${escapeHtml(source.label)}</strong></a>`).join("")}</div></div>`;
}

function guideResourceKind(label, url) {
  const value = `${label} ${url}`.toLowerCase();
  if (value.includes("youtube") || value.includes("video")) return "Video";
  if (/(start|setup|install|onboard|getting|how to)/.test(value)) return "Start here";
  if (/(earn|reward|payout|claim|withdraw|payment|token|econom)/.test(value)) return "Earnings / payout";
  return "Official reference";
}

export function renderOpportunityList(opportunities = [], options = {}) {
  if (!opportunities.length) {
    return "";
  }
  const heading = options.compact ? "Opportunity radar" : "Opportunity catalog";
  return `
    <section class="section-panel opportunity-section">
      <div class="section-header">
        <h2>${heading}</h2>
        <span class="badge info">${escapeHtml(String(opportunities.length))} reviewed</span>
      </div>
      <div class="opportunity-grid">
        ${opportunities.map(renderOpportunityCard).join("")}
      </div>
    </section>
  `;
}

export function renderOpportunityCard(opportunity) {
  const strategyText = opportunity.strategy_count > 0
    ? `${escapeHtml(String(opportunity.strategy_count))} modeled strateg${opportunity.strategy_count === 1 ? "y" : "ies"}`
    : opportunityCardState(opportunity);
  const rewardTypes = (opportunity.reward_asset_or_points_type || []).join(", ") || "Unspecified";
  const roiText = opportunity.strategy_count > 0 && opportunity.value_realization_status === "realizable"
    ? '<span class="badge good">ROI modeled</span>'
    : `<span class="badge warning">${escapeHtml(opportunityCardState(opportunity))}</span>`;
  const setupLabels = depinSetupLabels(opportunity);
  return `
    <article class="opportunity-card">
      <div class="identity-row">
        <span class="badge info">${escapeHtml(opportunityTypeLabel(opportunity.opportunity_type))}</span>
        ${renderFeasibilityStatus(opportunity.data_feasibility_status)}
      </div>
      <div class="card-identity">${renderOpportunityLogo(opportunity.logo, opportunity.name, true)}<h3><a class="strategy-link" href="/opportunities/${encodeURIComponent(opportunity.opportunity_id)}" data-link>${escapeHtml(opportunity.name)}</a></h3></div>
      <p class="muted">${escapeHtml(opportunityIntro(opportunity))}</p>
      <p class="muted">${strategyText}</p>
      ${setupLabels.length ? `<p class="muted">Setup: ${escapeHtml(setupLabels.slice(0, 2).join("; "))}</p>` : ""}
      <div class="opportunity-facts">
        ${metricItem("Reward type", escapeHtml(rewardTypes))}
        ${metricItem("ROI status", roiText)}
      </div>
      <p class="muted watchlist-note">${opportunity.strategy_count > 0 ? "Review the modeled strategy for assumptions and current freshness." : escapeHtml(conciseUnavailableRoiReason(opportunity))}</p>
      <div class="card-actions">
        <a class="secondary-button" href="/opportunities/${encodeURIComponent(opportunity.opportunity_id)}" data-link${productClickAttributes("internal_compare_or_next_click", {
          opportunityId: opportunity.opportunity_id,
          opportunityType: opportunity.opportunity_type,
          sourcePage: "opportunity_watchlist",
          placement: "opportunity_card",
        })}>Learn more</a>
        ${renderDestinationButton(opportunity.primary_destination, "Open", { sourcePage: "opportunity_watchlist", placement: "opportunity_card" })}
      </div>
    </article>
  `;
}

export function renderRankingsTable(rankings, options = {}) {
  const items = rankings.items || [];
  if (!items.length) {
    return `
      <section class="empty-state">
        <h2>No matching rankings</h2>
        <p class="muted">No stored strategy snapshot matches these filters. Try relaxing capital, risk, confidence, game, or economy filters.</p>
      </section>
    `;
  }
  const groups = options.groupByOpportunity ? groupRankingItemsByOpportunity(items) : null;
  const cardMarkup = groups
    ? groups.map((group) => renderOpportunityRankingGroup(group)).join("")
    : items.map((item) => renderRankingCard(item, options)).join("");
  const countLabel = groups
    ? `${groups.length} opportunities · ${items.length} strategies`
    : `${rankings.page?.total ?? items.length} stored`;
  return `
    <section class="section-panel ranking-section">
      <div class="section-header">
        <h2>${escapeHtml(options.heading || (options.compact ? "Current matches" : "Ranked strategies"))}</h2>
        <span class="badge info">${escapeHtml(countLabel)}</span>
      </div>
      <div class="ranking-card-grid">
        ${cardMarkup}
      </div>
    </section>
  `;
}

function groupRankingItemsByOpportunity(items) {
  const groups = new Map();
  for (const item of items) {
    const key = item.strategy?.opportunity_id || item.strategy?.game_id || item.latest_snapshot?.game_name || item.strategy?.strategy_id;
    if (!groups.has(key)) {
      groups.set(key, { items: [] });
    }
    groups.get(key).items.push(item);
  }
  return Array.from(groups.values());
}

function renderOpportunityRankingGroup(group) {
  const primary = group.items[0];
  const snapshot = primary.latest_snapshot;
  const strategy = primary.strategy;
  const opportunityId = strategy.opportunity_id || strategy.game_id;
  return `
    <article class="ranking-card opportunity-group-card">
      <div class="ranking-card-head">
        <span class="rank-chip">#${escapeHtml(String(primary.rank))}</span>
        <div>
          <p class="ranking-parent"><span>Opportunity</span> ${renderOpportunityLogo(strategy.logo, snapshot.game_name, true)}</p>
          <h3><a class="game-link" href="/opportunities/${encodeURIComponent(opportunityId)}" data-link>${escapeHtml(snapshot.game_name)}</a></h3>
          <p class="muted">${group.items.length} modeled strateg${group.items.length === 1 ? "y" : "ies"}; choose an assumption set below.</p>
        </div>
      </div>
      ${renderStrategySignals(snapshot)}
      <div class="card-metrics">
        ${metricItem("Top strategy capital", formatMoney(snapshot.capital.total_capital))}
        ${metricItem("Top strategy net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        ${metricItem("Top strategy ROI", formatRatio(snapshot.roi.roi_total_30d))}
      </div>
      <div class="group-strategy-list" aria-label="Strategies for ${escapeHtml(snapshot.game_name)}">
        ${group.items.map((item) => `<a class="strategy-link group-strategy-link" href="/strategies/${encodeURIComponent(item.strategy.strategy_id)}" data-link>${escapeHtml(item.strategy.name)} <span class="muted">#${escapeHtml(String(item.rank))}</span></a>`).join("")}
      </div>
      <p class="muted ranking-context">Organic comparison, not a recommendation.</p>
      <div class="card-actions">
        <a class="secondary-button" href="/opportunities/${encodeURIComponent(opportunityId)}" data-link>View opportunity and strategies</a>
      </div>
    </article>
  `;
}

export function renderRankingCard(item, options = {}) {
  const snapshot = item.latest_snapshot;
  const strategy = item.strategy;
  const rankingSlug = options.rankingSlug || (options.compact ? "home" : "rankings");
  const strategyClickEvent = options.clickEvent || "ranking_to_strategy_click";
  const strategyClickAnalytics = productClickAttributes(strategyClickEvent, {
    opportunityId: strategy.opportunity_id || strategy.game_id,
    opportunityType: snapshot.opportunity_type,
    strategyId: strategy.strategy_id,
    rankingSlug,
    snapshot,
    sourcePage: rankingSlug,
    placement: "strategy_card",
  });
  return `
    <article class="ranking-card">
      <div class="ranking-card-head">
        <span class="rank-chip">#${escapeHtml(String(item.rank))}</span>
        <div>
          <p class="ranking-parent"><span>Opportunity</span> ${renderOpportunityLogo(strategy.logo, snapshot.game_name, true)} <a class="game-link" href="/opportunities/${encodeURIComponent(strategy.opportunity_id || strategy.game_id)}" data-link>${escapeHtml(snapshot.game_name)}</a></p>
          <h3><a class="strategy-link" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link${strategyClickAnalytics}>${escapeHtml(strategy.name)}</a></h3>
        </div>
      </div>
      ${renderStrategySignals(snapshot)}
      <div class="card-metrics">
        ${metricItem("Starting capital", formatMoney(snapshot.capital.total_capital))}
        ${metricItem("Net earning/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        ${metricItem("30-day ROI", formatRatio(snapshot.roi.roi_total_30d))}
        ${metricItem("Modeled break-even", formatBreakEven(snapshot.roi.break_even))}
      </div>
      ${renderNetEarningsInterpretation(snapshot)}
      <p class="muted ranking-context">Organic comparison, not a recommendation.</p>
      <div class="card-badges">
        ${renderScoreBadge(snapshot.confidence, "confidence")}
        ${renderScoreBadge(snapshot.risk, "risk")}
        ${renderFreshnessPill(snapshot.freshness, { hideFresh: true })}
        ${renderWarningsIndicator(snapshot.warnings, { hideEmpty: true })}
      </div>
      <p class="updated-note">${formatUpdatedAge(snapshot.calculated_at)}</p>
      ${renderCtaRiskNotice(snapshot)}
      <div class="card-actions">
        <a class="secondary-button" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link${strategyClickAnalytics}>View strategy</a>
        ${renderDestinationButton(strategy.primary_destination, ctaLabelForSnapshot(snapshot, "Start"), { sourcePage: rankingSlug, placement: "strategy_card" })}
      </div>
    </article>
  `;
}

export function renderRankingRow(item) {
  const snapshot = item.latest_snapshot;
  const strategy = item.strategy;
  return `
    <tr>
      <td class="metric">${escapeHtml(String(item.rank))}</td>
      <td><span class="ranking-parent-label">Opportunity</span> <a class="game-link" href="/opportunities/${encodeURIComponent(strategy.opportunity_id || strategy.game_id)}" data-link>${escapeHtml(snapshot.game_name)}</a></td>
      <td>
        <a class="strategy-link" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>${escapeHtml(strategy.name)}</a>
        <div class="muted">${escapeHtml(strategy.strategy_version)} | ${escapeHtml(strategy.economy_type)}</div>
      </td>
      <td class="metric">${formatMoney(snapshot.capital.total_capital)}</td>
      <td class="metric">${formatMoney(snapshot.earnings.net_earnings_day)}</td>
      <td class="metric">${formatRatio(snapshot.roi.roi_total_30d)}</td>
      <td class="metric">${formatBreakEven(snapshot.roi.break_even)}</td>
      <td>${renderScoreBadge(snapshot.confidence, "confidence")}</td>
      <td>${renderScoreBadge(snapshot.risk, "risk")}</td>
      <td>${renderFreshnessPill(snapshot.freshness)}</td>
      <td>${renderWarningsIndicator(snapshot.warnings)}</td>
    </tr>
  `;
}

export function renderGameDetail(game) {
  const strategies = game.strategies || [];
  const snapshot = strategies[0]?.latest_snapshot;
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Game detail</p>
        <div class="identity-heading">${renderOpportunityLogo(game.logo, game.name)}<h1>${escapeHtml(game.name)}</h1></div>
        <p class="lede">${escapeHtml(game.status)} game with ${escapeHtml(String(game.strategy_count))} modeled strategy.</p>
        <div class="button-row">
          ${renderDestinationButton(game.primary_destination, ctaLabelForSnapshot(snapshot, "Start"), { sourcePage: "game_detail", placement: "primary_cta" })}
          <a class="secondary-button" href="/opportunities/${encodeURIComponent(game.opportunity_id)}" data-link>Opportunity record</a>
        </div>
        ${renderCtaRiskNotice(snapshot)}
      </section>
      <section class="game-grid">
        <div class="game-card">
          <h3>Chains</h3>
          <p>${(game.chains || []).map(escapeHtml).join(", ")}</p>
        </div>
        <div class="game-card">
          <h3>Economy Types</h3>
          <p>${(game.economy_types || []).map((value) => escapeHtml(labelize(value))).join(", ")}</p>
        </div>
        <div class="game-card">
          <h3>Status</h3>
          <p>${escapeHtml(game.status)}</p>
        </div>
      </section>
      ${renderStrategyList(strategies, { heading: "Strategies in this game" })}
    </div>
  `;
}

export function renderStrategyList(strategies, options = {}) {
  if (!strategies.length) {
    return `
      <section class="empty-state">
        <h2>No strategies available</h2>
        <p class="muted">This game is in the catalog, but no strategy snapshots are currently available.</p>
      </section>
    `;
  }
  const rankings = {
    items: strategies
      .filter((strategy) => strategy.latest_snapshot)
      .map((strategy, index) => ({
        rank: index + 1,
        strategy,
        latest_snapshot: strategy.latest_snapshot,
      })),
    page: { total: strategies.length },
  };
  return renderRankingsTable(rankings, {
    rankingSlug: options.rankingSlug || "strategy_list",
    clickEvent: options.clickEvent || "ranking_to_strategy_click",
    heading: options.heading || "Strategies in this opportunity",
  });
}

export function renderStrategyDetail(strategy, historyPage = { items: [] }) {
  const snapshot = strategy.latest_snapshot;
  if (!snapshot) {
    return `
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Strategy detail</p>
          <div class="identity-heading">${renderOpportunityLogo(strategy.logo, strategy.game_name)}<div><p class="eyebrow">${escapeHtml(strategy.game_name)}</p><h1>${escapeHtml(strategy.name)}</h1></div></div>
        </section>
        <section class="empty-state">
          <h2>No stored snapshot</h2>
          <p class="muted">This strategy exists, but it has not produced a successful stored calculation yet.</p>
        </section>
      </div>
    `;
  }
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Strategy detail</p>
        <div class="identity-heading">${renderOpportunityLogo(strategy.logo, strategy.game_name)}<div><p class="eyebrow">${escapeHtml(strategy.game_name)}</p><h1>${escapeHtml(strategy.name)}</h1></div></div>
        <p class="lede">${escapeHtml(strategy.description)}</p>
        <div class="button-row">
          <span class="badge">Strategy version ${escapeHtml(strategy.strategy_version)}</span>
          <a class="secondary-button" href="/opportunities/${encodeURIComponent(strategy.opportunity_id || strategy.game_id)}" data-link>View opportunity</a>
          ${renderDestinationButton(strategy.primary_destination, ctaLabelForSnapshot(snapshot, "Start"), { sourcePage: "strategy_detail", placement: "primary_cta" })}
        </div>
        ${renderCtaRiskNotice(snapshot)}
      </section>
      ${renderStrategyAnswerBlock(strategy, snapshot)}
      ${renderStrategyHumanSummary(strategy, snapshot)}
      ${renderFreshnessAlert(snapshot)}
      ${renderStrategySignals(snapshot)}
      ${renderOverviewMetrics(snapshot)}
      <section class="section-panel">
        <div class="section-header"><h2>Capital Breakdown</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Estimated starting capital", formatMoney(snapshot.capital.total_capital))}
          ${metricItem("Sunk cost", formatMoney(snapshot.capital.sunk_cost))}
          ${metricItem("Recoverable capital", formatMoney(snapshot.capital.recoverable_capital))}
          ${metricItem("Capital at risk", formatMoney(snapshot.capital.capital_at_risk))}
        </div>
        <div class="section-body">
          <p class="muted">Sunk cost is modeled as non-recoverable, recoverable capital is the estimated exit value of assets, and locked capital remains exposed until the modeled exit route is available.</p>
        </div>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Earnings and Costs</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Gross nominal/day", formatMoney(snapshot.earnings.gross_nominal_earnings_day, { perDay: true }))}
          ${metricItem("Realizable/day", formatMoney(snapshot.earnings.realizable_earnings_day, { perDay: true }))}
          ${metricItem("Operating cost/day", formatMoney(snapshot.earnings.operating_cost_day, { perDay: true }))}
          ${metricItem("Transaction cost/day", formatMoney(snapshot.earnings.transaction_cost_day, { perDay: true }))}
          ${metricItem("Other cost/day", formatMoney(snapshot.earnings.other_cost_day, { perDay: true }))}
          ${metricItem("Estimated net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        </div>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Return Metrics</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Modeled break-even", formatBreakEven(snapshot.roi.break_even))}
          ${metricItem("ROI total 7D", formatRatio(snapshot.roi.roi_total_7d))}
          ${metricItem("30-day modeled ROI", formatRatio(snapshot.roi.roi_total_30d))}
          ${metricItem("ROI total 90D", formatRatio(snapshot.roi.roi_total_90d))}
          ${metricItem("ROI at-risk 7D", formatRatio(snapshot.roi.roi_risk_7d))}
          ${metricItem("ROI at-risk 30D", formatRatio(snapshot.roi.roi_risk_30d))}
          ${metricItem("ROI at-risk 90D", formatRatio(snapshot.roi.roi_risk_90d))}
          ${metricItem("Exit-adjusted P&L", formatMoney(snapshot.roi.exit_adjusted_pnl))}
        </div>
      </section>
      ${renderUncertainty(snapshot)}
      <section class="split-grid">
        ${renderScoreDetails(snapshot.confidence, "Confidence")}
        ${renderScoreDetails(snapshot.risk, "Risk")}
      </section>
      ${renderWarnings(snapshot.warnings)}
      ${renderHistory(historyPage)}
      ${renderAdvancedSnapshotDetails(strategy, snapshot)}
    </div>
  `;
}


function renderAdvancedSnapshotDetails(strategy, snapshot) {
  return `
    <details class="advanced-panel snapshot-advanced">
      <summary>Technical snapshot details</summary>
      <div class="advanced-panel-body">
        <section class="section-panel">
          <div class="section-header"><h2>Versions</h2></div>
          <div class="section-body metric-grid">
            ${metricItem("Strategy ID", escapeHtml(strategy.strategy_id))}
            ${metricItem("Adapter contract", snapshot.versions.adapter_contract_version)}
            ${metricItem("ROI model", snapshot.versions.model_version)}
            ${metricItem("Scoring methodology", snapshot.versions.scoring_methodology_version || "Unavailable")}
            ${metricItem("Last calculated", `${formatUpdatedAge(snapshot.calculated_at)} (${formatDateTime(snapshot.calculated_at)})`)}
          </div>
        </section>
        ${renderClassificationSummary(snapshot.classification_summary)}
      </div>
    </details>
  `;
}

function historyTrendSummary(items) {
  const latest = items[items.length - 1];
  const previous = items[items.length - 2];
  const comparison = compareDecimalMetric(latest.roi?.roi_total_30d?.value, previous.roi?.roi_total_30d?.value);
  const latestRoi = textFromHtml(formatRatio(latest.roi.roi_total_30d));
  const previousRoi = textFromHtml(formatRatio(previous.roi.roi_total_30d));
  if (comparison > 0) {
    return `Recent 30-day ROI moved up from ${previousRoi} to ${latestRoi}.`;
  }
  if (comparison < 0) {
    return `Recent 30-day ROI moved down from ${previousRoi} to ${latestRoi}.`;
  }
  return `Recent 30-day ROI is unchanged at ${latestRoi}.`;
}

function compareDecimalMetric(left, right) {
  if (left === null || left === undefined || right === null || right === undefined) {
    return 0;
  }
  const leftNormalized = normalizeDecimalString(String(left));
  const rightNormalized = normalizeDecimalString(String(right));
  const leftSign = decimalSign(leftNormalized);
  const rightSign = decimalSign(rightNormalized);
  if (leftSign !== rightSign) {
    return leftSign > rightSign ? 1 : -1;
  }
  const comparison = comparePositiveDecimals(leftNormalized.replace(/^-/, ""), rightNormalized.replace(/^-/, ""));
  return leftSign < 0 ? comparison * -1 : comparison;
}

function historyBarHeight(value) {
  const normalized = normalizeDecimalString(String(value ?? "0"));
  const absolute = normalized.startsWith("-") ? normalized.slice(1) : normalized;
  if (!absolute || decimalSign(absolute) === 0) {
    return 12;
  }
  const buckets = [
    ["0.20", 92],
    ["0.10", 78],
    ["0.05", 64],
    ["0.02", 48],
    ["0.01", 36],
    ["0.001", 24],
  ];
  const match = buckets.find(([threshold]) => comparePositiveDecimals(absolute, threshold) >= 0);
  return match ? match[1] : 16;
}

function formatHistoryShortDate(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Date unavailable";
  }
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function renderSponsoredPlacements(placements = []) {
  if (!placements.length) {
    return "";
  }
  return `
    <section class="section-panel sponsored-section" aria-label="Sponsored placements">
      <div class="section-header">
        <h2>Sponsored</h2>
        <span class="badge warning">Commercial</span>
      </div>
      <div class="section-body contributor-list">
        ${placements
          .map(
            (placement) => `
              <article class="contributor">
                <strong>${escapeHtml(placement.label)}</strong>
                <span>${escapeHtml(placement.disclosure_text)}</span>
                <small>${escapeHtml(placement.status)} · ${escapeHtml(placement.surface)}</small>
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

export function renderOverviewMetrics(snapshot) {
  return `
    <section class="summary-grid" aria-label="Strategy summary">
      ${summaryItem("Estimated starting capital", formatMoney(snapshot.capital.total_capital))}
      ${summaryItem("Estimated net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
      ${summaryItem("30-day modeled ROI", formatRatio(snapshot.roi.roi_total_30d))}
      ${summaryItem("Risk", scoreText(snapshot.risk))}
    </section>
  `;
}

export function renderUncertainty(snapshot) {
  const ranges = snapshot.uncertainty_ranges || [];
  if (!ranges.length) {
    return `
      <section class="section-panel">
        <div class="section-header"><h2>Uncertainty Range</h2></div>
        <div class="section-body">
          <p class="muted">No explicit low/base/high uncertainty range is available for this deterministic strategy snapshot.</p>
        </div>
      </section>
    `;
  }
  return `
    <section class="section-panel">
      <div class="section-header"><h2>Uncertainty Range</h2></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Metric</th><th>Low</th><th>Base</th><th>High</th><th>Unit</th></tr></thead>
          <tbody>
            ${ranges
              .map(
                (range) => `
                  <tr>
                    <td>${escapeHtml(range.metric)}</td>
                    <td class="metric">${formatTechnicalValue(range.values?.low_metric)}</td>
                    <td class="metric">${formatTechnicalValue(range.values?.base_metric)}</td>
                    <td class="metric">${formatTechnicalValue(range.values?.high_metric)}</td>
                    <td>${escapeHtml(range.unit || "Unspecified")}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

export function renderScoreDetails(score, title) {
  if (!score?.available) {
    return `
      <section class="section-panel">
        <div class="section-header"><h2>${escapeHtml(title)}</h2>${renderScoreBadge(score, title.toLowerCase())}</div>
        <div class="section-body">
          <p class="muted">Score unavailable. ${(score?.unavailable_factors || []).map((factor) => escapeHtml(factor.reason)).join(" ")}</p>
        </div>
      </section>
    `;
  }
  const contributors = score.contributions || [];
  return `
    <section class="section-panel">
      <div class="section-header"><h2>${escapeHtml(title)}</h2>${renderScoreBadge(score, title.toLowerCase())}</div>
      <div class="section-body contributor-list">
        ${contributors.length ? contributors.map(renderContributor).join("") : '<p class="muted">No point contributors were recorded.</p>'}
        ${(score.unavailable_factors || []).length ? `<p class="muted">Unavailable factors: ${score.unavailable_factors.map((factor) => escapeHtml(factor.factor)).join(", ")}</p>` : ""}
      </div>
    </section>
  `;
}

export function renderContributor(contribution) {
  return `
    <article class="contributor">
      <strong>${escapeHtml(labelize(contribution.factor))}: ${escapeHtml(String(contribution.points))} points</strong>
      <span>${escapeHtml(contribution.reason)}</span>
      <small>${escapeHtml(evidenceSummary(contribution.evidence || {}))}</small>
    </article>
  `;
}

export function renderClassificationSummary(summary = { counts: {}, metrics: {} }) {
  const counts = summary.counts || {};
  const metrics = summary.metrics || {};
  const rows = Object.entries(metrics)
    .slice(0, 12)
    .map(
      ([metric, classification]) => `
        <tr>
          <td>${escapeHtml(metric)}</td>
          <td>${classificationBadge(classification)}</td>
        </tr>
      `,
    )
    .join("");
  return `
    <section class="section-panel">
      <div class="section-header"><h2>LIVE / CONFIG / DERIVED</h2></div>
      <div class="section-body">
        <div class="classification-grid">
          ${summaryItem("LIVE", escapeHtml(String(counts.LIVE ?? 0)))}
          ${summaryItem("CONFIG", escapeHtml(String(counts.CONFIG ?? 0)))}
          ${summaryItem("DERIVED", escapeHtml(String(counts.DERIVED ?? 0)))}
        </div>
        <p class="muted" style="margin-top: 14px;">LIVE values are current external observations, CONFIG values are explicit assumptions, and DERIVED values are calculated from observations or assumptions.</p>
      </div>
      ${rows ? `<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Classification</th></tr></thead><tbody>${rows}</tbody></table></div>` : ""}
    </section>
  `;
}

export function renderWarnings(warnings = []) {
  if (!warnings.length) {
    return `
      <section class="section-panel">
        <div class="section-header"><h2>Warnings</h2><span class="badge good">Clear</span></div>
        <div class="section-body"><p class="muted">No warnings are attached to this snapshot.</p></div>
      </section>
    `;
  }
  return `
    <section class="section-panel">
      <div class="section-header"><h2>Warnings</h2><span class="badge warning">${escapeHtml(String(warnings.length))} recorded</span></div>
      <div class="section-body contributor-list">
        ${warnings
          .map(
            (warning) => `
              <article class="contributor">
                <strong>${escapeHtml(labelize(warning.code))} (${escapeHtml(labelize(warning.severity))})</strong>
                <span>${escapeHtml(warning.message)}</span>
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

export function renderHistory(historyPage = { items: [] }) {
  const items = [...(historyPage.items || [])].sort((left, right) => Date.parse(left.calculated_at) - Date.parse(right.calculated_at));
  if (items.length < 2) {
    return `
      <section class="section-panel">
        <div class="section-header"><h2>History</h2></div>
        <div class="section-body">
          <p class="muted">At least two stored snapshots are needed before GamCryp can show a recent trend.</p>
        </div>
      </section>
    `;
  }
  const recent = items.slice(-6);
  return `
    <section class="section-panel history-panel">
      <div class="section-header"><h2>History</h2><span class="badge info">${escapeHtml(String(items.length))} snapshots</span></div>
      <div class="section-body">
        <p class="history-summary">${escapeHtml(historyTrendSummary(items))}</p>
        <div class="history-bars" aria-label="Recent 30-day ROI history">
          ${recent
            .map(
              (snapshot) => `
                <article class="history-bar ${decimalSign(snapshot.roi?.roi_total_30d?.value ?? "0") < 0 ? "negative" : "positive"}" style="--bar: ${historyBarHeight(snapshot.roi?.roi_total_30d?.value)};">
                  <div class="history-bar-fill" aria-hidden="true"></div>
                  <strong>${formatRatio(snapshot.roi.roi_total_30d)}</strong>
                  <span>${escapeHtml(formatHistoryShortDate(snapshot.calculated_at))}</span>
                  <small>${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}</small>
                </article>
              `,
            )
            .join("")}
        </div>
        <details class="advanced-panel history-advanced">
          <summary>Show full snapshot table</summary>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Calculated</th><th>Net/day</th><th>30D ROI</th><th>Confidence</th><th>Risk</th><th>Freshness</th></tr></thead>
              <tbody>
                ${items
                  .map(
                    (snapshot) => `
                      <tr>
                        <td>${formatDateTime(snapshot.calculated_at)}</td>
                        <td class="metric">${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}</td>
                        <td class="metric">${formatRatio(snapshot.roi.roi_total_30d)}</td>
                        <td>${renderScoreBadge(snapshot.confidence, "confidence")}</td>
                        <td>${renderScoreBadge(snapshot.risk, "risk")}</td>
                        <td>${renderFreshnessPill(snapshot.freshness)}</td>
                      </tr>
                    `,
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </section>
  `;
}

export function renderMethodologyPage() {
  const items = [
    ["Modeled ROI", "ROI is calculated only when entry cost, reward rate, realizable reward value or exit path, and relevant costs can be reproduced from evidence."],
    ["ROI unavailable", "When the economic path cannot be reproduced, GamCryp does not invent a financial ROI number."],
    ["Realizable earnings", "Rewards are valued after the modeled route to sell or realize them, including route costs when available."],
    ["Slippage", "Displayed spot price can overstate sellable value. A quote or market simulation is preferred when the source supports it."],
    ["Total vs at-risk capital", "Total capital is the full entry requirement. Capital at risk is the portion economically exposed after recoverable value is considered."],
    ["Risk", "Risk describes how exposed or fragile the opportunity or strategy is."],
    ["Confidence", "Confidence describes how strong and reproducible the evidence behind the model is. It is separate from Risk."],
    ["Freshness", "Freshness describes how recently the model and source inputs were updated or recalculated."],
    ["LIVE / CONFIG / DERIVED", "LIVE means current observation, CONFIG means explicit assumption, and DERIVED means calculated from observed or configured inputs."],
    ["Commercial independence", "Referral, affiliate, sponsorship, or commercial relationships do not affect ROI, Risk, Confidence, or organic ranking."],
    ["Decision support", "GamCryp provides decision-support analysis, not investment advice, guarantees, or automated execution instructions."],
  ];
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Methodology</p>
        <h1>How GamCryp reads Web3 opportunity economics</h1>
        <p class="lede">The model emphasizes explainable assumptions, realizable values, and source quality over hype.</p>
      </section>
      <section class="method-grid">
        ${items
          .map(
            ([title, body]) => `
              <article class="method-item">
                <h2>${escapeHtml(title)}</h2>
                <p class="muted">${escapeHtml(body)}</p>
              </article>
            `,
          )
          .join("")}
      </section>
    </div>
  `;
}

export function renderFreshnessAlert(snapshot) {
  const messages = [];
  if (snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh") {
    messages.push(`Freshness status is ${snapshot.freshness.overall_status}.`);
  }
  if (snapshot.confidence?.available && snapshot.confidence.label === "LOW") {
    messages.push("Confidence is LOW, so the calculation depends on weaker or incomplete evidence.");
  }
  if (!messages.length) {
    return "";
  }
  const danger = snapshot.freshness?.overall_status === "invalid" || snapshot.freshness?.overall_status === "missing";
  return `<section class="alert ${danger ? "danger" : ""}">${messages.map(escapeHtml).join(" ")}</section>`;
}

export function renderStrategySignals(snapshot) {
  const signals = [];
  const roi = snapshot.roi?.roi_total_30d;
  const netSign = decimalSign(snapshot.earnings?.net_earnings_day?.amount ?? "0");
  const stale = snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh";
  if (!roi || roi.value === null || roi.value === undefined) {
    signals.push({ label: "ROI not measurable yet", tone: "warning" });
  } else if (netSign > 0) {
    signals.push({ label: stale ? "Modeled positive net/day (stale)" : "Profitable now", tone: stale ? "warning" : "good" });
  } else if (netSign < 0) {
    signals.push({ label: stale ? "Modeled negative net/day (stale)" : "Unprofitable now", tone: stale ? "warning" : "high" });
  } else {
    signals.push({ label: "Flat net earnings", tone: "medium" });
  }
  if (snapshot.confidence?.available && snapshot.confidence.label === "LOW") {
    signals.push({ label: "Low confidence", tone: "warning" });
  }
  if (snapshot.risk?.available && ["HIGH", "VERY HIGH"].includes(snapshot.risk.label)) {
    signals.push({
      label: snapshot.risk.label === "VERY HIGH" ? "Very high risk" : "High risk",
      tone: "high",
    });
  }
  if (snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh") {
    signals.push({ label: "Stale data", tone: "warning" });
  }
  return `
    <div class="signal-row">
      ${signals.map((signal) => `<span class="badge ${signal.tone}">${escapeHtml(signal.label)}</span>`).join("")}
    </div>
  `;
}

export function renderError(error) {
  const notFound = error?.status === 404;
  return `
    <section class="error-state">
      <h1>${notFound ? "Not found" : "Data unavailable"}</h1>
      <p>${escapeHtml(error?.message || "The API is unavailable or returned an unexpected response.")}</p>
    </section>
  `;
}

export function renderLoading() {
  return '<section class="loading-state"><p>Loading strategy data...</p></section>';
}

export function renderRouteDegradedNotice(error) {
  const message = error?.message || "Live data is temporarily unavailable.";
  return `
    <section class="error-state" role="status" aria-live="polite">
      <h2>Live data temporarily unavailable</h2>
      <p>${escapeHtml(message)} Stored page content remains visible where available. No fresh or estimated values are being invented.</p>
      <button class="secondary-button" type="button" data-retry-data>Retry</button>
    </section>
  `;
}

function preserveServerRenderedPage(root, initialMarkup, error) {
  root.innerHTML = `${renderRouteDegradedNotice(error)}${initialMarkup}`;
  root.querySelector("[data-retry-data]")?.addEventListener("click", () => renderCurrentRoute());
}

export function formatMoney(money, options = {}) {
  if (!money || money.amount === null || money.amount === undefined) {
    return '<span class="muted">Unavailable</span>';
  }
  const rawAmount = String(money.amount);
  const amount = normalizeDecimalString(rawAmount);
  const currency = String(money.currency || "").trim();
  const exact = `${rawAmount} ${currency}`.trim();
  const suffix = options.perDay ? "/day" : "";
  if (currency.toUpperCase() === "USD") {
    const sign = decimalSign(amount);
    const absolute = sign < 0 ? amount.slice(1) : amount;
    let display;
    if (sign !== 0 && comparePositiveDecimals(absolute, "0.0001") < 0) {
      display = `${sign < 0 ? "loss " : ""}< $0.0001${suffix}`;
    } else {
      const scale = comparePositiveDecimals(absolute, "0.01") < 0 && sign !== 0 ? 4 : 2;
      const rounded = trimTrailingZeros(addThousands(roundDecimalString(absolute, scale)));
      display = `${sign < 0 ? "-" : ""}$${rounded}${suffix}`;
    }
    return `<span class="money" title="${escapeHtml(exact)}">${escapeHtml(display)}</span>`;
  }
  const rounded = trimTrailingZeros(roundDecimalString(amount, 4));
  return `<span class="money" title="${escapeHtml(exact)}">${escapeHtml(`${rounded} ${currency}${suffix}`.trim())}</span>`;
}

export function formatRatio(metric) {
  if (!metric || metric.value === null || metric.value === undefined) {
    return `<span class="muted">${escapeHtml(metric?.reason || "Unavailable")}</span>`;
  }
  const rawValue = String(metric.value);
  const normalized = normalizeDecimalString(rawValue);
  const percent = trimTrailingZeros(roundDecimalString(shiftDecimal(normalized, 2), 2));
  return `<span class="ratio" title="Exact ratio: ${escapeHtml(rawValue)}">${escapeHtml(percent)}%</span>`;
}

export function formatBreakEven(metric) {
  if (!metric || metric.days === null || metric.days === undefined) {
    const reason = metric?.reason || "Unavailable";
    const label = /positive net earnings/i.test(reason) ? "Not profitable" : reason;
    return `<span class="muted" title="${escapeHtml(reason)}">${escapeHtml(label)}</span>`;
  }
  const rawDays = String(metric.days);
  const rounded = roundDecimalString(normalizeDecimalString(rawDays), 0);
  const days = addThousands(rounded);
  return `<span class="break-even" title="Exact days: ${escapeHtml(rawDays)}">${escapeHtml(days)} ${rounded === "1" ? "day" : "days"}</span>`;
}

function normalizeDecimalString(value) {
  const text = expandExponentialNotation(String(value).trim());
  if (!text) {
    return text;
  }
  const negative = text.startsWith("-");
  const unsigned = text.replace(/^[+-]/, "");
  const [integerPart = "0", fractionPart = ""] = unsigned.split(".");
  const integer = integerPart.replace(/^0+(?=\d)/, "") || "0";
  const fraction = fractionPart.replace(/0+$/, "");
  const normalized = fraction ? `${integer}.${fraction}` : integer;
  return negative && normalized !== "0" ? `-${normalized}` : normalized;
}

function expandExponentialNotation(value) {
  const match = String(value)
    .trim()
    .match(/^([+-]?)(\d+)(?:\.(\d+))?[eE]([+-]?\d+)$/);
  if (!match) {
    return value;
  }
  const [, sign, integer, fraction = "", exponentText] = match;
  const exponent = parseSignedInteger(exponentText);
  const digits = `${integer}${fraction}`;
  const point = integer.length + exponent;
  let expanded;
  if (point <= 0) {
    expanded = `0.${"0".repeat(Math.abs(point))}${digits}`;
  } else if (point >= digits.length) {
    expanded = `${digits}${"0".repeat(point - digits.length)}`;
  } else {
    expanded = `${digits.slice(0, point)}.${digits.slice(point)}`;
  }
  return `${sign === "-" ? "-" : ""}${expanded}`;
}

function parseSignedInteger(value) {
  const text = String(value);
  const negative = text.startsWith("-");
  const digits = text.replace(/^[+-]/, "");
  let parsed = 0;
  for (const char of digits) {
    parsed = parsed * 10 + (char.charCodeAt(0) - 48);
  }
  return negative ? -parsed : parsed;
}

function shiftDecimal(value, places) {
  const normalized = normalizeDecimalString(value);
  if (!normalized || /e/i.test(normalized)) {
    return normalized;
  }
  const negative = normalized.startsWith("-");
  const unsigned = negative ? normalized.slice(1) : normalized;
  const [integer, fraction = ""] = unsigned.split(".");
  const digits = `${integer}${fraction}` || "0";
  const position = integer.length + places;
  let shifted;
  if (position <= 0) {
    shifted = `0.${"0".repeat(Math.abs(position))}${digits}`;
  } else if (position >= digits.length) {
    shifted = `${digits}${"0".repeat(position - digits.length)}`;
  } else {
    shifted = `${digits.slice(0, position)}.${digits.slice(position)}`;
  }
  const normalizedShifted = normalizeDecimalString(shifted);
  return negative && normalizedShifted !== "0" ? `-${normalizedShifted}` : normalizedShifted;
}

function roundDecimalString(value, fractionDigits) {
  const normalized = normalizeDecimalString(value);
  if (!normalized || /e/i.test(normalized)) {
    return normalized;
  }
  const negative = normalized.startsWith("-");
  const unsigned = negative ? normalized.slice(1) : normalized;
  const [integer, fraction = ""] = unsigned.split(".");
  const padded = fraction.padEnd(fractionDigits + 1, "0");
  const retained = padded.slice(0, fractionDigits);
  const shouldRoundUp = (padded[fractionDigits] || "0") >= "5";
  let digits = `${integer}${retained}` || "0";
  if (shouldRoundUp) {
    digits = incrementDecimalDigits(digits);
  }
  const splitAt = Math.max(0, digits.length - fractionDigits);
  const roundedInteger = (fractionDigits === 0 ? digits : digits.slice(0, splitAt)) || "0";
  const roundedFraction = fractionDigits === 0 ? "" : digits.slice(splitAt).padStart(fractionDigits, "0");
  const rounded = fractionDigits === 0 ? roundedInteger : `${roundedInteger}.${roundedFraction}`;
  const normalizedRounded = normalizeDecimalString(rounded);
  return negative && normalizedRounded !== "0" ? `-${normalizedRounded}` : normalizedRounded;
}

function incrementDecimalDigits(digits) {
  const chars = digits.split("");
  for (let index = chars.length - 1; index >= 0; index -= 1) {
    if (chars[index] !== "9") {
      chars[index] = String.fromCharCode(chars[index].charCodeAt(0) + 1);
      return chars.join("");
    }
    chars[index] = "0";
  }
  return `1${chars.join("")}`;
}

function addThousands(value) {
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [integer, fraction] = unsigned.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${fraction ? `${grouped}.${fraction}` : grouped}`;
}

function trimTrailingZeros(value) {
  const trimmed = String(value).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return trimmed === "" || trimmed === "-0" ? "0" : trimmed;
}

function decimalSign(value) {
  const normalized = normalizeDecimalString(value);
  const digits = normalized.replace(/[-.]/g, "");
  if (!/[1-9]/.test(digits)) {
    return 0;
  }
  return normalized.startsWith("-") ? -1 : 1;
}

function comparePositiveDecimals(left, right) {
  const normalizedLeft = normalizeDecimalString(left).replace(/^-/, "");
  const normalizedRight = normalizeDecimalString(right).replace(/^-/, "");
  const [leftInteger, leftFraction = ""] = normalizedLeft.split(".");
  const [rightInteger, rightFraction = ""] = normalizedRight.split(".");
  const cleanLeftInteger = leftInteger.replace(/^0+(?=\d)/, "");
  const cleanRightInteger = rightInteger.replace(/^0+(?=\d)/, "");
  if (cleanLeftInteger.length !== cleanRightInteger.length) {
    return cleanLeftInteger.length > cleanRightInteger.length ? 1 : -1;
  }
  if (cleanLeftInteger !== cleanRightInteger) {
    return cleanLeftInteger > cleanRightInteger ? 1 : -1;
  }
  const fractionLength = Math.max(leftFraction.length, rightFraction.length);
  const paddedLeftFraction = leftFraction.padEnd(fractionLength, "0");
  const paddedRightFraction = rightFraction.padEnd(fractionLength, "0");
  if (paddedLeftFraction === paddedRightFraction) {
    return 0;
  }
  return paddedLeftFraction > paddedRightFraction ? 1 : -1;
}

export function renderScoreBadge(score, kind) {
  if (!score?.available) {
    return `<span class="badge">${escapeHtml(labelize(kind))} unavailable</span>`;
  }
  const label = score.label || "UNKNOWN";
  return `<span class="badge ${scoreClass(label, kind)}">${escapeHtml(labelize(kind))} ${escapeHtml(String(score.score))} ${escapeHtml(publicScoreLabel(label))}</span>`;
}

export function scoreText(score) {
  if (!score?.available) {
    return "Unavailable";
  }
  return `${score.score} ${publicScoreLabel(score.label)}`;
}

export function renderFreshnessPill(freshness, options = {}) {
  const status = freshness?.overall_status || "unknown";
  if (options.hideFresh && status === "fresh") {
    return "";
  }
  const className = status === "fresh" ? "good" : "warning";
  return `<span class="badge ${className}">${escapeHtml(labelize(status))}</span>`;
}

export function renderWarningsIndicator(warnings = [], options = {}) {
  if (!warnings.length) {
    if (options.hideEmpty) {
      return "";
    }
    return '<span class="badge good">No warnings</span>';
  }
  return `<span class="badge warning">${escapeHtml(String(warnings.length))} warning${warnings.length === 1 ? "" : "s"}</span>`;
}

export function renderDestinationButton(destination, label = "Open", context = {}) {
  if (!destination || destination.status !== "active" || !destination.redirect_url) {
    return '<span class="badge">No reviewed link</span>';
  }
  const relationship = destinationRelationshipLabel(destination);
  const href = redirectWithContext(destination.redirect_url, context);
  const analytics = analyticsAttributes(destination, context);
  return `
    <a class="button cta" href="${escapeHtml(href)}" title="${escapeHtml(destination.disclosure_text)}" target="_blank" rel="noopener noreferrer"${analytics}>
      ${escapeHtml(label)}
      ${relationship ? `<span>${escapeHtml(relationship)}</span>` : ""}
    </a>
  `;
}

export function renderDestinationDisclosure(destination) {
  return `
    <article class="contributor">
      <strong>${escapeHtml(destination.label)} (${escapeHtml(labelize(destination.destination_type))})</strong>
      <span>${escapeHtml(destination.disclosure_text)}</span>
      <small>${escapeHtml(destination.verification_status)} | reviewed ${formatDateTime(destination.reviewed_at)}</small>
    </article>
  `;
}

export function renderFeasibilityStatus(status) {
  const normalized = String(status || "unknown").toUpperCase();
  const className = normalized === "GO" ? "good" : normalized === "REJECTED" ? "high" : "medium";
  return `<span class="badge ${className}" title="${escapeHtml(feasibilityLabel(normalized))} review state">${escapeHtml(feasibilityLabel(normalized))}</span>`;
}

export function renderValueStatus(status, strategyCount = 0) {
  const normalized = String(status || "unknown");
  const measurable = normalized === "realizable" && strategyCount > 0;
  const label = measurable ? "ROI can be measured" : "ROI not measurable yet";
  return `<span class="badge ${measurable ? "good" : "warning"}">${escapeHtml(label)}</span>`;
}

function valueStatusText(status, strategyCount = 0) {
  const normalized = String(status || "unknown");
  return normalized === "realizable" && strategyCount > 0 ? "ROI can be measured" : "ROI not measurable yet";
}

function unavailableRoiReason(opportunity) {
  return plainUnavailableReason(opportunity);
}

function conciseUnavailableRoiReason(opportunity) {
  return plainUnavailableReason(opportunity);
}

export function classificationBadge(classification) {
  const className = classification === "LIVE" ? "good" : classification === "DERIVED" ? "info" : "medium";
  return `<span class="badge ${className}">${escapeHtml(classification)}</span>`;
}

function scoreClass(label, kind) {
  const normalized = label.toLowerCase().replace(/\s+/g, "-");
  if (kind === "confidence" && normalized === "low") {
    return "low-confidence";
  }
  if (kind === "risk") {
    if (normalized === "low") {
      return "good";
    }
    if (normalized === "medium") {
      return "medium";
    }
    return normalized;
  }
  if (normalized === "high") {
    return "good";
  }
  if (normalized === "moderate") {
    return "medium";
  }
  return normalized;
}

function addParam(params, key, value) {
  const text = value === null || value === undefined ? "" : String(value).trim();
  if (text !== "") {
    params.set(key, text);
  }
}

function summaryItem(label, value) {
  return `<div class="summary-item"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`;
}

function metricItem(label, value) {
  return `<div class="metric-item"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`;
}

function formatTechnicalValue(value) {
  if (value === null || value === undefined || value === "") {
    return '<span class="muted">Unavailable</span>';
  }
  const raw = String(value);
  if (isDateTimeLike(raw)) {
    return `<span class="technical-value" title="Exact timestamp: ${escapeHtml(raw)}">${formatDateTime(raw)}</span>`;
  }
  if (isDecimalLike(raw)) {
    return `<span class="technical-value" title="Exact value: ${escapeHtml(raw)}">${escapeHtml(formatConciseDecimal(raw))}</span>`;
  }
  return escapeHtml(raw);
}

function evidenceSummary(evidence) {
  const entries = Object.entries(evidence || {});
  if (!entries.length) {
    return "No detailed evidence payload";
  }
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${labelize(key)}: ${summarizeEvidenceValue(value)}`)
    .join("; ");
}

function summarizeEvidenceValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (Array.isArray(value)) {
    const text = value.slice(0, 3).map(summarizeEvidenceValue).join(", ");
    return value.length > 3 ? `${text}, and ${value.length - 3} more` : text;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length) {
      return "No details";
    }
    return entries
      .slice(0, 3)
      .map(([key, nested]) => `${labelize(key)} ${primitiveEvidenceText(nested)}`)
      .join(", ");
  }
  if (isDateTimeLike(value)) {
    return textFromHtml(formatDateTime(value));
  }
  if (isDecimalLike(value)) {
    return formatConciseDecimal(value);
  }
  return String(value);
}

function primitiveEvidenceText(value) {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (typeof value === "object") {
    return Array.isArray(value) ? value.slice(0, 3).map(primitiveEvidenceText).join(", ") : "available";
  }
  if (isDateTimeLike(value)) {
    return textFromHtml(formatDateTime(value));
  }
  if (isDecimalLike(value)) {
    return formatConciseDecimal(value);
  }
  return String(value);
}

export function formatUpdatedAge(value, now = new Date()) {
  const parsed = Date.parse(value);
  const current = now instanceof Date ? now.getTime() : Date.parse(now);
  if (!Number.isFinite(parsed) || !Number.isFinite(current)) {
    return "Updated time unavailable";
  }
  const elapsedSeconds = Math.max(0, Math.floor((current - parsed) / 1000));
  if (elapsedSeconds < 60) {
    return "Updated just now";
  }
  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  if (elapsedMinutes < 60) {
    return `Updated ${elapsedMinutes}m ago`;
  }
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 48) {
    return `Updated ${elapsedHours}h ago`;
  }
  const elapsedDays = Math.floor(elapsedHours / 24);
  if (elapsedDays < 30) {
    return `Updated ${elapsedDays}d ago`;
  }
  return `Updated ${formatDateTime(value)}`;
}

function redirectWithContext(url, context = {}) {
  if (!url) {
    return url;
  }
  const params = new URLSearchParams();
  addParam(params, "source_page", context.sourcePage);
  addParam(params, "placement", context.placement);
  const query = params.toString();
  if (!query) {
    return url;
  }
  return `${url}${url.includes("?") ? "&" : "?"}${query}`;
}

function formatDateTime(value) {
  if (!value) {
    return "Unavailable";
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const display = `${months[parsed.getUTCMonth()]} ${parsed.getUTCDate()}, ${parsed.getUTCFullYear()} ${pad2(parsed.getUTCHours())}:${pad2(parsed.getUTCMinutes())} UTC`;
    return escapeHtml(display);
  }
  return escapeHtml(stripTimestampNoise(value));
}

export function labelize(value) {
  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isDecimalLike(value) {
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(String(value).trim());
}

function isDateTimeLike(value) {
  return /^\d{4}-\d{2}-\d{2}[T ][\d:.+-]+Z?$/.test(String(value).trim());
}

function formatConciseDecimal(value) {
  const normalized = normalizeDecimalString(value);
  const sign = decimalSign(normalized);
  const absolute = sign < 0 ? normalized.slice(1) : normalized;
  if (!absolute || sign === 0) {
    return "0";
  }
  if (comparePositiveDecimals(absolute, "0.0001") < 0) {
    return `${sign < 0 ? "-" : ""}< 0.0001`;
  }
  const scale = comparePositiveDecimals(absolute, "1") < 0 ? 4 : 2;
  return `${sign < 0 ? "-" : ""}${trimTrailingZeros(addThousands(roundDecimalString(absolute, scale)))}`;
}

function stripTimestampNoise(value) {
  let text = String(value).replace("T", " ").replace("Z", " UTC");
  const suffix = text.includes("+00:00") || text.includes(" UTC") ? " UTC" : "";
  text = text.replace("+00:00", "");
  if (text.includes(".")) {
    text = text.split(".", 1)[0];
  }
  return `${text}${suffix}`.replace(/:00 UTC$/, " UTC");
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

export function opportunityTypeLabel(value) {
  const normalized = String(value || "").toUpperCase();
  if (normalized === "GAME") {
    return "Games";
  }
  if (normalized === "DEPIN_NODE") {
    return "DePIN / Nodes";
  }
  if (normalized === "POINTS") {
    return "Points programs";
  }
  return labelize(value || "Opportunity");
}

function opportunityTypeDescription(value) {
  const normalized = String(value || "").toUpperCase();
  if (normalized === "GAME") {
    return "Earn through blockchain game economies where rewards and exits can be reviewed.";
  }
  if (normalized === "DEPIN_NODE") {
    return "Earn rewards by running software or providing network, compute, storage, bandwidth, or similar resources.";
  }
  if (normalized === "POINTS") {
    return "Earn points now; cash or token value may not exist yet.";
  }
  return "A reviewed Web3 earning opportunity.";
}

function opportunityIntro(opportunity) {
  const typeDescription = opportunityTypeDescription(opportunity.opportunity_type);
  const rewardTypes = (opportunity.reward_asset_or_points_type || []).join(", ");
  const rewardText = rewardTypes ? ` Rewards tracked: ${rewardTypes}.` : "";
  const summary = opportunity.feasibility_summary ? ` ${opportunity.feasibility_summary}` : "";
  return `${typeDescription}${rewardText}${summary}`.trim();
}

function opportunityCardState(opportunity) {
  const status = String(opportunity.data_feasibility_status || "").toUpperCase();
  if (status === "PARKED" || status === "REJECTED") {
    return "Watchlist / Research";
  }
  return "ROI not measurable yet";
}

function plainUnavailableReason(opportunity) {
  const structuredReason = String(opportunity?.roi_unavailable?.reason || "").trim();
  if (structuredReason) {
    return structuredReason;
  }
  const valueStatus = String(opportunity.value_realization_status || "").toLowerCase();
  const feasibility = String(opportunity.data_feasibility_status || "").toUpperCase();
  const summary = String(opportunity.feasibility_summary || "").toLowerCase();
  if (valueStatus.includes("non_transferable_points") || summary.includes("points are not") || summary.includes("no monetary value")) {
    return "Points cannot currently be converted to cash reliably.";
  }
  if (valueStatus.includes("future_airdrop") || summary.includes("future") || summary.includes("airdrop")) {
    return "Reward value is not yet verifiable.";
  }
  if (feasibility === "REJECTED" || valueStatus.includes("unknown") || summary.includes("exit") || summary.includes("realizable value")) {
    return "A reproducible exit value is not available yet.";
  }
  if (valueStatus === "realizable") {
    return "The reward token may be priced, but earning rate, costs, or exit assumptions are not reproducible yet.";
  }
  return "Reward has no reliable market price yet.";
}

function feasibilityLabel(value) {
  if (value === "GO") {
    return "Ready";
  }
  if (value === "PARTIAL") {
    return "Research";
  }
  if (value === "PARKED") {
    return "Watchlist";
  }
  if (value === "REJECTED") {
    return "Not modelable";
  }
  return "Under review";
}

function publicScoreLabel(label) {
  return labelize(String(label || "unknown").toLowerCase());
}

function destinationRelationshipLabel(destination) {
  if (destination.is_affiliate) {
    return "Affiliate";
  }
  const relationship = String(destination.commercial_relationship || "").toLowerCase();
  if (!relationship || relationship === "none" || relationship === "official") {
    return "";
  }
  return labelize(relationship);
}

function analyticsAttributes(destination, context = {}) {
  const attributes = {
    "data-analytics-link": "outbound",
    "data-destination-slug": destination.destination_slug,
    "data-opportunity-id": destination.opportunity_id,
    "data-strategy-id": destination.strategy_id,
    "data-opportunity-type": opportunityTypeLabel(destination.opportunity_type),
    "data-placement": context.placement,
    "data-source-page": context.sourcePage,
    "data-target-url-kind": destinationTargetKind(destination),
    "data-referral-status": String(destination.referral_status || (destination.is_affiliate ? "affiliate" : "none")).toLowerCase(),
    "data-commercial-relationship": destination.commercial_relationship,
    "data-is-affiliate": destination.is_affiliate ? "true" : "false",
  };
  return Object.entries(attributes)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .map(([key, value]) => ` ${key}="${escapeHtml(String(value))}"`)
    .join("");
}

function productClickAttributes(eventName, values = {}) {
  const attributes = {
    "data-product-click": eventName,
    "data-opportunity-id": values.opportunityId,
    "data-opportunity-type": values.opportunityType,
    "data-strategy-id": values.strategyId,
    "data-ranking-slug": values.rankingSlug,
    "data-snapshot-id": values.snapshotId || values.snapshot?.snapshot_id,
    "data-snapshot-timestamp": values.snapshotTimestamp || values.snapshot?.calculated_at,
    "data-placement": values.placement,
    "data-source-page": values.sourcePage,
  };
  return Object.entries(attributes)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .map(([key, value]) => ` ${key}="${escapeHtml(String(value))}"`)
    .join("");
}

function destinationTargetKind(destination) {
  const referralStatus = String(destination.referral_status || "").toUpperCase();
  return destination.referral_url && referralStatus === "ACTIVE" ? "referral" : "official";
}

function renderNetEarningsInterpretation(snapshot) {
  const sign = decimalSign(snapshot.earnings?.net_earnings_day?.amount ?? "0");
  const stale = snapshot.freshness?.overall_status && snapshot.freshness.overall_status !== "fresh";
  if (sign < 0) {
    return `<p class="metric-note">${stale ? "The model estimates a loss of" : "Modeled net earnings are"} ${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}.</p>`;
  }
  if (sign > 0) {
    return `<p class="metric-note">${stale ? "The model estimates net earnings of" : "Modeled net earnings are"} ${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}.</p>`;
  }
  return '<p class="metric-note">Estimated net earnings are currently flat.</p>';
}

export function publicConfig(win = globalThis.window) {
  return win?.GAMCRYP_PUBLIC_CONFIG || {};
}

export function analyticsMeasurementId(win = globalThis.window) {
  const value = publicConfig(win).gaMeasurementId;
  const text = typeof value === "string" ? value.trim() : "";
  return /^G-[A-Z0-9]{6,20}$/.test(text) ? text : "";
}

export function posthogProjectApiKey(win = globalThis.window) {
  const value = publicConfig(win).posthogProjectApiKey;
  const text = typeof value === "string" ? value.trim() : "";
  return /^[A-Za-z0-9_-]{8,128}$/.test(text) ? text : "";
}

export function posthogHost(win = globalThis.window) {
  const value = publicConfig(win).posthogHost || "https://us.i.posthog.com";
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:" || !parsed.host || parsed.pathname !== "/" || parsed.search || parsed.hash) {
      return "";
    }
    return `${parsed.protocol}//${parsed.host}`;
  } catch {
    return "";
  }
}

export function sentryFrontendDsn(win = globalThis.window) {
  const value = publicConfig(win).sentryFrontendDsn;
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  try {
    const parsed = new URL(value.trim());
    if (parsed.protocol !== "https:" || !parsed.host || parsed.search || parsed.hash) {
      return "";
    }
    return value.trim();
  } catch {
    return "";
  }
}

export function hasConsentGatedAnalytics(win = globalThis.window) {
  return Boolean(analyticsMeasurementId(win) || posthogProjectApiKey(win));
}

export function analyticsConsent(storage = globalThis.window?.localStorage) {
  try {
    return storage?.getItem(ANALYTICS_CONSENT_KEY) || null;
  } catch {
    return null;
  }
}

export function renderAnalyticsConsentBanner(win = globalThis.window) {
  if (!hasConsentGatedAnalytics(win) || analyticsConsent(win?.localStorage)) {
    return "";
  }
  return `
    <section class="analytics-consent" data-analytics-consent-banner>
      <div>
        <strong>Privacy-friendly analytics</strong>
        <p>Help GamCryp understand which public opportunity pages are useful. Essential site and /go redirect behavior works either way.</p>
      </div>
      <div class="analytics-consent-actions">
        <button class="button" type="button" data-analytics-consent="accepted">Accept analytics</button>
        <button class="secondary-button" type="button" data-analytics-consent="rejected">Reject essential only</button>
      </div>
    </section>
  `;
}

export function setAnalyticsConsent(preference, context = {}) {
  const win = context.win || globalThis.window;
  const storage = context.storage || win?.localStorage;
  const normalized = preference === "accepted" ? "accepted" : "rejected";
  try {
    storage?.setItem(ANALYTICS_CONSENT_KEY, normalized);
  } catch {
    return false;
  }
  if (normalized === "accepted") {
    initializeAnalytics(context);
    initializeProductAnalytics(context);
  }
  return true;
}

export function initializeAnalytics(context = {}) {
  const win = context.win || globalThis.window;
  const doc = context.doc || win?.document || globalThis.document;
  const storage = context.storage || win?.localStorage;
  const measurementId = analyticsMeasurementId(win);
  if (!win || !doc || !measurementId || analyticsConsent(storage) !== "accepted") {
    return false;
  }
  win.dataLayer = win.dataLayer || [];
  if (typeof win.gtag !== "function") {
    win.gtag = function gtag() {
      win.dataLayer.push(arguments);
    };
  }
  if (!doc.querySelector?.(`script[data-gamcryp-ga="${measurementId}"]`)) {
    const script = doc.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    script.dataset.gamcrypGa = measurementId;
    doc.head?.appendChild(script);
  }
  if (initializedAnalyticsId !== measurementId) {
    win.gtag("js", new Date());
    win.gtag("config", measurementId, { send_page_view: false });
    initializedAnalyticsId = measurementId;
  }
  return true;
}

export function initializeProductAnalytics(context = {}) {
  const win = context.win || globalThis.window;
  const storage = context.storage || win?.localStorage;
  const key = posthogProjectApiKey(win);
  if (!win || !key || !posthogHost(win) || analyticsConsent(storage) !== "accepted") {
    return false;
  }
  if (!productAnalyticsDistinctId(context)) {
    return false;
  }
  initializedProductAnalyticsKey = key;
  return true;
}

export function productAnalyticsDistinctId(context = {}) {
  const win = context.win || globalThis.window;
  const storage = context.storage || win?.localStorage;
  try {
    const existing = storage?.getItem(PRODUCT_ANALYTICS_DISTINCT_ID_KEY);
    if (existing) {
      return String(existing).slice(0, 128);
    }
    const generator = context.idGenerator || (() => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `${Date.now()}-${Math.random()}`));
    const generated = `visitor:${String(generator()).slice(0, 120)}`;
    storage?.setItem(PRODUCT_ANALYTICS_DISTINCT_ID_KEY, generated);
    return generated.slice(0, 128);
  } catch {
    return "visitor:ephemeral";
  }
}

export function trackAnalyticsEvent(name, params = {}, context = {}) {
  const win = context.win || globalThis.window;
  if (!ANALYTICS_ALLOWED_EVENTS.has(name) || !initializeAnalytics(context) || typeof win?.gtag !== "function") {
    return false;
  }
  const safeParams = {};
  for (const [key, value] of Object.entries(params || {})) {
    if (ANALYTICS_ALLOWED_PARAMS.has(key) && value !== null && value !== undefined && String(value).trim() !== "") {
      safeParams[key] = String(value).slice(0, 120);
    }
  }
  try {
    win.gtag("event", name, safeParams);
    return true;
  } catch {
    return false;
  }
}

export function trackProductAnalyticsEvent(name, params = {}, context = {}) {
  const win = context.win || globalThis.window;
  const fetcher = context.fetcher || win?.fetch || globalThis.fetch;
  if (!PRODUCT_ANALYTICS_ALLOWED_EVENTS.has(name) || !initializeProductAnalytics(context)) {
    return false;
  }
  const host = posthogHost(win);
  const payload = {
    api_key: posthogProjectApiKey(win),
    event: name,
    distinct_id: productAnalyticsDistinctId(context),
    timestamp: new Date().toISOString(),
    properties: safeProductAnalyticsParams(params, context),
  };
  const url = `${host}/capture/`;
  try {
    const body = JSON.stringify(payload);
    if (typeof win?.navigator?.sendBeacon === "function" && win.navigator.sendBeacon(url, body)) {
      return true;
    }
    if (typeof fetcher === "function") {
      Promise.resolve(fetcher(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        mode: "cors",
        keepalive: true,
      })).catch(() => {});
      return true;
    }
  } catch {
    return false;
  }
  return false;
}

function safeProductAnalyticsParams(params = {}, context = {}) {
  const win = context.win || globalThis.window;
  const safeParams = { "$process_person_profile": false };
  const search = win?.location?.search || "";
  try {
    const urlParams = new URLSearchParams(search);
    for (const key of ["utm_source", "utm_medium", "utm_campaign"]) {
      const value = urlParams.get(key);
      if (value) {
        safeParams[key] = value.slice(0, 160);
      }
    }
  } catch {
    // Ignore malformed client URLs; analytics must stay best-effort.
  }
  for (const [key, value] of Object.entries(params || {})) {
    if (!PRODUCT_ANALYTICS_ALLOWED_PARAMS.has(key) || SENSITIVE_ANALYTICS_KEY_PATTERN.test(key)) {
      continue;
    }
    const cleaned = safeAnalyticsValue(value);
    if (cleaned !== null) {
      safeParams[key] = cleaned;
    }
  }
  return safeParams;
}

function safeAnalyticsValue(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "boolean" || typeof value === "number") {
    return value;
  }
  const text = String(value).trim();
  return text ? text.slice(0, 160) : null;
}

export function initializeErrorTracking(context = {}) {
  const win = context.win || globalThis.window;
  const doc = context.doc || win?.document || globalThis.document;
  const dsn = sentryFrontendDsn(win);
  if (!win || !doc || !dsn) {
    return false;
  }
  if (typeof win.Sentry?.init === "function") {
    return initializeSentryBrowserGlobal(win, dsn);
  }
  if (doc.querySelector?.("script[data-gamcryp-sentry='browser']")) {
    return true;
  }
  try {
    const script = doc.createElement("script");
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = SENTRY_BROWSER_SDK_URL;
    script.dataset.gamcrypSentry = "browser";
    script.onload = () => initializeSentryBrowserGlobal(win, dsn);
    script.onerror = () => {};
    doc.head?.appendChild(script);
    initializedSentryDsn = dsn;
    return true;
  } catch {
    return false;
  }
}

function initializeSentryBrowserGlobal(win, dsn) {
  if (initializedSentryDsn === dsn) {
    return true;
  }
  const config = publicConfig(win);
  const tracesSampleRate = boundedRate(config.sentryTracesSampleRate, 0.02);
  const options = {
    dsn,
    environment: config.sentryEnvironment || "production",
    release: config.sentryRelease || undefined,
    sendDefaultPii: false,
    tracesSampleRate,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    beforeSend: sanitizeBrowserSentryEvent,
  };
  if (tracesSampleRate > 0 && typeof win.Sentry.browserTracingIntegration === "function") {
    options.integrations = [win.Sentry.browserTracingIntegration()];
  }
  try {
    win.Sentry.init(options);
    initializedSentryDsn = dsn;
    return true;
  } catch {
    return false;
  }
}

function boundedRate(value, fallback) {
  const text = typeof value === "number" ? String(value) : String(value ?? "").trim();
  const parsed = /^0(?:\.\d+)?$|^1(?:\.0+)?$/.test(text) ? +text : NaN;
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(1, Math.max(0, parsed));
}

export function sanitizeBrowserSentryEvent(event = {}) {
  const request = event.request;
  if (request && typeof request === "object") {
    delete request.data;
    delete request.cookies;
    delete request.query_string;
    delete request.env;
    if (typeof request.url === "string") {
      request.url = stripQueryAndHash(request.url);
    }
    if (request.headers && typeof request.headers === "object") {
      request.headers = scrubSensitiveMap(request.headers);
    }
  }
  if (event.user && typeof event.user === "object") {
    delete event.user.email;
    delete event.user.username;
    delete event.user.ip_address;
    if (!Object.keys(event.user).length) {
      delete event.user;
    }
  }
  for (const key of ["extra", "contexts", "tags"]) {
    if (event[key] && typeof event[key] === "object") {
      event[key] = scrubSensitiveMap(event[key]);
    }
  }
  return event;
}

function scrubSensitiveMap(values) {
  const scrubbed = {};
  for (const [key, value] of Object.entries(values || {})) {
    if (SENSITIVE_ANALYTICS_KEY_PATTERN.test(key)) {
      scrubbed[key] = "[Filtered]";
    } else if (value && typeof value === "object" && !Array.isArray(value)) {
      scrubbed[key] = scrubSensitiveMap(value);
    } else {
      scrubbed[key] = value;
    }
  }
  return scrubbed;
}

function stripQueryAndHash(value) {
  try {
    const parsed = new URL(value);
    return `${parsed.protocol}//${parsed.host}${parsed.pathname}`;
  } catch {
    return value.split("?")[0].split("#")[0];
  }
}

export function resetAnalyticsForTests() {
  initializedAnalyticsId = null;
  initializedProductAnalyticsKey = null;
  initializedSentryDsn = null;
  lastTrackedPage = null;
}

function trackPageView(path = globalThis.window?.location?.pathname || "", title = globalThis.document?.title || "") {
  const key = `${path}|${title}`;
  if (lastTrackedPage === key) {
    return false;
  }
  lastTrackedPage = key;
  return trackAnalyticsEvent("page_view", { page_path: path, page_title: title });
}

function trackRouteView(path, routeContext = {}) {
  if (path.startsWith("/opportunities/")) {
    const opportunityId = routeContext.opportunity_id || decodeURIComponent(path.replace("/opportunities/", ""));
    const params = { ...routeContext, opportunity_id: opportunityId, opportunity_slug: opportunityId, page_path: path };
    trackAnalyticsEvent("opportunity_view", { opportunity_id: opportunityId, page_path: path });
    trackProductAnalyticsEvent("opportunity_view", params);
  } else if (path.startsWith("/strategies/")) {
    const strategyId = routeContext.strategy_id || decodeURIComponent(path.replace("/strategies/", ""));
    const params = { ...routeContext, strategy_id: strategyId, strategy_slug: strategyId, page_path: path };
    trackAnalyticsEvent("strategy_view", { strategy_id: strategyId, page_path: path });
    trackProductAnalyticsEvent("strategy_view", params);
  } else if (path === "/" || path === "/rankings" || path.startsWith("/rankings/")) {
    const rankingSlug = routeContext.ranking_slug || rankingSlugForPath(path);
    trackProductAnalyticsEvent("ranking_view", { ...routeContext, ranking_slug: rankingSlug, page_path: path });
  }
  trackPageView(path);
}

function rankingSlugForPath(path) {
  if (path === "/") {
    return "home";
  }
  if (path === "/rankings") {
    return "rankings";
  }
  return path.replace(/^\/rankings\/?/, "") || "rankings";
}

function rankingAnalyticsContext(rankings, rankingSlug) {
  const snapshot = rankings?.items?.[0]?.latest_snapshot;
  return {
    ranking_slug: rankingSlug,
    snapshot_id: snapshot?.snapshot_id,
    snapshot_timestamp: snapshot?.calculated_at,
  };
}

function opportunityAnalyticsContext(opportunity) {
  const strategy = (opportunity?.strategies || []).find((item) => item.latest_snapshot);
  return {
    opportunity_id: opportunity?.opportunity_id,
    opportunity_slug: opportunity?.opportunity_id,
    opportunity_type: opportunity?.opportunity_type,
    strategy_id: strategy?.strategy_id,
    strategy_slug: strategy?.strategy_id,
    snapshot_id: strategy?.latest_snapshot?.snapshot_id,
    snapshot_timestamp: strategy?.latest_snapshot?.calculated_at,
  };
}

function strategyAnalyticsContext(strategy) {
  return {
    opportunity_id: strategy?.opportunity_id || strategy?.game_id,
    opportunity_slug: strategy?.opportunity_id || strategy?.game_id,
    opportunity_type: strategy?.opportunity_type,
    strategy_id: strategy?.strategy_id,
    strategy_slug: strategy?.strategy_id,
    snapshot_id: strategy?.latest_snapshot?.snapshot_id,
    snapshot_timestamp: strategy?.latest_snapshot?.calculated_at,
  };
}

function mountAnalyticsConsent() {
  if (typeof document === "undefined" || !document.body || !renderAnalyticsConsentBanner()) {
    return;
  }
  if (!document.querySelector("[data-analytics-consent-banner]")) {
    document.body.insertAdjacentHTML("beforeend", renderAnalyticsConsentBanner());
  }
}

function bindAnalyticsConsentClick(event) {
  const button = event.target.closest("[data-analytics-consent]");
  if (!button) {
    return;
  }
  setAnalyticsConsent(button.getAttribute("data-analytics-consent"));
  document.querySelector("[data-analytics-consent-banner]")?.remove();
  trackPageView(window.location.pathname);
}

function bindOutboundAnalytics(event) {
  const link = event.target.closest("a[data-analytics-link='outbound']");
  if (!link) {
    return;
  }
  const params = {
    opportunity_id: link.dataset.opportunityId,
    strategy_id: link.dataset.strategyId,
    opportunity_type: link.dataset.opportunityType,
    placement: link.dataset.placement,
    referral_status: link.dataset.referralStatus,
  };
  const productParams = {
    ...params,
    opportunity_slug: link.dataset.opportunityId,
    strategy_slug: link.dataset.strategyId,
    destination_slug: link.dataset.destinationSlug,
    target_url_kind: link.dataset.targetUrlKind,
    commercial_relationship: link.dataset.commercialRelationship,
    is_affiliate: link.dataset.isAffiliate === "true",
    source_page: link.dataset.sourcePage,
    page_path: window.location.pathname,
  };
  trackAnalyticsEvent("start_click", params);
  trackAnalyticsEvent("outbound_click", params);
  trackProductAnalyticsEvent("outbound_go_click", productParams);
  trackProductAnalyticsEvent(
    link.dataset.targetUrlKind === "referral" ? "referral_outbound_click" : "official_fallback_outbound_click",
    productParams,
  );
}

function bindProductAnalyticsClick(event) {
  const link = event.target.closest("a[data-product-click]");
  if (!link) {
    return;
  }
  trackProductAnalyticsEvent(link.dataset.productClick, {
    opportunity_id: link.dataset.opportunityId,
    opportunity_slug: link.dataset.opportunityId,
    opportunity_type: link.dataset.opportunityType,
    strategy_id: link.dataset.strategyId,
    strategy_slug: link.dataset.strategyId,
    ranking_slug: link.dataset.rankingSlug,
    snapshot_id: link.dataset.snapshotId,
    snapshot_timestamp: link.dataset.snapshotTimestamp,
    placement: link.dataset.placement,
    source_page: link.dataset.sourcePage,
    page_path: window.location.pathname,
  });
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function renderOpportunityLogo(logo, label, compact = false) {
  if (!logo || !logo.asset || !logo.alt) {
    return "";
  }
  const className = compact ? "opportunity-logo opportunity-logo-compact" : "opportunity-logo";
  return `<img class="${className}" src="${escapeHtml(logo.asset)}" alt="${escapeHtml(logo.alt)}" loading="lazy" decoding="async">`;
}

async function renderCurrentRoute() {
  const root = document.getElementById("app");
  const initialMarkup = window.__GAMCRYP_INITIAL_ROUTE_RENDERED ? "" : root.innerHTML;
  window.__GAMCRYP_INITIAL_ROUTE_RENDERED = true;
  root.setAttribute("aria-busy", "true");
  setActiveNav();
  let routeAnalyticsContext = {};
  try {
    const path = window.location.pathname;
    if (path === "/") {
      const results = await Promise.allSettled([
        apiGet("/games"),
        apiGet("/rankings"),
        apiGet("/opportunities"),
      ]);
      const [gamesResult, rankingsResult, opportunitiesResult] = results;
      const games = gamesResult.status === "fulfilled" ? gamesResult.value : { items: [] };
      const rankings = rankingsResult.status === "fulfilled" ? rankingsResult.value : { items: [], page: { total: 0 } };
      const opportunities = opportunitiesResult.status === "fulfilled" ? opportunitiesResult.value : { items: [] };
      const degradedMessages = results
        .filter((result) => result.status === "rejected")
        .map((result) => result.reason?.message || "A data request failed.");
      if (results.every((result) => result.status === "rejected")) {
        preserveServerRenderedPage(root, initialMarkup, results[0].reason);
      } else {
        root.innerHTML = renderHomeShell(games.items, rankings, opportunities.items, degradedMessages);
      }
      routeAnalyticsContext = rankingAnalyticsContext(rankings, "home");
      bindFinder(root);
    } else if (path === "/rankings") {
      const rankings = await apiGet(`/rankings${window.location.search}`);
      root.innerHTML = renderRankingsPage(rankings);
      routeAnalyticsContext = rankingAnalyticsContext(rankings, "rankings");
    } else if (CURATED_RANKING_FILTERS[path]) {
      const query = curatedRankingQuery(path, window.location.search);
      const constraints = CURATED_RANKING_CONSTRAINTS[path];
      const [rankings, opportunities] = constraints
        ? await Promise.all([apiGet(`/rankings${query}`), apiGet("/opportunities")])
        : [await apiGet(`/rankings${query}`), { items: [] }];
      const visibleRankings = applyCuratedRankingConstraints(rankings, opportunities.items || [], path);
      const visibleCount = visibleRankings.page?.total ?? visibleRankings.items?.length ?? 0;
      if (visibleCount < CURATED_RANKING_MIN_RESULTS) {
        root.innerHTML = renderError(new ApiError(404, "Not enough authoritative data to publish this comparison page yet."));
        return;
      }
      root.innerHTML = renderRankingsPage(visibleRankings, {
        title: CURATED_RANKING_TITLES[path] || "Curated organic rankings",
        filters: CURATED_RANKING_FILTERS[path],
      });
      routeAnalyticsContext = rankingAnalyticsContext(visibleRankings, rankingSlugForPath(path));
    } else if (path === "/opportunities") {
      root.innerHTML = renderOpportunitiesPage(await apiGet("/opportunities"));
    } else if (path.startsWith("/opportunities/")) {
      const opportunityId = decodeURIComponent(path.replace("/opportunities/", ""));
      const opportunity = await apiGet(`/opportunities/${encodeURIComponent(opportunityId)}`);
      root.innerHTML = renderOpportunityDetail(opportunity);
      routeAnalyticsContext = opportunityAnalyticsContext(opportunity);
    } else if (path.startsWith("/games/")) {
      const gameId = decodeURIComponent(path.replace("/games/", ""));
      root.innerHTML = renderGameDetail(await apiGet(`/games/${encodeURIComponent(gameId)}`));
    } else if (path.startsWith("/strategies/")) {
      const strategyId = decodeURIComponent(path.replace("/strategies/", ""));
      const [strategy, history] = await Promise.all([
        apiGet(`/strategies/${encodeURIComponent(strategyId)}`),
        apiGet(`/strategies/${encodeURIComponent(strategyId)}/history`),
      ]);
      root.innerHTML = renderStrategyDetail(strategy, history);
      routeAnalyticsContext = strategyAnalyticsContext(strategy);
    } else if (path === "/methodology") {
      root.innerHTML = renderMethodologyPage();
    } else {
      root.innerHTML = renderError(new ApiError(404, "The requested page does not exist."));
    }
    trackRouteView(path, routeAnalyticsContext);
  } catch (error) {
    preserveServerRenderedPage(root, initialMarkup, error);
  }
  root.removeAttribute("aria-busy");
  root.focus({ preventScroll: true });
  mountAnalyticsConsent();
}

function bindFinder(root) {
  const form = root.querySelector("#finder-form");
  const results = root.querySelector("#finder-results");
  const riskInput = root.querySelector("#risk-max");
  const riskOutput = root.querySelector("#risk-output");
  const confidenceInput = root.querySelector("#confidence-min");
  const confidenceOutput = root.querySelector("#confidence-output");
  riskInput.addEventListener("input", () => {
    riskOutput.value = riskInput.value;
  });
  confidenceInput.addEventListener("input", () => {
    confidenceOutput.value = confidenceInput.value;
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const filters = {
      capitalMax: data.get("capitalMax"),
      riskMax: data.get("riskMax"),
      confidenceMin: data.get("confidenceMin"),
      gameId: data.get("gameId"),
      opportunityType: data.get("opportunityType"),
      economyType: data.get("economyType"),
    };
    trackProductAnalyticsEvent("ranking_filter_used", {
      capital_max: filters.capitalMax,
      confidence_min: filters.confidenceMin,
      risk_max: filters.riskMax,
      game_id: filters.gameId,
      opportunity_type: filters.opportunityType,
      economy_type: filters.economyType,
      ranking_slug: "home",
      page_path: window.location.pathname,
    });
    results.innerHTML = renderLoading();
    try {
      const rankings = await apiGet(buildRankingsPath(filters));
      results.innerHTML = renderRankingsTable(rankings, { compact: true });
    } catch (error) {
      results.innerHTML = renderError(error);
    }
  });
}

function setActiveNav() {
  const current = window.location.pathname;
  document.querySelectorAll(".site-nav a").forEach((link) => {
    const href = link.getAttribute("href");
    const active = href === "/" ? current === "/" : current.startsWith(href);
    link.classList.toggle("active", active);
  });
}

if (typeof window !== "undefined") {
  window.addEventListener("popstate", renderCurrentRoute);
  document.addEventListener("click", (event) => {
    bindAnalyticsConsentClick(event);
    bindOutboundAnalytics(event);
    bindProductAnalyticsClick(event);
    const link = event.target.closest("a[data-link]");
    if (!link || link.origin !== window.location.origin) {
      return;
    }
    event.preventDefault();
    window.history.pushState({}, "", link.href);
    renderCurrentRoute();
  });
  initializeErrorTracking();
  if (analyticsConsent() === "accepted") {
    initializeAnalytics();
    initializeProductAnalytics();
  }
  renderCurrentRoute();
}
