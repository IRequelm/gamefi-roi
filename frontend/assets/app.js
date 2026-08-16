const API_BASE = "/api/v1";

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
  addParam(params, "chain", filters.chain);
  addParam(params, "economy_type", filters.economyType);
  const query = params.toString();
  return `/rankings${query ? `?${query}` : ""}`;
}

export function renderHomeShell(games = [], rankings = { items: [], page: { total: 0 } }) {
  const economyOptions = Array.from(new Set(games.flatMap((game) => game.economy_types || []))).sort();
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Public web MVP</p>
        <h1>Find GameFi strategies by capital, confidence, and risk.</h1>
        <p class="lede">Rankings come directly from the stored API snapshots. The interface filters what already exists; it does not recalculate ROI or invent unsupported assumptions.</p>
      </section>
      <section class="finder-grid" aria-label="ROI finder">
        <form class="tool-panel" id="finder-form">
          <h2>ROI Finder</h2>
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
        <div id="finder-results">
          ${renderRankingsTable(rankings, { compact: true })}
        </div>
      </section>
    </div>
  `;
}

export function renderRankingsPage(rankings) {
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Rankings</p>
        <h1>Stored strategy rankings</h1>
        <p class="lede">The order is supplied by the API: 30D ROI, confidence, risk, last calculation time, then strategy id.</p>
      </section>
      ${renderRankingsTable(rankings)}
    </div>
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
    <section class="section-panel">
      <div class="section-header">
        <h2>${options.compact ? "Current matches" : "Ranked strategies"}</h2>
        <span class="badge info">${escapeHtml(String(rankings.page?.total ?? items.length))} stored</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Game</th>
              <th>Strategy</th>
              <th>Capital</th>
              <th>Net/day</th>
              <th>30D ROI</th>
              <th>Break-even</th>
              <th>Confidence</th>
              <th>Risk</th>
              <th>Freshness</th>
              <th>Warnings</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(renderRankingRow).join("")}
          </tbody>
        </table>
      </div>
    </section>
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
        </div>
      </section>
      ${renderFreshnessAlert(snapshot)}
      ${renderOverviewMetrics(snapshot)}
      <section class="section-panel">
        <div class="section-header"><h2>Capital Breakdown</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Total capital", formatMoney(snapshot.capital.total_capital))}
          ${metricItem("Sunk cost", formatMoney(snapshot.capital.sunk_cost))}
          ${metricItem("Recoverable capital", formatMoney(snapshot.capital.recoverable_capital))}
          ${metricItem("Capital at risk", formatMoney(snapshot.capital.capital_at_risk))}
        </div>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Earnings and Costs</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Gross nominal/day", formatMoney(snapshot.earnings.gross_nominal_earnings_day))}
          ${metricItem("Realizable/day", formatMoney(snapshot.earnings.realizable_earnings_day))}
          ${metricItem("Operating cost/day", formatMoney(snapshot.earnings.operating_cost_day))}
          ${metricItem("Transaction cost/day", formatMoney(snapshot.earnings.transaction_cost_day))}
          ${metricItem("Other cost/day", formatMoney(snapshot.earnings.other_cost_day))}
          ${metricItem("Net/day", formatMoney(snapshot.earnings.net_earnings_day))}
        </div>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Return Metrics</h2></div>
        <div class="section-body metric-grid">
          ${metricItem("Break-even", formatBreakEven(snapshot.roi.break_even))}
          ${metricItem("ROI total 7D", formatRatio(snapshot.roi.roi_total_7d))}
          ${metricItem("ROI total 30D", formatRatio(snapshot.roi.roi_total_30d))}
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
          ${metricItem("Last calculated", formatDateTime(snapshot.calculated_at))}
        </div>
      </section>
    </div>
  `;
}

export function renderOverviewMetrics(snapshot) {
  return `
    <section class="summary-grid" aria-label="Strategy summary">
      ${summaryItem("Capital", formatMoney(snapshot.capital.total_capital))}
      ${summaryItem("Net/day", formatMoney(snapshot.earnings.net_earnings_day))}
      ${summaryItem("30D ROI", formatRatio(snapshot.roi.roi_total_30d))}
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
        <div class="section-header"><h2>Warnings</h2><span class="badge good">None</span></div>
        <div class="section-body"><p class="muted">No adapter warnings are attached to this snapshot.</p></div>
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
                    <td class="metric">${formatMoney(snapshot.earnings.net_earnings_day)}</td>
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
    ["No guaranteed returns", "Expected value and ROI are analytical estimates, not promises, investment advice, or automated execution instructions."],
  ];
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Methodology</p>
        <h1>How GameFi ROI reads strategy economics</h1>
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

export function formatMoney(money) {
  if (!money || money.amount === null || money.amount === undefined) {
    return '<span class="muted">Unavailable</span>';
  }
  return `${escapeHtml(String(money.amount))} ${escapeHtml(money.currency || "")}`.trim();
}

export function formatRatio(metric) {
  if (!metric || metric.value === null || metric.value === undefined) {
    return `<span class="muted">${escapeHtml(metric?.reason || "Unavailable")}</span>`;
  }
  return `${escapeHtml(String(metric.value))}`;
}

export function formatBreakEven(metric) {
  if (!metric || metric.days === null || metric.days === undefined) {
    return `<span class="muted">${escapeHtml(metric?.reason || "Unavailable")}</span>`;
  }
  return `${escapeHtml(String(metric.days))} days`;
}

export function renderScoreBadge(score, kind) {
  if (!score?.available) {
    return '<span class="badge">Unavailable</span>';
  }
  const label = score.label || "UNKNOWN";
  return `<span class="badge ${scoreClass(label, kind)}">${escapeHtml(String(score.score))} ${escapeHtml(label)}</span>`;
}

export function scoreText(score) {
  if (!score?.available) {
    return "Unavailable";
  }
  return `${score.score} ${score.label}`;
}

export function renderFreshnessPill(freshness) {
  const status = freshness?.overall_status || "unknown";
  const className = status === "fresh" ? "good" : "warning";
  return `<span class="badge ${className}">${escapeHtml(status)}</span>`;
}

export function renderWarningsIndicator(warnings = []) {
  if (!warnings.length) {
    return '<span class="badge good">None</span>';
  }
  return `<span class="badge warning">${escapeHtml(String(warnings.length))} warning${warnings.length === 1 ? "" : "s"}</span>`;
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

function formatDateTime(value) {
  if (!value) {
    return "Unavailable";
  }
  return escapeHtml(String(value).replace("T", " ").replace("Z", " UTC"));
}

export function labelize(value) {
  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
      const [games, rankings] = await Promise.all([apiGet("/games"), apiGet("/rankings")]);
      root.innerHTML = renderHomeShell(games.items, rankings);
      bindFinder(root);
    } else if (path === "/rankings") {
      root.innerHTML = renderRankingsPage(await apiGet(`/rankings${window.location.search}`));
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
  } catch (error) {
    root.innerHTML = renderError(error);
  }
  root.focus({ preventScroll: true });
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
    const link = event.target.closest("a[data-link]");
    if (!link || link.origin !== window.location.origin) {
      return;
    }
    event.preventDefault();
    window.history.pushState({}, "", link.href);
    renderCurrentRoute();
  });
  renderCurrentRoute();
}
