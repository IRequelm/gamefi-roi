import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateRoiScenario,
  formatCalculatorPercent,
  formatCalculatorUsd,
  parseCalculatorUsd,
  renderRoiCalculatorPage,
} from "../assets/roi_calculator.js";

test("calculator parses decimal USD exactly without floating point", () => {
  assert.equal(parseCalculatorUsd("12.340005"), 12_340_005n);
  assert.equal(parseCalculatorUsd("0,000001"), 1n);
  assert.equal(formatCalculatorUsd("1234500006"), "$1,234.500006");
});

test("positive scenario computes net cash flow, ROI, payback, and measured-effort rate", () => {
  const result = calculateRoiScenario({
    initialOutlay: "100.00",
    dailyRealizableRewards: "1.230001",
    dailyOperatingCosts: "0.230001",
    horizonDays: "30",
    activeMinutesPerDay: "30",
  });

  assert.equal(result.netPerDay, "1000000");
  assert.equal(result.totalNetCashFlow, "30000000");
  assert.equal(result.roiHundredthsPercent, "3000");
  assert.equal(formatCalculatorPercent(result.roiHundredthsPercent), "30.00%");
  assert.equal(result.breakEvenDays, "100");
  assert.equal(result.netPerActiveHour, "2000000");
  assert.equal(result.basis, "user_assumptions_cash_flow_only");
});

test("negative daily net is disclosed and has no break-even claim", () => {
  const result = calculateRoiScenario({
    initialOutlay: "100",
    dailyRealizableRewards: "0.10",
    dailyOperatingCosts: "0.20",
    horizonDays: "30",
  });

  assert.equal(result.netPerDay, "-100000");
  assert.equal(result.totalNetCashFlow, "-3000000");
  assert.equal(formatCalculatorPercent(result.roiHundredthsPercent), "−3.00%");
  assert.equal(result.breakEvenDays, null);
  assert.equal(result.netPerActiveHour, null);
});

test("calculator rejects invalid, negative, and over-precision money inputs", () => {
  assert.throws(() => parseCalculatorUsd("-1"), /non-negative USD amount/);
  assert.throws(() => parseCalculatorUsd("0.0000001"), /up to 6 decimal places/);
  assert.throws(() => calculateRoiScenario({
    initialOutlay: "0",
    dailyRealizableRewards: "1",
    dailyOperatingCosts: "0",
    horizonDays: "30",
  }), /greater than zero/);
  assert.throws(() => calculateRoiScenario({
    initialOutlay: "1",
    dailyRealizableRewards: "1",
    dailyOperatingCosts: "0",
    horizonDays: "3651",
  }), /between 1 and 3650/);
});

test("calculator page is an input-only scenario tool with explicit caveats", () => {
  const html = renderRoiCalculatorPage();
  assert.match(html, /GameFi &amp; DePIN ROI calculator/);
  assert.match(html, /id="roi-scenario-form"/);
  assert.match(html, /id="scenario-initial-outlay"/);
  assert.match(html, /id="scenario-daily-rewards"/);
  assert.match(html, /not saved or sent to GamCryp/);
  assert.match(html, /not a live quote or verified GamCryp model/);
  assert.match(html, /does not value assets you may still own at exit/);
  assert.doesNotMatch(html, /\bname=/);
});
