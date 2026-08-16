"""Transparent risk and confidence scoring for strategy snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.risk.results import (
    METHODOLOGY_VERSION,
    ConfidenceLabel,
    ConfidenceScore,
    RiskLabel,
    RiskScore,
    ScoreContribution,
    SnapshotScoreResult,
    UnavailableFactor,
)
from app.storage.history import StrategySnapshot

SOURCE_AUTHORITY = {
    "onchain": Decimal("1.00"),
    "official_api": Decimal("0.95"),
    "market_api": Decimal("0.90"),
    "official_docs": Decimal("0.70"),
    "verified_config": Decimal("0.65"),
    "derived_provider_data": Decimal("0.75"),
}


class SnapshotScorer:
    methodology_version = METHODOLOGY_VERSION

    def score(
        self,
        snapshot: StrategySnapshot,
        *,
        history: Sequence[StrategySnapshot] = (),
        scored_at: datetime | None = None,
    ) -> SnapshotScoreResult:
        active_time = datetime.now(UTC) if scored_at is None else _normalize_utc(scored_at)
        confidence_contributions, confidence_unavailable = _confidence_contributions(snapshot)
        risk_contributions, risk_unavailable = _risk_contributions(snapshot, history)
        confidence_points_lost = min(100, sum(contribution.points for contribution in confidence_contributions))
        risk_points_added = min(100, sum(contribution.points for contribution in risk_contributions))

        confidence_score = 100 - confidence_points_lost
        risk_score = risk_points_added
        return SnapshotScoreResult(
            snapshot_id=snapshot.snapshot_id,
            strategy_id=snapshot.strategy_id,
            strategy_version=snapshot.strategy_version,
            methodology_version=self.methodology_version,
            scored_at=active_time,
            confidence=ConfidenceScore(
                score=confidence_score,
                label=confidence_label(confidence_score),
                points_lost=confidence_points_lost,
                contributions=tuple(confidence_contributions),
                unavailable_factors=tuple(confidence_unavailable),
            ),
            risk=RiskScore(
                score=risk_score,
                label=risk_label(risk_score),
                points_added=risk_points_added,
                contributions=tuple(risk_contributions),
                unavailable_factors=tuple(risk_unavailable),
            ),
        )


def confidence_label(score: int) -> ConfidenceLabel:
    if score >= 80:
        return ConfidenceLabel.HIGH
    if score >= 50:
        return ConfidenceLabel.MODERATE
    return ConfidenceLabel.LOW


def risk_label(score: int) -> RiskLabel:
    if score >= 75:
        return RiskLabel.VERY_HIGH
    if score >= 50:
        return RiskLabel.HIGH
    if score >= 25:
        return RiskLabel.MEDIUM
    return RiskLabel.LOW


def _confidence_contributions(snapshot: StrategySnapshot) -> tuple[list[ScoreContribution], list[UnavailableFactor]]:
    contributions: list[ScoreContribution] = []
    unavailable: list[UnavailableFactor] = []
    references = _references(snapshot)

    freshness_penalty = _freshness_penalty(snapshot)
    if freshness_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="freshness",
                points=freshness_penalty,
                reason=f"Confidence lost {freshness_penalty} points because one or more inputs were stale, invalid, or missing.",
                evidence={"status_counts": snapshot.freshness_summary.get("status_counts", {})},
            )
        )

    provenance_penalty, provenance_evidence = _provenance_penalty(snapshot, references)
    if provenance_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="provenance_completeness",
                points=provenance_penalty,
                reason=f"Confidence lost {provenance_penalty} points because input provenance is incomplete.",
                evidence=provenance_evidence,
            )
        )

    source_penalty, source_evidence = _source_authority_penalty(references)
    if source_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="source_authority",
                points=source_penalty,
                reason=f"Confidence lost {source_penalty} points because not all inputs come from top-authority live sources.",
                evidence=source_evidence,
            )
        )

    config_penalty, config_evidence = _config_confidence_penalty(snapshot, references)
    if config_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="config_dependence",
                points=config_penalty,
                reason=f"Confidence lost {config_penalty} points because required inputs depend on CONFIG assumptions.",
                evidence=config_evidence,
            )
        )

    valuation_penalty, valuation_evidence = _valuation_confidence_penalty(snapshot)
    if valuation_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="valuation_quality",
                points=valuation_penalty,
                reason=f"Confidence lost {valuation_penalty} points because valuation relies on approximation or lacks executable quote evidence.",
                evidence=valuation_evidence,
            )
        )

    uncertainty_penalty, uncertainty_evidence = _uncertainty_confidence_penalty(snapshot)
    if uncertainty_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="model_uncertainty",
                points=uncertainty_penalty,
                reason=f"Confidence lost {uncertainty_penalty} points because the model includes probabilistic or range-based assumptions.",
                evidence=uncertainty_evidence,
            )
        )

    warning_penalty, warning_evidence = _warning_confidence_penalty(snapshot)
    if warning_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="warnings",
                points=warning_penalty,
                reason=f"Confidence lost {warning_penalty} points because adapter warnings limit model certainty.",
                evidence=warning_evidence,
            )
        )

    zero_cost_penalty, zero_cost_evidence = _zero_cost_assumption_penalty(snapshot)
    if zero_cost_penalty > 0:
        contributions.append(
            ScoreContribution(
                factor="zero_cost_assumption",
                points=zero_cost_penalty,
                reason=f"Confidence lost {zero_cost_penalty} points because a modeled transaction or operating cost is explicitly zero/configured.",
                evidence=zero_cost_evidence,
            )
        )

    if not references:
        unavailable.append(UnavailableFactor("source_authority", "No input observation references are stored."))

    return contributions, unavailable


def _risk_contributions(
    snapshot: StrategySnapshot,
    history: Sequence[StrategySnapshot],
) -> tuple[list[ScoreContribution], list[UnavailableFactor]]:
    contributions: list[ScoreContribution] = []
    unavailable: list[UnavailableFactor] = []

    liquidity_points, liquidity_evidence, liquidity_available = _liquidity_risk(snapshot)
    if liquidity_points > 0:
        contributions.append(
            ScoreContribution(
                factor="liquidity_exit_quality",
                points=liquidity_points,
                reason=f"Risk gained {liquidity_points} points because liquidity, slippage, or exit-quality evidence is weak.",
                evidence=liquidity_evidence,
            )
        )
    elif not liquidity_available:
        unavailable.append(UnavailableFactor("liquidity_exit_quality", "No slippage, liquidity, or exit-quality evidence is stored."))

    lock_points, lock_evidence = _lock_exit_penalty_risk(snapshot)
    if lock_points > 0:
        contributions.append(
            ScoreContribution(
                factor="lock_exit_penalty",
                points=lock_points,
                reason=f"Risk gained {lock_points} points because capital is locked or early exit is penalized.",
                evidence=lock_evidence,
            )
        )

    uncertainty_points, uncertainty_evidence = _probabilistic_risk(snapshot)
    if uncertainty_points > 0:
        contributions.append(
            ScoreContribution(
                factor="probabilistic_uncertainty",
                points=uncertainty_points,
                reason=f"Risk gained {uncertainty_points} points because rewards depend on probability or a wide model range.",
                evidence=uncertainty_evidence,
            )
        )

    config_points, config_evidence = _config_risk(snapshot)
    if config_points > 0:
        contributions.append(
            ScoreContribution(
                factor="config_dependence",
                points=config_points,
                reason=f"Risk gained {config_points} points because economic outcomes depend on CONFIG assumptions.",
                evidence=config_evidence,
            )
        )

    yield_points, yield_evidence = _yield_weakness_risk(snapshot)
    if yield_points > 0:
        contributions.append(
            ScoreContribution(
                factor="yield_weakness",
                points=yield_points,
                reason=f"Risk gained {yield_points} points because break-even or ROI indicates weak cash yield.",
                evidence=yield_evidence,
            )
        )

    exit_loss_points, exit_loss_evidence = _recoverable_exit_loss_risk(snapshot)
    if exit_loss_points > 0:
        contributions.append(
            ScoreContribution(
                factor="recoverable_exit_loss",
                points=exit_loss_points,
                reason=f"Risk gained {exit_loss_points} points because modeled exit value is materially below capital invested.",
                evidence=exit_loss_evidence,
            )
        )

    warning_points, warning_evidence = _warning_risk(snapshot)
    if warning_points > 0:
        contributions.append(
            ScoreContribution(
                factor="warnings",
                points=warning_points,
                reason=f"Risk gained {warning_points} points because adapter warnings describe economic uncertainty.",
                evidence=warning_evidence,
            )
        )

    trend_points, trend_evidence, trend_available = _history_trend_risk(snapshot, history)
    if trend_points > 0:
        contributions.append(
            ScoreContribution(
                factor="roi_yield_deterioration_trend",
                points=trend_points,
                reason=f"Risk gained {trend_points} points because historical net earnings deteriorated.",
                evidence=trend_evidence,
            )
        )
    elif not trend_available:
        unavailable.append(
            UnavailableFactor(
                "roi_yield_deterioration_trend",
                "At least three same-version snapshots are required before scoring trend risk.",
            )
        )

    return contributions, unavailable


def _freshness_penalty(snapshot: StrategySnapshot) -> int:
    counts = dict(snapshot.freshness_summary.get("status_counts", {}))
    stale = _int_from_any(counts.get("stale"))
    invalid = _int_from_any(counts.get("invalid"))
    missing = _int_from_any(counts.get("missing"))
    return min(40, stale * 8 + invalid * 20 + missing * 20)


def _provenance_penalty(
    snapshot: StrategySnapshot,
    references: Mapping[str, Mapping[str, Any]],
) -> tuple[int, dict[str, Any]]:
    required = (
        "source_provider",
        "source_type",
        "source_locator",
        "retrieved_at",
        "value",
        "unit",
        "status_at_calculation",
    )
    expected_count = len(snapshot.input_observation_ids)
    missing_references = [observation_id for observation_id in snapshot.input_observation_ids if observation_id not in references]
    missing_fields: list[str] = []
    for observation_id, reference in references.items():
        for field_name in required:
            if reference.get(field_name) in (None, ""):
                missing_fields.append(f"{observation_id}:{field_name}")
    issue_count = len(missing_references) + len(missing_fields)
    checked_count = max(1, expected_count * len(required))
    penalty = min(25, _round_int(Decimal(issue_count) / Decimal(checked_count) * Decimal("25")))
    return penalty, {
        "missing_references": missing_references,
        "missing_fields": missing_fields,
        "input_count": expected_count,
    }


def _source_authority_penalty(references: Mapping[str, Mapping[str, Any]]) -> tuple[int, dict[str, Any]]:
    if not references:
        return 0, {"source_counts": {}, "average_quality": None}
    source_counts: dict[str, int] = {}
    total_quality = Decimal("0")
    for reference in references.values():
        source_type = str(reference.get("source_type", "unknown"))
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        total_quality += SOURCE_AUTHORITY.get(source_type, Decimal("0.50"))
    average_quality = total_quality / Decimal(len(references))
    penalty = _round_int((Decimal("1") - average_quality) * Decimal("20"))
    return penalty, {"source_counts": source_counts, "average_quality": str(average_quality)}


def _config_confidence_penalty(
    snapshot: StrategySnapshot,
    references: Mapping[str, Mapping[str, Any]],
) -> tuple[int, dict[str, Any]]:
    if references:
        input_count = len(references)
        config_count = sum(1 for reference in references.values() if reference.get("source_type") == "verified_config")
    else:
        counts = _classification_counts(snapshot)
        input_count = max(1, sum(counts.values()))
        config_count = counts.get("CONFIG", 0)
    ratio = Decimal(config_count) / Decimal(max(1, input_count))
    penalty = min(25, _round_int(ratio * Decimal("25")))
    return penalty, {"config_count": config_count, "input_count": input_count, "config_ratio": str(ratio)}


def _valuation_confidence_penalty(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    text = _snapshot_text(snapshot)
    gross = _money_amount(snapshot.earnings_cost_metrics, "gross_nominal_earnings_day")
    realizable = _money_amount(snapshot.earnings_cost_metrics, "realizable_earnings_day")
    executable_quote = "quote_exact" in text or "executable quote" in text
    approximation = any(term in text for term in ("haircut", "approx", "reference price", "spot"))
    has_haircut = gross is not None and realizable is not None and gross > Decimal("0") and realizable < gross

    if executable_quote:
        return 0, {"executable_quote_evidence": True}
    if approximation or has_haircut:
        penalty = 12 if "haircut" in text or "approx" in text else 8
        return penalty, {
            "executable_quote_evidence": False,
            "approximation_evidence": approximation,
            "gross_nominal_earnings_day": str(gross) if gross is not None else None,
            "realizable_earnings_day": str(realizable) if realizable is not None else None,
        }
    return 0, {"executable_quote_evidence": False}


def _uncertainty_confidence_penalty(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    ranges = dict(snapshot.uncertainty_ranges)
    text = _snapshot_text(snapshot)
    points = 0
    if ranges:
        points += 8
    if any(term in text for term in ("expected value", "probability", "probabilistic", "not guaranteed")):
        points += 6
    return min(15, points), {"range_count": len(ranges), "probability_text_detected": points > 0}


def _warning_confidence_penalty(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    points = 0
    for warning in snapshot.warnings:
        severity = str(warning.get("severity", "warning"))
        if severity == "critical":
            points += 20
        elif severity == "warning":
            points += 8
        elif severity == "info":
            points += 3
    return min(25, points), {"warnings": [dict(warning) for warning in snapshot.warnings]}


def _zero_cost_assumption_penalty(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    tx_cost = _money_amount(snapshot.earnings_cost_metrics, "transaction_cost_day")
    other_cost = _money_amount(snapshot.earnings_cost_metrics, "other_cost_day")
    text = _snapshot_text(snapshot)
    if (tx_cost == Decimal("0") or other_cost == Decimal("0")) and any(
        term in text for term in ("configured", "zero", "no claim gas", "transaction/resource assumption")
    ):
        return 5, {
            "transaction_cost_day": str(tx_cost) if tx_cost is not None else None,
            "other_cost_day": str(other_cost) if other_cost is not None else None,
        }
    return 0, {}


def _liquidity_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any], bool]:
    gross = _money_amount(snapshot.earnings_cost_metrics, "gross_nominal_earnings_day")
    realizable = _money_amount(snapshot.earnings_cost_metrics, "realizable_earnings_day")
    text = _snapshot_text(snapshot)
    points = 0
    evidence: dict[str, Any] = {}
    available = False

    if gross is not None and realizable is not None and gross > Decimal("0"):
        haircut = (gross - realizable) / gross
        if haircut > Decimal("0"):
            available = True
            evidence["realization_haircut_ratio"] = str(haircut)
            if haircut >= Decimal("0.15"):
                points += 25
            elif haircut >= Decimal("0.05"):
                points += 18
            elif haircut >= Decimal("0.01"):
                points += 10
            else:
                points += 4

    if "thin liquidity" in text or "market liquidity remains thin" in text:
        available = True
        points += 12
        evidence["thin_liquidity_text"] = True

    volume_values = _reference_metric_values(snapshot, "alcor.market.volume_usd_24h")
    if volume_values:
        available = True
        min_volume = min(volume_values)
        evidence["min_volume_usd_24h"] = str(min_volume)
        if min_volume < Decimal("1000"):
            points += 15
        elif min_volume < Decimal("10000"):
            points += 8

    return min(35, points), evidence, available


def _lock_exit_penalty_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    lock_days = _find_metric_decimal(snapshot, "lock_days")
    penalty_bps = _find_key_decimal(snapshot.assumptions, "penalty_bps")
    points = 0
    evidence: dict[str, Any] = {}

    if lock_days is not None:
        evidence["lock_days"] = str(lock_days)
        if lock_days >= Decimal("365"):
            points += 20
        elif lock_days >= Decimal("90"):
            points += 12
        elif lock_days > Decimal("14"):
            points += 6

    if penalty_bps is not None:
        evidence["early_exit_penalty_bps"] = str(penalty_bps)
        if penalty_bps >= Decimal("5000"):
            points += 25
        elif penalty_bps >= Decimal("1000"):
            points += 12
        elif penalty_bps > Decimal("0"):
            points += 6

    return min(35, points), evidence


def _probabilistic_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    ranges = dict(snapshot.uncertainty_ranges)
    text = _snapshot_text(snapshot)
    points = 0
    evidence: dict[str, Any] = {"range_count": len(ranges)}

    if ranges:
        points += 15
        max_width: Decimal | None = None
        for metric_range in ranges.values():
            low = _derived_decimal(snapshot, str(metric_range.get("low_metric")))
            base = _derived_decimal(snapshot, str(metric_range.get("base_metric")))
            high = _derived_decimal(snapshot, str(metric_range.get("high_metric")))
            if low is None or base is None or high is None or base == Decimal("0"):
                continue
            width = (high - low) / abs(base)
            max_width = width if max_width is None else max(max_width, width)
        if max_width is not None:
            evidence["max_range_width_ratio"] = str(max_width)
            if max_width >= Decimal("0.40"):
                points += 15
            elif max_width >= Decimal("0.20"):
                points += 8
    if any(term in text for term in ("expected value", "probability", "probabilistic", "not guaranteed")):
        points += 10
        evidence["probability_text_detected"] = True
    return min(30, points), evidence


def _config_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    counts = _classification_counts(snapshot)
    input_count = _int_from_any(snapshot.freshness_summary.get("input_count")) or sum(counts.values())
    if input_count == 0:
        return 0, {"config_count": 0, "input_count": 0}
    references = _references(snapshot)
    if references:
        config_count = sum(1 for reference in references.values() if reference.get("source_type") == "verified_config")
    else:
        config_count = counts.get("CONFIG", 0)
    ratio = Decimal(config_count) / Decimal(input_count)
    return _round_int(ratio * Decimal("20")), {
        "config_count": config_count,
        "input_count": input_count,
        "config_ratio": str(ratio),
    }


def _yield_weakness_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    break_even_days = _decimal_from_any(_nested(snapshot.roi_outputs, "break_even", "days"))
    roi_30d = _decimal_from_any(_nested(snapshot.roi_outputs, "roi_total_30d", "value"))
    net = _money_amount(snapshot.earnings_cost_metrics, "net_earnings_day")
    points = 0
    evidence = {
        "break_even_days": str(break_even_days) if break_even_days is not None else None,
        "roi_total_30d": str(roi_30d) if roi_30d is not None else None,
        "net_earnings_day": str(net) if net is not None else None,
    }

    if net is not None and net <= Decimal("0"):
        points += 30
    elif break_even_days is not None:
        if break_even_days > Decimal("365"):
            points += 18
        elif break_even_days > Decimal("180"):
            points += 12
        elif break_even_days > Decimal("90"):
            points += 6

    if roi_30d is not None:
        if roi_30d < Decimal("0.05"):
            points += 10
        elif roi_30d < Decimal("0.10"):
            points += 6
    return min(30, points), evidence


def _recoverable_exit_loss_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    total = _money_amount(snapshot.capital_metrics, "total_capital")
    recoverable = _money_amount(snapshot.capital_metrics, "recoverable_capital")
    if total is None or recoverable is None or total <= Decimal("0"):
        return 0, {"total_capital": str(total) if total is not None else None, "recoverable_capital": None}
    ratio = recoverable / total
    points = 0
    if ratio < Decimal("0.50"):
        points += 20
    elif ratio < Decimal("0.80"):
        points += 10
    return points, {"recoverable_to_total_ratio": str(ratio)}


def _warning_risk(snapshot: StrategySnapshot) -> tuple[int, dict[str, Any]]:
    points = 0
    for warning in snapshot.warnings:
        severity = str(warning.get("severity", "warning"))
        if severity == "critical":
            points += 20
        elif severity == "warning":
            points += 8
        elif severity == "info":
            points += 2
    return min(20, points), {"warnings": [dict(warning) for warning in snapshot.warnings]}


def _history_trend_risk(
    snapshot: StrategySnapshot,
    history: Sequence[StrategySnapshot],
) -> tuple[int, dict[str, Any], bool]:
    comparable = [
        item
        for item in history
        if item.strategy_id == snapshot.strategy_id
        and item.strategy_version == snapshot.strategy_version
        and item.model_version == snapshot.model_version
        and item.adapter_contract_version == snapshot.adapter_contract_version
    ]
    by_id = {item.snapshot_id: item for item in comparable}
    by_id[snapshot.snapshot_id] = snapshot
    ordered = sorted(by_id.values(), key=lambda item: item.calculated_at)
    if len(ordered) < 3:
        return 0, {"snapshot_count": len(ordered)}, False

    first = _money_amount(ordered[0].earnings_cost_metrics, "net_earnings_day")
    latest = _money_amount(ordered[-1].earnings_cost_metrics, "net_earnings_day")
    if first is None or latest is None or first <= Decimal("0"):
        return 0, {"snapshot_count": len(ordered), "first_net": str(first), "latest_net": str(latest)}, True
    ratio = latest / first
    if ratio <= Decimal("0.50"):
        return 25, {"snapshot_count": len(ordered), "latest_to_first_net_ratio": str(ratio)}, True
    if ratio <= Decimal("0.80"):
        return 15, {"snapshot_count": len(ordered), "latest_to_first_net_ratio": str(ratio)}, True
    return 0, {"snapshot_count": len(ordered), "latest_to_first_net_ratio": str(ratio)}, True


def _classification_counts(snapshot: StrategySnapshot) -> dict[str, int]:
    counts = snapshot.classification_summary.get("counts", {})
    return {str(key): _int_from_any(value) for key, value in dict(counts).items()}


def _references(snapshot: StrategySnapshot) -> dict[str, Mapping[str, Any]]:
    return {
        str(key): dict(value)
        for key, value in dict(snapshot.input_observation_references).items()
        if isinstance(value, Mapping)
    }


def _reference_metric_values(snapshot: StrategySnapshot, metric: str) -> list[Decimal]:
    values: list[Decimal] = []
    for reference in _references(snapshot).values():
        if reference.get("metric") != metric:
            continue
        value = _decimal_from_any(reference.get("value"))
        if value is not None:
            values.append(value)
    return values


def _find_metric_decimal(snapshot: StrategySnapshot, metric_suffix: str) -> Decimal | None:
    for reference in _references(snapshot).values():
        metric = str(reference.get("metric", ""))
        if metric.endswith(metric_suffix) or metric_suffix in metric:
            value = _decimal_from_any(reference.get("value"))
            if value is not None:
                return value
    return None


def _find_key_decimal(mapping: Mapping[str, Any], key_suffix: str) -> Decimal | None:
    for key, value in mapping.items():
        if key.endswith(key_suffix) or key_suffix in key:
            parsed = _decimal_from_any(value)
            if parsed is not None:
                return parsed
    return None


def _derived_decimal(snapshot: StrategySnapshot, metric: str) -> Decimal | None:
    if not metric:
        return None
    return _decimal_from_any(snapshot.adapter_derived_values.get(metric))


def _money_amount(payload: Mapping[str, Any], metric: str) -> Decimal | None:
    value = payload.get(metric)
    if isinstance(value, Mapping):
        return _decimal_from_any(value.get("amount"))
    return None


def _nested(payload: Mapping[str, Any], first: str, second: str) -> Any:
    first_value = payload.get(first)
    if not isinstance(first_value, Mapping):
        return None
    return first_value.get(second)


def _snapshot_text(snapshot: StrategySnapshot) -> str:
    parts: list[str] = []
    for payload in (
        snapshot.assumptions,
        snapshot.input_observation_references,
        snapshot.uncertainty_ranges,
        snapshot.adapter_derived_values,
    ):
        parts.append(str(payload).lower())
    parts.extend(str(warning).lower() for warning in snapshot.warnings)
    return " ".join(parts)


def _decimal_from_any(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def _int_from_any(value: Any) -> int:
    parsed = _decimal_from_any(value)
    if parsed is None:
        return 0
    return int(parsed)


def _round_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Scoring timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)
