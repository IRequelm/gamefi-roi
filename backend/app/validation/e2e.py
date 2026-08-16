"""Independent G12 validation calculations.

These helpers intentionally avoid importing the ROI engine calculator. They use
the documented Decimal policy and explicit strategy formulas so validation can
compare source fixtures against adapter, engine, history, API, and web outputs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

VALIDATION_DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

STRATEGY_FIXTURES = {
    "dfk-crystalvale-jeweler-cjewel-max-lock": "dfk_jeweler_golden.json",
    "farmers-world-axe-wood-production": "farmers_world_axe_golden.json",
    "splinterlands-modern-ranked-sps-ev": "splinterlands_modern_ranked_golden.json",
}


class ManualValidationError(ValueError):
    """Raised when validation inputs cannot produce a meaningful manual result."""


@dataclass(frozen=True)
class ManualValidationResult:
    strategy_id: str
    metrics: Mapping[str, Decimal | None]
    source_values: Mapping[str, Decimal]


def load_golden_fixture(strategy_id: str) -> dict[str, Any]:
    fixture_name = STRATEGY_FIXTURES[strategy_id]
    return json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))


def manual_from_golden_fixture(strategy_id: str) -> ManualValidationResult:
    fixture = load_golden_fixture(strategy_id)
    values = _decimal_mapping(fixture["strategy"])
    if strategy_id == "dfk-crystalvale-jeweler-cjewel-max-lock":
        metrics = _manual_dfk(values)
    elif strategy_id == "farmers-world-axe-wood-production":
        metrics = _manual_farmers_world(values)
    elif strategy_id == "splinterlands-modern-ranked-sps-ev":
        metrics = _manual_splinterlands(values)
    else:
        raise ManualValidationError(f"Unsupported strategy for G12 validation: {strategy_id}")
    return ManualValidationResult(strategy_id=strategy_id, metrics=metrics, source_values=values)


def manual_from_snapshot_references(strategy_id: str, references: Mapping[str, Any]) -> ManualValidationResult:
    values = _values_by_metric(references)
    if strategy_id == "dfk-crystalvale-jeweler-cjewel-max-lock":
        metrics = _manual_dfk(
            {
                "locked_jewel_amount": _required(values, "dfk.jeweler.locked_jewel_amount"),
                "lock_days": _required(values, "dfk.jeweler.lock_days"),
                "max_lock_days": _required(values, "dfk.jeweler.max_lock_days"),
                "yesterday_cjewel_balance": _required(values, "dfk.jeweler.yesterday_cjewel_balance"),
                "yesterday_reward_jewel": _required(values, "dfk.jeweler.yesterday_reward_jewel"),
                "entry_value_usd": _required(values, "dfk.jeweler.entry_value_usd"),
                "emergency_exit_value_usd": _required(values, "dfk.jeweler.emergency_exit_value_usd"),
                "jewel_reference_price_usd": _required(values, "dfk.jeweler.jewel_reference_price_usd"),
                "reward_realizable_value_usd": _required(values, "dfk.jeweler.reward_realizable_value_usd"),
                "claim_transaction_cost_usd": _required(values, "dfk.jeweler.claim_transaction_cost_usd"),
            }
        )
    elif strategy_id == "farmers-world-axe-wood-production":
        metrics = _manual_farmers_world(
            {
                "tool_count": _required(values, "farmers_world.axe.tool_count"),
                "cycles_per_day": _required(values, "farmers_world.axe.cycles_per_day"),
                "cycle_hours": _required(values, "farmers_world.axe.cycle_hours"),
                "fww_output_per_cycle": _required(values, "farmers_world.axe.fww_output_per_cycle"),
                "fwf_input_per_cycle": _required(values, "farmers_world.axe.fwf_input_per_cycle"),
                "fwg_input_per_cycle": _required(values, "farmers_world.axe.fwg_input_per_cycle"),
                "entry_value_usd": _required(values, "farmers_world.axe.entry_value_usd"),
                "exit_value_usd": _required(values, "farmers_world.axe.exit_value_usd"),
                "fww_reference_price_usd": _required(values, "farmers_world.axe.fww_reference_price_usd"),
                "fww_realizable_value_day_usd": _required(values, "farmers_world.axe.fww_realizable_value_day_usd"),
                "fwf_operating_cost_day_usd": _required(values, "farmers_world.axe.fwf_operating_cost_day_usd"),
                "fwg_operating_cost_day_usd": _required(values, "farmers_world.axe.fwg_operating_cost_day_usd"),
                "transaction_cost_day_usd": _required(values, "farmers_world.axe.transaction_cost_day_usd"),
            }
        )
    elif strategy_id == "splinterlands-modern-ranked-sps-ev":
        metrics = _manual_splinterlands(
            {
                "spellbook_cost_usd": _required(values, "splinterlands.settings.starter_pack_price_usd"),
                "battles_per_day": _required(values, "splinterlands.modern_ranked.battles_per_day"),
                "win_probability": _required(values, "splinterlands.modern_ranked.win_probability"),
                "win_probability_low": _required(values, "splinterlands.modern_ranked.win_probability_low"),
                "win_probability_high": _required(values, "splinterlands.modern_ranked.win_probability_high"),
                "sps_reward_per_win": _required(values, "splinterlands.modern_ranked.sps_reward_per_win"),
                "sps_reference_price_usd": _required(values, "splinterlands.modern_ranked.sps_reference_price_usd"),
                "realization_haircut_bps": _required(values, "splinterlands.modern_ranked.realization_haircut_bps"),
                "card_rental_cost_day_usd": _required(values, "splinterlands.modern_ranked.card_rental_cost_day_usd"),
                "transaction_cost_day_usd": _required(values, "splinterlands.modern_ranked.transaction_cost_day_usd"),
            }
        )
    else:
        raise ManualValidationError(f"Unsupported strategy for G12 validation: {strategy_id}")
    return ManualValidationResult(strategy_id=strategy_id, metrics=metrics, source_values=values)


def manual_common_outputs(
    *,
    sunk_cost: Decimal,
    recoverable_entry_cost: Decimal,
    current_recoverable_value: Decimal,
    initial_operating_reserve: Decimal,
    capital_at_risk: Decimal,
    gross_nominal_earnings_day: Decimal,
    realizable_earnings_day: Decimal,
    operating_cost_day: Decimal,
    transaction_cost_day: Decimal,
    other_cost_day: Decimal,
    cumulative_net_cash_earnings: Decimal,
    total_cash_invested_to_date: Decimal,
    break_even_basis: str = "total_capital",
) -> dict[str, Decimal | None]:
    _reject_negative(
        {
            "sunk_cost": sunk_cost,
            "recoverable_entry_cost": recoverable_entry_cost,
            "current_recoverable_value": current_recoverable_value,
            "initial_operating_reserve": initial_operating_reserve,
            "capital_at_risk": capital_at_risk,
            "gross_nominal_earnings_day": gross_nominal_earnings_day,
            "realizable_earnings_day": realizable_earnings_day,
            "operating_cost_day": operating_cost_day,
            "transaction_cost_day": transaction_cost_day,
            "other_cost_day": other_cost_day,
            "total_cash_invested_to_date": total_cash_invested_to_date,
        }
    )
    total_capital = _add(sunk_cost, recoverable_entry_cost, initial_operating_reserve)
    net_earnings_day = _sub(realizable_earnings_day, operating_cost_day, transaction_cost_day, other_cost_day)
    recovery_target = {
        "total_capital": total_capital,
        "sunk_cost": sunk_cost,
        "capital_at_risk": capital_at_risk,
    }.get(break_even_basis)
    if recovery_target is None:
        raise ManualValidationError(f"Unsupported break-even basis: {break_even_basis}")

    metrics: dict[str, Decimal | None] = {
        "total_capital": total_capital,
        "sunk_cost": sunk_cost,
        "recoverable_capital": current_recoverable_value,
        "capital_at_risk": capital_at_risk,
        "gross_nominal_earnings_day": gross_nominal_earnings_day,
        "realizable_earnings_day": realizable_earnings_day,
        "operating_cost_day": operating_cost_day,
        "transaction_cost_day": transaction_cost_day,
        "other_cost_day": other_cost_day,
        "net_earnings_day": net_earnings_day,
        "break_even_days": _divide(recovery_target, net_earnings_day) if net_earnings_day > Decimal("0") else None,
        "roi_total_7d": _roi(net_earnings_day, total_capital, Decimal("7")),
        "roi_total_30d": _roi(net_earnings_day, total_capital, Decimal("30")),
        "roi_total_90d": _roi(net_earnings_day, total_capital, Decimal("90")),
        "roi_risk_7d": _roi(net_earnings_day, capital_at_risk, Decimal("7")),
        "roi_risk_30d": _roi(net_earnings_day, capital_at_risk, Decimal("30")),
        "roi_risk_90d": _roi(net_earnings_day, capital_at_risk, Decimal("90")),
        "exit_adjusted_pnl": _sub(
            _add(cumulative_net_cash_earnings, current_recoverable_value),
            total_cash_invested_to_date,
        ),
    }
    return metrics


def assert_manual_matches_expected(
    result: ManualValidationResult,
    expected: Mapping[str, Any],
    *,
    fields: tuple[str, ...],
) -> None:
    mismatches = []
    for field in fields:
        actual = result.metrics[field]
        expected_value = None if expected[field] is None else _decimal(expected[field])
        if actual != expected_value:
            mismatches.append(f"{field}: actual={actual} expected={expected_value}")
    if mismatches:
        raise AssertionError("; ".join(mismatches))


def _manual_dfk(values: Mapping[str, Decimal]) -> dict[str, Decimal | None]:
    cjewel_received = _divide(_mul(values["locked_jewel_amount"], values["lock_days"]), values["max_lock_days"])
    user_reward_share = _divide(cjewel_received, values["yesterday_cjewel_balance"])
    reward_jewel_day = _mul(values["yesterday_reward_jewel"], user_reward_share)
    gross_nominal_earnings_day = _mul(reward_jewel_day, values["jewel_reference_price_usd"])
    return {
        "cjewel_received": cjewel_received,
        "user_reward_share": user_reward_share,
        "reward_jewel_day": reward_jewel_day,
        **manual_common_outputs(
            sunk_cost=Decimal("0"),
            recoverable_entry_cost=values["entry_value_usd"],
            current_recoverable_value=values["emergency_exit_value_usd"],
            initial_operating_reserve=Decimal("0"),
            capital_at_risk=values["entry_value_usd"],
            gross_nominal_earnings_day=gross_nominal_earnings_day,
            realizable_earnings_day=values["reward_realizable_value_usd"],
            operating_cost_day=Decimal("0"),
            transaction_cost_day=values["claim_transaction_cost_usd"],
            other_cost_day=Decimal("0"),
            cumulative_net_cash_earnings=Decimal("0"),
            total_cash_invested_to_date=values["entry_value_usd"],
        ),
    }


def _manual_farmers_world(values: Mapping[str, Decimal]) -> dict[str, Decimal | None]:
    production_cycles = _mul(values["tool_count"], values["cycles_per_day"])
    fww_output_day = _mul(production_cycles, values["fww_output_per_cycle"])
    fwf_input_day = _mul(production_cycles, values["fwf_input_per_cycle"])
    fwg_input_day = _mul(production_cycles, values["fwg_input_per_cycle"])
    gross_nominal_earnings_day = _mul(fww_output_day, values["fww_reference_price_usd"])
    operating_cost_day = _add(values["fwf_operating_cost_day_usd"], values["fwg_operating_cost_day_usd"])
    return {
        "fww_output_day": fww_output_day,
        "fwf_input_day": fwf_input_day,
        "fwg_input_day": fwg_input_day,
        **manual_common_outputs(
            sunk_cost=Decimal("0"),
            recoverable_entry_cost=values["entry_value_usd"],
            current_recoverable_value=values["exit_value_usd"],
            initial_operating_reserve=Decimal("0"),
            capital_at_risk=values["entry_value_usd"],
            gross_nominal_earnings_day=gross_nominal_earnings_day,
            realizable_earnings_day=values["fww_realizable_value_day_usd"],
            operating_cost_day=operating_cost_day,
            transaction_cost_day=values["transaction_cost_day_usd"],
            other_cost_day=Decimal("0"),
            cumulative_net_cash_earnings=Decimal("0"),
            total_cash_invested_to_date=values["entry_value_usd"],
        ),
    }


def _manual_splinterlands(values: Mapping[str, Decimal]) -> dict[str, Decimal | None]:
    expected_wins_day = _mul(values["battles_per_day"], values["win_probability"])
    expected_wins_day_low = _mul(values["battles_per_day"], values["win_probability_low"])
    expected_wins_day_high = _mul(values["battles_per_day"], values["win_probability_high"])
    expected_sps_day = _mul(expected_wins_day, values["sps_reward_per_win"])
    expected_sps_day_low = _mul(expected_wins_day_low, values["sps_reward_per_win"])
    expected_sps_day_high = _mul(expected_wins_day_high, values["sps_reward_per_win"])
    gross_nominal_earnings_day = _mul(expected_sps_day, values["sps_reference_price_usd"])
    realization_multiplier = _sub(Decimal("1"), _divide(values["realization_haircut_bps"], Decimal("10000")))
    realizable_earnings_day = _mul(_mul(expected_sps_day, values["sps_reference_price_usd"]), realization_multiplier)
    realizable_earnings_day_low = _mul(_mul(expected_sps_day_low, values["sps_reference_price_usd"]), realization_multiplier)
    realizable_earnings_day_high = _mul(_mul(expected_sps_day_high, values["sps_reference_price_usd"]), realization_multiplier)
    common = manual_common_outputs(
        sunk_cost=values["spellbook_cost_usd"],
        recoverable_entry_cost=Decimal("0"),
        current_recoverable_value=Decimal("0"),
        initial_operating_reserve=Decimal("0"),
        capital_at_risk=values["spellbook_cost_usd"],
        gross_nominal_earnings_day=gross_nominal_earnings_day,
        realizable_earnings_day=realizable_earnings_day,
        operating_cost_day=values["card_rental_cost_day_usd"],
        transaction_cost_day=values["transaction_cost_day_usd"],
        other_cost_day=Decimal("0"),
        cumulative_net_cash_earnings=Decimal("0"),
        total_cash_invested_to_date=values["spellbook_cost_usd"],
    )
    daily_cost = _add(values["card_rental_cost_day_usd"], values["transaction_cost_day_usd"])
    return {
        "expected_wins_day": expected_wins_day,
        "expected_wins_day_low": expected_wins_day_low,
        "expected_wins_day_high": expected_wins_day_high,
        "expected_sps_day": expected_sps_day,
        "expected_sps_day_low": expected_sps_day_low,
        "expected_sps_day_high": expected_sps_day_high,
        "realizable_earnings_day_low": realizable_earnings_day_low,
        "realizable_earnings_day_high": realizable_earnings_day_high,
        "net_earnings_day_low": _sub(realizable_earnings_day_low, daily_cost),
        "net_earnings_day_high": _sub(realizable_earnings_day_high, daily_cost),
        **common,
    }


def _values_by_metric(references: Mapping[str, Any]) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for reference in references.values():
        if not isinstance(reference, Mapping):
            continue
        value = reference.get("value")
        metric = reference.get("metric")
        if metric is None or value is None:
            continue
        values[str(metric)] = _decimal(value)
    return values


def _decimal_mapping(payload: Mapping[str, Any]) -> dict[str, Decimal]:
    return {str(key): _decimal(value) for key, value in payload.items()}


def _required(values: Mapping[str, Decimal], key: str) -> Decimal:
    try:
        return values[key]
    except KeyError as exc:
        raise ManualValidationError(f"Missing required validation source value: {key}") from exc


def _reject_negative(values: Mapping[str, Decimal]) -> None:
    for name, value in values.items():
        if value < Decimal("0"):
            raise ManualValidationError(f"{name} must be non-negative for ROI validation")


def _roi(net_earnings_day: Decimal, denominator: Decimal, days: Decimal) -> Decimal | None:
    if denominator == Decimal("0"):
        return None
    if denominator < Decimal("0"):
        raise ManualValidationError("ROI denominator must not be negative")
    return _divide(_mul(net_earnings_day, days), denominator)


def _decimal(value: Any) -> Decimal:
    return VALIDATION_DECIMAL_CONTEXT.create_decimal(str(value))


def _add(*values: Decimal) -> Decimal:
    total = Decimal("0")
    for value in values:
        total = VALIDATION_DECIMAL_CONTEXT.add(total, value)
    return total


def _sub(first: Decimal, *rest: Decimal) -> Decimal:
    result = first
    for value in rest:
        result = VALIDATION_DECIMAL_CONTEXT.subtract(result, value)
    return result


def _mul(first: Decimal, second: Decimal) -> Decimal:
    return VALIDATION_DECIMAL_CONTEXT.multiply(first, second)


def _divide(first: Decimal, second: Decimal) -> Decimal:
    return VALIDATION_DECIMAL_CONTEXT.divide(first, second)


def main() -> int:
    fields_by_strategy = {
        "dfk-crystalvale-jeweler-cjewel-max-lock": (
            "cjewel_received",
            "user_reward_share",
            "reward_jewel_day",
            "gross_nominal_earnings_day",
            "realizable_earnings_day",
            "transaction_cost_day",
            "net_earnings_day",
            "total_capital",
            "recoverable_capital",
            "capital_at_risk",
            "break_even_days",
            "roi_total_30d",
            "roi_risk_30d",
            "exit_adjusted_pnl",
        ),
        "farmers-world-axe-wood-production": (
            "fww_output_day",
            "fwf_input_day",
            "fwg_input_day",
            "gross_nominal_earnings_day",
            "realizable_earnings_day",
            "operating_cost_day",
            "transaction_cost_day",
            "net_earnings_day",
            "total_capital",
            "recoverable_capital",
            "capital_at_risk",
            "break_even_days",
            "roi_total_30d",
            "roi_risk_30d",
            "exit_adjusted_pnl",
        ),
        "splinterlands-modern-ranked-sps-ev": (
            "expected_wins_day",
            "expected_sps_day",
            "gross_nominal_earnings_day",
            "realizable_earnings_day",
            "realizable_earnings_day_low",
            "realizable_earnings_day_high",
            "operating_cost_day",
            "transaction_cost_day",
            "net_earnings_day",
            "net_earnings_day_low",
            "net_earnings_day_high",
            "total_capital",
            "sunk_cost",
            "recoverable_capital",
            "capital_at_risk",
            "break_even_days",
            "roi_total_30d",
            "roi_risk_30d",
            "exit_adjusted_pnl",
        ),
    }
    for strategy_id, fields in fields_by_strategy.items():
        result = manual_from_golden_fixture(strategy_id)
        expected = load_golden_fixture(strategy_id)["manual_expected"]
        assert_manual_matches_expected(result, expected, fields=fields)
        print(f"[PASS] {strategy_id} manual fixture validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
