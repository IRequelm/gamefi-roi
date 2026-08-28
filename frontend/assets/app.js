const API_BASE = "/api/v1";
const CURATED_RANKING_FILTERS = {
  "/rankings/under-25": "capital_max=25",
  "/rankings/high-confidence": "confidence_min=80",
  "/rankings/gamefi": "opportunity_type=GAME",
  "/rankings/gamefi-under-10": "opportunity_type=GAME&capital_max=10",
  "/rankings/gamefi-under-50": "opportunity_type=GAME&capital_max=50",
  "/rankings/gamefi-under-100": "opportunity_type=GAME&capital_max=100",
  "/rankings/lowest-capital-gamefi": "opportunity_type=GAME&capital_max=25",
  "/rankings/highest-roi-gamefi": "opportunity_type=GAME",
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
let initializedAnalyticsId = null;
let lastTrackedPage = null;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet(path, fetcher = fetch) {
  const response = await fetcher(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
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

export function renderHomeShell(games = [], rankings = { items: [], page: { total: 0 } }, opportunities = []) {
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
      ${renderHomeAnswerBlock(rankings, opportunities)}
      ${renderTopRankingSummary(rankings)}
      ${renderCatalogStats(rankings, opportunities)}
      <section class="finder-grid" aria-label="ROI finder">
        <div id="finder-results">
          ${renderRankingsTable(rankings, { compact: true })}
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
  const types = Array.from(new Set(opportunities.map((opportunity) => opportunityTypeLabel(opportunity.opportunity_type)))).sort();
  return `
    <section class="catalog-stat-grid" aria-label="GamCryp V1 coverage">
      ${summaryItem("Reviewed opportunities", escapeHtml(String(opportunityCount)))}
      ${summaryItem("Modeled strategies", escapeHtml(String(modeledCount)))}
      ${summaryItem("Opportunity types", escapeHtml(types.join(", ") || "Unavailable"))}
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
  return `
    <section class="top-opportunity-card" aria-label="Top ranked organic strategy">
      <div class="top-opportunity-copy">
        <span class="eyebrow">Top modeled opportunity right now</span>
        <h2>${escapeHtml(snapshot.game_name)}</h2>
        <p><a class="strategy-link" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>${escapeHtml(strategy.name)}</a></p>
        <p class="muted">Ranked by modeled 30D ROI, then confidence, risk, and recency according to the organic ranking methodology.</p>
        ${renderStrategySignals(snapshot)}
        <p class="updated-note">${formatUpdatedAge(snapshot.calculated_at)} · Organic ranking from API</p>
      </div>
      <div class="choice-metrics">
        ${summaryItem("Estimated starting capital", formatMoney(snapshot.capital.total_capital))}
        ${summaryItem("Estimated net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        ${summaryItem("30-day modeled ROI", formatRatio(snapshot.roi.roi_total_30d))}
      </div>
      <div class="top-opportunity-actions">
        <a class="secondary-button" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>View strategy</a>
        ${renderDestinationButton(strategy.primary_destination, "Start", { sourcePage: "home", placement: "top_opportunity" })}
      </div>
    </section>
  `;
}

export function renderHomeAnswerBlock(rankings = { items: [], page: { total: 0 } }, opportunities = []) {
  const unavailableCount = opportunities.filter((opportunity) => !opportunity.strategy_count).length;
  const fields = [
    ["Reviewed opportunities", escapeHtml(String(opportunities.length))],
    ["Modeled strategies", escapeHtml(String(rankings.page?.total ?? (rankings.items || []).length))],
    ["Opportunity coverage", escapeHtml(Array.from(new Set(opportunities.map((item) => opportunityTypeLabel(item.opportunity_type)))).sort().join(", ") || "Unavailable")],
    ["Current top answer", escapeHtml(rankingsSummary(rankings))],
    ["Unavailable ROI policy", escapeHtml(`${unavailableCount} opportunities remain unavailable, not zero, until value is reproducible.`)],
    ["Data source", "Stored snapshots served through /api/v1; page requests do not call live providers."],
  ];
  return renderAnswerBlock(
    "Answer-ready overview",
    "GamCryp is a Web3 opportunity intelligence source for modeled ROI, risk, confidence, freshness, and explicit unavailable states.",
    fields,
  );
}

export function renderRankingsAnswerBlock(rankings = { items: [], page: { total: 0 } }, options = {}) {
  const fields = [
    ["Comparison page", escapeHtml(options.title || "Current strategy cards")],
    ["Matching modeled strategies", escapeHtml(String(rankings.page?.total ?? (rankings.items || []).length))],
    ["Ranking basis", "30D ROI descending, confidence descending, risk ascending, latest calculation descending, then strategy id."],
    ["Filters", escapeHtml(filterSummary(options.filters || ""))],
    ["Last snapshot update", escapeHtml(latestSnapshotTime(rankings))],
    ["Data source", "Latest successful persisted strategy snapshots from /api/v1/rankings."],
    ["Commercial policy", "Referral, affiliate, and sponsor metadata never changes organic ranking order or analytical scores."],
  ];
  return renderAnswerBlock("Answer-ready comparison", rankingsSummary(rankings), fields);
}

export function renderOpportunityAnswerBlock(opportunity) {
  const strategies = opportunity.strategies || [];
  const strategy = strategies.find((item) => item.latest_snapshot) || strategies[0];
  const snapshot = strategy?.latest_snapshot;
  if (strategy && snapshot) {
    const fields = strategyAnswerFields(strategy, snapshot);
    fields.unshift(["Opportunity page", escapeHtml(opportunity.name)]);
    return renderAnswerBlock("Answer-ready opportunity summary", rankingAnswer(snapshot, strategy), fields);
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
  return renderAnswerBlock("Answer-ready opportunity summary", `ROI for ${opportunity.name} is not measurable yet. ${plainUnavailableReason(opportunity)}`, fields);
}

export function renderStrategyAnswerBlock(strategy, snapshot) {
  if (!snapshot) {
    return renderAnswerBlock("Answer-ready strategy summary", `${strategy.name} has no successful stored calculation yet.`, [
      ["Strategy", escapeHtml(strategy.name)],
      ["Strategy version", escapeHtml(strategy.strategy_version)],
      ["Opportunity", escapeHtml(strategy.game_name)],
      ["Opportunity type", escapeHtml(opportunityTypeLabel(strategy.opportunity_type))],
      ["ROI status", "No successful stored calculation yet."],
    ]);
  }
  return renderAnswerBlock("Answer-ready strategy summary", rankingAnswer(snapshot, strategy), strategyAnswerFields(strategy, snapshot));
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
    ["Financial data source", "Latest successful persisted snapshot; no live provider call during page view."],
  ];
}

function renderAnswerBlock(title, summary, fields) {
  return `
    <section class="answer-card" data-ai-answer-block="true">
      <div class="section-header"><h2>${escapeHtml(title)}</h2><span class="badge info">Citation-ready</span></div>
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
  return `GamCryp currently models ${strategy.name} at ${textFromHtml(formatRatio(snapshot.roi.roi_total_30d))} 30-day ROI using ${textFromHtml(formatMoney(snapshot.capital.total_capital))} capital. Net earnings are ${textFromHtml(formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}. Risk is ${scoreText(snapshot.risk)} and Confidence is ${scoreText(snapshot.confidence)}. Latest modeled snapshot was calculated at ${formatDateTime(snapshot.calculated_at)}.`;
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
  const title = options.title || "Current strategy cards";
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Organic rankings</p>
        <h1>${escapeHtml(title)}</h1>
        <p class="lede">The order is supplied by the API: 30D ROI, confidence, risk, last calculation time, then strategy id. Brand or referral metadata never changes this order.</p>
      </section>
      ${renderRankingsAnswerBlock(rankings, { title })}
      ${renderRankingsTable(rankings)}
      ${renderSponsoredPlacements(rankings.sponsored_placements || [])}
    </div>
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
        <h1>${escapeHtml(opportunity.name)}</h1>
        <p class="lede">${escapeHtml(opportunityIntro(opportunity))}</p>
        <div class="button-row">
          ${renderDestinationButton(opportunity.primary_destination, opportunity.opportunity_type === "GAME" ? "Start" : "Open", { sourcePage: "opportunity_detail", placement: "primary_cta" })}
          ${opportunity.legacy_game_id ? `<a class="secondary-button" href="/games/${encodeURIComponent(opportunity.legacy_game_id)}" data-link>Game view</a>` : ""}
        </div>
      </section>
      ${renderOpportunityAnswerBlock(opportunity)}
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
          ? renderStrategyList(opportunity.strategies)
          : `<section class="empty-state"><h2>ROI not measurable yet</h2><p class="muted">${escapeHtml(unavailableRoiReason(opportunity))}</p></section>`
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
  return `
    <article class="opportunity-card">
      <div class="identity-row">
        <span class="badge info">${escapeHtml(opportunityTypeLabel(opportunity.opportunity_type))}</span>
        ${renderFeasibilityStatus(opportunity.data_feasibility_status)}
      </div>
      <h3><a class="strategy-link" href="/opportunities/${encodeURIComponent(opportunity.opportunity_id)}" data-link>${escapeHtml(opportunity.name)}</a></h3>
      <p class="muted">${escapeHtml(opportunityIntro(opportunity))}</p>
      <p class="muted">${strategyText}</p>
      <div class="opportunity-facts">
        ${metricItem("Opportunity type", escapeHtml(opportunityTypeLabel(opportunity.opportunity_type)))}
        ${metricItem("Reward type", escapeHtml(rewardTypes))}
        ${metricItem("Can ROI be measured?", roiText)}
      </div>
      <p class="muted watchlist-note">${opportunity.strategy_count > 0 ? "Review the modeled strategy for assumptions and current freshness." : escapeHtml(conciseUnavailableRoiReason(opportunity))}</p>
      <div class="card-actions">
        <a class="secondary-button" href="/opportunities/${encodeURIComponent(opportunity.opportunity_id)}" data-link>Learn more</a>
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
  return `
    <section class="section-panel ranking-section">
      <div class="section-header">
        <h2>${options.compact ? "Current matches" : "Ranked strategies"}</h2>
        <span class="badge info">${escapeHtml(String(rankings.page?.total ?? items.length))} stored</span>
      </div>
      <div class="ranking-card-grid">
        ${items.map(renderRankingCard).join("")}
      </div>
    </section>
  `;
}

export function renderRankingCard(item) {
  const snapshot = item.latest_snapshot;
  const strategy = item.strategy;
  return `
    <article class="ranking-card">
      <div class="ranking-card-head">
        <span class="rank-chip">#${escapeHtml(String(item.rank))}</span>
        <div>
          <a class="game-link" href="/games/${encodeURIComponent(strategy.game_id)}" data-link>${escapeHtml(snapshot.game_name)}</a>
          <h3><a class="strategy-link" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>${escapeHtml(strategy.name)}</a></h3>
          <p class="muted">${escapeHtml(strategy.strategy_version)} | ${escapeHtml(labelize(strategy.economy_type))}</p>
        </div>
      </div>
      ${renderStrategySignals(snapshot)}
      <div class="card-metrics">
        ${metricItem("Estimated starting capital", formatMoney(snapshot.capital.total_capital))}
        ${metricItem("Estimated net/day", formatMoney(snapshot.earnings.net_earnings_day, { perDay: true }))}
        ${metricItem("30-day modeled ROI", formatRatio(snapshot.roi.roi_total_30d))}
        ${metricItem("Current break-even", formatBreakEven(snapshot.roi.break_even))}
      </div>
      ${renderNetEarningsInterpretation(snapshot)}
      <div class="card-badges">
        ${renderScoreBadge(snapshot.confidence, "confidence")}
        ${renderScoreBadge(snapshot.risk, "risk")}
        ${renderFreshnessPill(snapshot.freshness, { hideFresh: true })}
        ${renderWarningsIndicator(snapshot.warnings, { hideEmpty: true })}
      </div>
      <p class="updated-note">${formatUpdatedAge(snapshot.calculated_at)}</p>
      <div class="card-actions">
        <a class="secondary-button" href="/strategies/${encodeURIComponent(strategy.strategy_id)}" data-link>View strategy</a>
        ${renderDestinationButton(strategy.primary_destination, "Start", { sourcePage: "rankings", placement: "strategy_card" })}
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
      <td><a class="game-link" href="/games/${encodeURIComponent(strategy.game_id)}" data-link>${escapeHtml(snapshot.game_name)}</a></td>
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
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Game detail</p>
        <h1>${escapeHtml(game.name)}</h1>
        <p class="lede">${escapeHtml(game.status)} game with ${escapeHtml(String(game.strategy_count))} modeled strategy.</p>
        <div class="button-row">
          ${renderDestinationButton(game.primary_destination, "Start", { sourcePage: "game_detail", placement: "primary_cta" })}
          <a class="secondary-button" href="/opportunities/${encodeURIComponent(game.opportunity_id)}" data-link>Opportunity record</a>
        </div>
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
      ${renderStrategyList(game.strategies || [])}
    </div>
  `;
}

export function renderStrategyList(strategies) {
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
  return renderRankingsTable(rankings);
}

export function renderStrategyDetail(strategy, historyPage = { items: [] }) {
  const snapshot = strategy.latest_snapshot;
  if (!snapshot) {
    return `
      <div class="page-shell">
        <section class="page-head">
          <p class="eyebrow">Strategy detail</p>
          <h1>${escapeHtml(strategy.name)}</h1>
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
        <h1>${escapeHtml(strategy.name)}</h1>
        <p class="lede">${escapeHtml(strategy.description)}</p>
        <div class="button-row">
          <span class="badge info">${escapeHtml(strategy.strategy_id)}</span>
          <span class="badge">${escapeHtml(strategy.strategy_version)}</span>
          <a class="secondary-button" href="/games/${encodeURIComponent(strategy.game_id)}" data-link>${escapeHtml(strategy.game_name)}</a>
          ${renderDestinationButton(strategy.primary_destination, "Start", { sourcePage: "strategy_detail", placement: "primary_cta" })}
        </div>
      </section>
      ${renderStrategyAnswerBlock(strategy, snapshot)}
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
          ${metricItem("Current break-even", formatBreakEven(snapshot.roi.break_even))}
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
      ${renderClassificationSummary(snapshot.classification_summary)}
      ${renderWarnings(snapshot.warnings)}
      ${renderHistory(historyPage)}
      <section class="section-panel">
        <div class="section-header"><h2>Versions</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Adapter contract", snapshot.versions.adapter_contract_version)}
          ${metricItem("ROI model", snapshot.versions.model_version)}
          ${metricItem("Scoring methodology", snapshot.versions.scoring_methodology_version || "Unavailable")}
          ${metricItem("Last calculated", `${formatUpdatedAge(snapshot.calculated_at)} (${formatDateTime(snapshot.calculated_at)})`)}
        </div>
      </section>
    </div>
  `;
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
                    <td class="metric">${valueOrUnavailable(range.values?.low_metric)}</td>
                    <td class="metric">${valueOrUnavailable(range.values?.base_metric)}</td>
                    <td class="metric">${valueOrUnavailable(range.values?.high_metric)}</td>
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
                <strong>${escapeHtml(warning.code)} (${escapeHtml(warning.severity)})</strong>
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
  const items = historyPage.items || [];
  if (items.length < 2) {
    return `
      <section class="section-panel">
        <div class="section-header"><h2>History</h2></div>
        <div class="section-body">
          <p class="muted">Insufficient history for a trend view. At least two stored snapshots are needed before showing a time-series table.</p>
        </div>
      </section>
    `;
  }
  return `
    <section class="section-panel">
      <div class="section-header"><h2>History</h2><span class="badge info">${escapeHtml(String(items.length))} snapshots</span></div>
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
    </section>
  `;
}

export function renderMethodologyPage() {
  const items = [
    ["Strategy-specific ROI", "A game does not have one universal ROI. Each result belongs to a named strategy version and model version."],
    ["Realizable earnings", "Rewards are valued after the modeled route to sell or realize them, including route costs when available."],
    ["Slippage", "Displayed spot price can overstate sellable value. A quote or market simulation is preferred when the source supports it."],
    ["Total vs at-risk capital", "Total capital is the full entry requirement. Capital at risk is the portion economically exposed after recoverable value is considered."],
    ["Confidence vs risk", "Confidence measures trust in the calculation and data. Risk measures economic downside. They are independent."],
    ["LIVE / CONFIG / DERIVED", "LIVE means current observation, CONFIG means explicit assumption, and DERIVED means calculated from observed or configured inputs."],
    ["Commercial separation", "Referral, affiliate, or sponsor relationships are disclosure metadata only. They do not change ROI, Risk, Confidence, or organic ranking order."],
    ["No guaranteed returns", "Expected value and ROI are analytical estimates, not promises, investment advice, or automated execution instructions."],
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
  if (!roi || roi.value === null || roi.value === undefined) {
    signals.push({ label: "ROI not measurable yet", tone: "warning" });
  } else if (netSign > 0) {
    signals.push({ label: "Profitable now", tone: "good" });
  } else if (netSign < 0) {
    signals.push({ label: "Unprofitable now", tone: "high" });
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
    <a class="button cta" href="${escapeHtml(href)}" title="${escapeHtml(destination.disclosure_text)}"${analytics}>
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

function valueOrUnavailable(value) {
  if (value === null || value === undefined || value === "") {
    return '<span class="muted">Unavailable</span>';
  }
  return escapeHtml(String(value));
}

function evidenceSummary(evidence) {
  const entries = Object.entries(evidence);
  if (!entries.length) {
    return "No detailed evidence payload";
  }
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${labelize(key)}: ${String(value)}`)
    .join("; ");
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
  if (elapsedDays < 14) {
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
  return escapeHtml(String(value).replace("T", " ").replace("Z", " UTC").replace(/:00 UTC$/, " UTC"));
}

export function labelize(value) {
  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
    "data-opportunity-id": destination.opportunity_id,
    "data-strategy-id": destination.strategy_id,
    "data-opportunity-type": opportunityTypeLabel(destination.opportunity_type),
    "data-placement": context.placement,
    "data-referral-status": String(destination.referral_status || (destination.is_affiliate ? "affiliate" : "none")).toLowerCase(),
  };
  return Object.entries(attributes)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .map(([key, value]) => ` ${key}="${escapeHtml(String(value))}"`)
    .join("");
}

function renderNetEarningsInterpretation(snapshot) {
  const sign = decimalSign(snapshot.earnings?.net_earnings_day?.amount ?? "0");
  if (sign < 0) {
    return `<p class="metric-note">Currently losing approximately ${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}.</p>`;
  }
  if (sign > 0) {
    return `<p class="metric-note">Currently earning approximately ${formatMoney(snapshot.earnings.net_earnings_day, { perDay: true })}.</p>`;
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

export function analyticsConsent(storage = globalThis.window?.localStorage) {
  try {
    return storage?.getItem(ANALYTICS_CONSENT_KEY) || null;
  } catch {
    return null;
  }
}

export function renderAnalyticsConsentBanner(win = globalThis.window) {
  if (!analyticsMeasurementId(win) || analyticsConsent(win?.localStorage)) {
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

export function resetAnalyticsForTests() {
  initializedAnalyticsId = null;
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

function trackRouteView(path) {
  if (path.startsWith("/opportunities/")) {
    trackAnalyticsEvent("opportunity_view", { opportunity_id: decodeURIComponent(path.replace("/opportunities/", "")), page_path: path });
  } else if (path.startsWith("/strategies/")) {
    trackAnalyticsEvent("strategy_view", { strategy_id: decodeURIComponent(path.replace("/strategies/", "")), page_path: path });
  }
  trackPageView(path);
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
  trackAnalyticsEvent("start_click", params);
  trackAnalyticsEvent("outbound_click", params);
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function renderCurrentRoute() {
  const root = document.getElementById("app");
  root.innerHTML = renderLoading();
  setActiveNav();
  try {
    const path = window.location.pathname;
    if (path === "/") {
      const [games, rankings, opportunities] = await Promise.all([
        apiGet("/games"),
        apiGet("/rankings"),
        apiGet("/opportunities"),
      ]);
      root.innerHTML = renderHomeShell(games.items, rankings, opportunities.items);
      bindFinder(root);
    } else if (path === "/rankings") {
      root.innerHTML = renderRankingsPage(await apiGet(`/rankings${window.location.search}`));
    } else if (CURATED_RANKING_FILTERS[path]) {
      root.innerHTML = renderRankingsPage(await apiGet(`/rankings${curatedRankingQuery(path, window.location.search)}`), {
        title: CURATED_RANKING_TITLES[path] || "Curated organic rankings",
        filters: CURATED_RANKING_FILTERS[path],
      });
    } else if (path === "/opportunities") {
      root.innerHTML = renderOpportunitiesPage(await apiGet("/opportunities"));
    } else if (path.startsWith("/opportunities/")) {
      const opportunityId = decodeURIComponent(path.replace("/opportunities/", ""));
      root.innerHTML = renderOpportunityDetail(await apiGet(`/opportunities/${encodeURIComponent(opportunityId)}`));
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
    } else if (path === "/methodology") {
      root.innerHTML = renderMethodologyPage();
    } else {
      root.innerHTML = renderError(new ApiError(404, "The requested page does not exist."));
    }
    trackRouteView(path);
  } catch (error) {
    root.innerHTML = renderError(error);
  }
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
    const link = event.target.closest("a[data-link]");
    if (!link || link.origin !== window.location.origin) {
      return;
    }
    event.preventDefault();
    window.history.pushState({}, "", link.href);
    renderCurrentRoute();
  });
  if (analyticsConsent() === "accepted") {
    initializeAnalytics();
  }
  renderCurrentRoute();
}
