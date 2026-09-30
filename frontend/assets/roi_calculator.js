const USD_SCALE = 1_000_000n;
const MAX_AMOUNT_WHOLE_DIGITS = 12;
const MAX_HORIZON_DAYS = 3650;

/** Parse a non-negative, user-entered USD value into exact micro-dollars. */
export function parseCalculatorUsd(value, label = "Amount") {
  const input = String(value ?? "").trim().replace(",", ".");
  const match = input.match(/^(\d{1,12})(?:\.(\d{1,6}))?$/);
  if (!match || match[1].length > MAX_AMOUNT_WHOLE_DIGITS) {
    throw new Error(`${label} must be a non-negative USD amount with up to 6 decimal places.`);
  }
  const whole = BigInt(match[1]);
  const fraction = BigInt((match[2] || "").padEnd(6, "0") || "0");
  return whole * USD_SCALE + fraction;
}

/**
 * Calculate a cash-flow-only scenario from explicit visitor assumptions.
 * Values remain integer micro-dollars; no binary floating-point is used for money.
 */
export function calculateRoiScenario({
  initialOutlay,
  dailyRealizableRewards,
  dailyOperatingCosts,
  horizonDays,
  activeMinutesPerDay = "",
}) {
  const initial = parseCalculatorUsd(initialOutlay, "Initial outlay");
  if (initial <= 0n) throw new Error("Initial outlay must be greater than zero.");

  const rewards = parseCalculatorUsd(dailyRealizableRewards, "Daily realizable rewards");
  const costs = parseCalculatorUsd(dailyOperatingCosts, "Daily operating costs");
  const daysText = String(horizonDays ?? "").trim();
  if (!/^\d{1,4}$/.test(daysText)) throw new Error("Analysis period must be a whole number of days.");
  const days = Number(daysText);
  if (days < 1 || days > MAX_HORIZON_DAYS) {
    throw new Error(`Analysis period must be between 1 and ${MAX_HORIZON_DAYS} days.`);
  }

  const netPerDay = rewards - costs;
  const totalNetCashFlow = netPerDay * BigInt(days);
  const roiHundredthsPercent = roundRatio(totalNetCashFlow * 10_000n, initial);
  const breakEvenDays = netPerDay > 0n
    ? ((initial + netPerDay - 1n) / netPerDay).toString()
    : null;

  let netPerActiveHour = null;
  const minutesText = String(activeMinutesPerDay ?? "").trim();
  if (minutesText) {
    if (!/^\d{1,4}$/.test(minutesText)) {
      throw new Error("Hands-on time must be a whole number of minutes.");
    }
    const minutes = Number(minutesText);
    if (minutes < 1 || minutes > 1440) {
      throw new Error("Hands-on time must be between 1 and 1,440 minutes per day.");
    }
    netPerActiveHour = roundRatio(netPerDay * 60n, BigInt(minutes)).toString();
  }

  return {
    initialOutlay: initial.toString(),
    dailyRealizableRewards: rewards.toString(),
    dailyOperatingCosts: costs.toString(),
    netPerDay: netPerDay.toString(),
    totalNetCashFlow: totalNetCashFlow.toString(),
    roiHundredthsPercent: roiHundredthsPercent.toString(),
    breakEvenDays,
    netPerActiveHour,
    horizonDays: days,
    basis: "user_assumptions_cash_flow_only",
  };
}

export function formatCalculatorUsd(microDollars) {
  const value = BigInt(microDollars);
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const whole = (absolute / USD_SCALE).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  let fraction = (absolute % USD_SCALE).toString().padStart(6, "0").replace(/0+$/, "");
  if (fraction.length < 2) fraction = fraction.padEnd(2, "0");
  return `${negative ? "−" : ""}$${whole}.${fraction}`;
}

export function formatCalculatorPercent(hundredthsPercent) {
  const value = BigInt(hundredthsPercent);
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  return `${negative ? "−" : ""}${absolute / 100n}.${(absolute % 100n).toString().padStart(2, "0")}%`;
}

/** Build an explicit, visitor-triggered share summary; values never enter a URL or analytics. */
export function buildRoiScenarioShareText(scenario, shareUrl) {
  const breakEven = scenario.breakEvenDays === null
    ? "Not reached at this daily net"
    : `${scenario.breakEvenDays} days (cash-flow only)`;
  const activeTime = scenario.netPerActiveHour === null
    ? "Not included"
    : `${formatCalculatorUsd(scenario.netPerActiveHour)} per measured active hour`;
  return [
    "My GameFi/DePIN cash-flow scenario (my assumptions; not a live or verified estimate)",
    `Initial outlay: ${formatCalculatorUsd(scenario.initialOutlay)}`,
    `Realizable rewards/day: ${formatCalculatorUsd(scenario.dailyRealizableRewards)}`,
    `Operating costs/day: ${formatCalculatorUsd(scenario.dailyOperatingCosts)}`,
    `Net/day: ${formatCalculatorUsd(scenario.netPerDay)}`,
    `Net over ${scenario.horizonDays} days: ${formatCalculatorUsd(scenario.totalNetCashFlow)}`,
    `Cash-flow return on initial outlay: ${formatCalculatorPercent(scenario.roiHundredthsPercent)}`,
    `Break-even: ${breakEven}`,
    `Net per active hour: ${activeTime}`,
    "Assumes daily rewards and costs remain constant; excludes asset resale/exit value. Not financial advice.",
    `Test your own assumptions: ${shareUrl}`,
  ].join("\n");
}

export function renderRoiCalculatorPage() {
  return `
    <div class="page-shell">
      <section class="page-head">
        <p class="eyebrow">Free scenario tool</p>
        <h1>GameFi &amp; DePIN ROI calculator</h1>
        <p class="lede">Estimate cash-flow return from your own setup assumptions. Enter only rewards you believe you can realize after fees—not points or speculative token values.</p>
      </section>
      <section class="calculator-layout" aria-label="Custom ROI scenario calculator">
        <form class="tool-panel" id="roi-scenario-form">
          <div class="filter-panel-head">
            <h2>Your scenario</h2>
            <p class="muted">These values stay in this browser. They are not saved or sent to GamCryp.</p>
          </div>
          <div class="form-grid calculator-fields">
            <div class="field">
              <label for="scenario-initial-outlay">Initial outlay (USD)</label>
              <input id="scenario-initial-outlay" type="text" inputmode="decimal" autocomplete="off" placeholder="e.g. 50.00" required>
              <small class="muted">Include the upfront capital and one-time setup costs.</small>
            </div>
            <div class="field">
              <label for="scenario-daily-rewards">Realizable rewards per day (USD)</label>
              <input id="scenario-daily-rewards" type="text" inputmode="decimal" autocomplete="off" placeholder="e.g. 0.250000" required>
              <small class="muted">Use a conservative amount you expect to sell or withdraw after fees.</small>
            </div>
            <div class="field">
              <label for="scenario-daily-costs">Recurring costs per day (USD)</label>
              <input id="scenario-daily-costs" type="text" inputmode="decimal" autocomplete="off" placeholder="e.g. 0.080000" required>
              <small class="muted">Include rentals, subscriptions, energy, claims, repairs, or other operating costs.</small>
            </div>
            <div class="field">
              <label for="scenario-horizon">Analysis period</label>
              <select id="scenario-horizon">
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">365 days</option>
              </select>
            </div>
            <div class="field">
              <label for="scenario-active-minutes">Hands-on time per day (optional)</label>
              <input id="scenario-active-minutes" type="text" inputmode="numeric" autocomplete="off" placeholder="e.g. 45">
              <small class="muted">Only enter active minutes you measured; the hourly figure is not an earnings forecast.</small>
            </div>
          </div>
          <div class="button-row">
            <button class="button" type="submit">Calculate my scenario</button>
            <a class="secondary-button" href="/methodology" data-link>How GamCryp models ROI</a>
          </div>
          <p id="scenario-error" class="form-error" role="alert" hidden></p>
        </form>
        <div id="scenario-result" aria-live="polite" aria-atomic="true"></div>
      </section>
      <section class="section-panel calculator-caveat">
        <h2>What this estimate does—and does not—mean</h2>
        <p class="muted">This is a cash-flow-only scenario using your inputs, not a live quote or verified GamCryp model. It assumes daily rewards and costs remain constant and does not value assets you may still own at exit. Break-even is unavailable when daily net cash flow is zero or negative. Points, unlisted rewards, and speculative token prices should not be entered as realizable earnings.</p>
      </section>
    </div>
  `;
}

export function bindRoiCalculator(root, onCalculated = () => {}, onShared = () => {}) {
  const form = root.querySelector("#roi-scenario-form");
  const output = root.querySelector("#scenario-result");
  const error = root.querySelector("#scenario-error");
  if (!form || !output || !error) return;

  let lastScenario = null;
  output.addEventListener("click", async (event) => {
    const button = event.target?.closest?.("button[data-scenario-share]");
    if (!button || !lastScenario) return;
    const document = root.ownerDocument || globalThis.document;
    const navigator = document?.defaultView?.navigator || globalThis.navigator;
    const shareUrl = buildCalculatorShareUrl(document?.location?.href || globalThis.location?.href);
    const text = buildRoiScenarioShareText(lastScenario, shareUrl);
    const status = output.querySelector("[data-scenario-share-status]");
    try {
      if (button.dataset.scenarioShare === "native" && typeof navigator?.share === "function") {
        await navigator.share({
          title: "My GameFi/DePIN scenario",
          text,
          url: shareUrl,
        });
        onShared("native_share");
        if (status) status.textContent = "Share sheet opened. Your assumptions were included only because you chose to share.";
        return;
      }
      if (typeof navigator?.clipboard?.writeText !== "function") {
        if (status) status.textContent = "Sharing is unavailable in this browser. Your scenario remains on this device.";
        return;
      }
      await navigator.clipboard.writeText(text);
      onShared("copy");
      if (status) status.textContent = "Scenario summary copied. It leaves this browser only if you paste or share it.";
    } catch (cause) {
      if (cause?.name === "AbortError") return;
      if (status) status.textContent = "Could not share this scenario. Your values remain in this browser.";
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    output.innerHTML = "";
    error.hidden = true;
    error.textContent = "";
    try {
      const scenario = calculateRoiScenario({
        initialOutlay: form.querySelector("#scenario-initial-outlay").value,
        dailyRealizableRewards: form.querySelector("#scenario-daily-rewards").value,
        dailyOperatingCosts: form.querySelector("#scenario-daily-costs").value,
        horizonDays: form.querySelector("#scenario-horizon").value,
        activeMinutesPerDay: form.querySelector("#scenario-active-minutes").value,
      });
      lastScenario = scenario;
      output.innerHTML = renderScenarioResult(scenario);
      const nativeShareButton = output.querySelector('button[data-scenario-share="native"]');
      const document = root.ownerDocument || globalThis.document;
      const navigator = document?.defaultView?.navigator || globalThis.navigator;
      if (nativeShareButton && typeof navigator?.share === "function") {
        nativeShareButton.hidden = false;
      }
      onCalculated();
    } catch (cause) {
      error.textContent = cause instanceof Error ? cause.message : "Check the values and try again.";
      error.hidden = false;
    }
  });
}

function renderScenarioResult(scenario) {
  const netTone = BigInt(scenario.netPerDay) < 0n ? "negative" : "positive";
  const breakEven = scenario.breakEvenDays === null
    ? "Not reached at this daily net"
    : `${scenario.breakEvenDays} days (cash-flow only)`;
  const effortValue = scenario.netPerActiveHour === null
    ? "Not calculated"
    : `${formatCalculatorUsd(scenario.netPerActiveHour)} / active hour`;
  return `
    <section class="section-panel calculator-result" aria-labelledby="scenario-result-title">
      <p class="eyebrow">Your assumption-based estimate</p>
      <h2 id="scenario-result-title">${scenario.horizonDays}-day cash-flow view</h2>
      <dl class="calculator-result-grid">
        <div><dt>Net cash flow / day</dt><dd class="${netTone}">${formatCalculatorUsd(scenario.netPerDay)}</dd></div>
        <div><dt>Net cash flow / period</dt><dd class="${netTone}">${formatCalculatorUsd(scenario.totalNetCashFlow)}</dd></div>
        <div><dt>Cash-flow return on initial outlay</dt><dd>${formatCalculatorPercent(scenario.roiHundredthsPercent)}</dd></div>
        <div><dt>Break-even from daily cash flow</dt><dd>${breakEven}</dd></div>
        <div><dt>Net per active hour</dt><dd>${effortValue}</dd></div>
      </dl>
      <p class="muted calculator-result-basis">Based only on the values you entered. It excludes the resale or exit value of assets.</p>
      <div class="button-row calculator-share-actions">
        <button class="secondary-button" type="button" data-scenario-share="copy">Copy share summary</button>
        <button class="secondary-button" type="button" data-scenario-share="native" hidden>Share scenario</button>
      </div>
      <p class="muted calculator-share-privacy">The summary includes the amounts and results shown above. Nothing is shared until you choose Copy or Share; no scenario values are sent to GamCryp or analytics.</p>
      <p class="muted" role="status" aria-live="polite" data-scenario-share-status></p>
    </section>
  `;
}

function buildCalculatorShareUrl(currentUrl) {
  if (!currentUrl) return "/roi-calculator?utm_source=calculator&utm_medium=share&utm_campaign=user_scenario";
  try {
    const url = new URL("/roi-calculator", currentUrl);
    url.searchParams.set("utm_source", "calculator");
    url.searchParams.set("utm_medium", "share");
    url.searchParams.set("utm_campaign", "user_scenario");
    return url.toString();
  } catch {
    return "/roi-calculator?utm_source=calculator&utm_medium=share&utm_campaign=user_scenario";
  }
}

function roundRatio(numerator, denominator) {
  if (denominator <= 0n) throw new Error("The denominator must be positive.");
  const quotient = numerator / denominator;
  const remainder = numerator % denominator;
  if (remainder === 0n || (remainder < 0n ? -remainder : remainder) * 2n < denominator) {
    return quotient;
  }
  return quotient + (numerator < 0n ? -1n : 1n);
}
