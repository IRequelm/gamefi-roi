"""Raw observation persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.sources.observations import Observation, ObservationStatus, SourceType
from app.storage.metadata import Base


class ObservationRecord(Base):
    __tablename__ = "observations"

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_currency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_locator: Mapped[str] = mapped_column(String(1024), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fresh_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    @classmethod
    def from_observation(cls, observation: Observation) -> "ObservationRecord":
        return cls(
            observation_id=observation.observation_id,
            entity_type=observation.entity_type,
            entity_id=observation.entity_id,
            metric=observation.metric,
            value=str(observation.value) if observation.value is not None else None,
            unit=observation.unit,
            quote_currency=observation.quote_currency,
            source_provider=observation.source_provider,
            source_type=observation.source_type.value,
            source_locator=observation.source_locator,
            observed_at=observation.observed_at,
            retrieved_at=observation.retrieved_at,
            fresh_until=observation.fresh_until,
            status=observation.status.value,
            metadata_json=observation.metadata,
        )

    def to_observation(self) -> Observation:
        return Observation(
            observation_id=self.observation_id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            metric=self.metric,
            value=Decimal(self.value) if self.value is not None else None,
            unit=self.unit,
            quote_currency=self.quote_currency,
            source_provider=self.source_provider,
            source_type=SourceType(self.source_type),
            source_locator=self.source_locator,
            observed_at=_as_utc(self.observed_at),
            retrieved_at=_as_utc(self.retrieved_at),
            fresh_until=_as_utc(self.fresh_until),
            status=ObservationStatus(self.status),
            metadata=self.metadata_json,
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
