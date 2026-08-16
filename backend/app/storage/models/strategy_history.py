"""Historical strategy snapshot persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.metadata import Base


class StrategySnapshotRecord(Base):
    __tablename__ = "strategy_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    strategy_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adapter_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    intended_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intended_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reporting_currency: Mapped[str] = mapped_column(String(32), nullable=False)
    capital_metrics_json: Mapped[dict[str, Any]] = mapped_column("capital_metrics", JSON, nullable=False)
    earnings_cost_metrics_json: Mapped[dict[str, Any]] = mapped_column("earnings_cost_metrics", JSON, nullable=False)
    roi_outputs_json: Mapped[dict[str, Any]] = mapped_column("roi_outputs", JSON, nullable=False)
    adapter_derived_values_json: Mapped[dict[str, Any]] = mapped_column("adapter_derived_values", JSON, nullable=False)
    uncertainty_ranges_json: Mapped[dict[str, Any]] = mapped_column("uncertainty_ranges", JSON, nullable=False)
    warnings_json: Mapped[list[dict[str, Any]]] = mapped_column("warnings", JSON, nullable=False)
    classification_summary_json: Mapped[dict[str, Any]] = mapped_column("classification_summary", JSON, nullable=False)
    input_observation_ids_json: Mapped[list[str]] = mapped_column("input_observation_ids", JSON, nullable=False)
    input_observation_references_json: Mapped[dict[str, Any]] = mapped_column(
        "input_observation_references",
        JSON,
        nullable=False,
    )
    freshness_summary_json: Mapped[dict[str, Any]] = mapped_column("freshness_summary", JSON, nullable=False)
    assumptions_json: Mapped[dict[str, Any]] = mapped_column("assumptions", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyCalculationFailureRecord(Base):
    __tablename__ = "strategy_calculation_failures"

    failure_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    strategy_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    intended_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intended_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    error_type: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str] = mapped_column(String(2048), nullable=False)
    input_observation_ids_json: Mapped[list[str]] = mapped_column("input_observation_ids", JSON, nullable=False)
    input_observation_references_json: Mapped[dict[str, Any]] = mapped_column(
        "input_observation_references",
        JSON,
        nullable=False,
    )
    freshness_summary_json: Mapped[dict[str, Any]] = mapped_column("freshness_summary", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
