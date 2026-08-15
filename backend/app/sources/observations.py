"""Normalized observations from external or verified configured sources."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceType(StrEnum):
    ONCHAIN = "onchain"
    OFFICIAL_API = "official_api"
    MARKET_API = "market_api"
    OFFICIAL_DOCS = "official_docs"
    VERIFIED_CONFIG = "verified_config"
    DERIVED_PROVIDER_DATA = "derived_provider_data"


class ObservationStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    INVALID = "invalid"
    MISSING = "missing"


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: Decimal | None
    unit: str = Field(min_length=1)
    quote_currency: str | None = None
    source_provider: str = Field(min_length=1)
    source_type: SourceType
    source_locator: str = Field(min_length=1)
    observed_at: datetime | None = None
    retrieved_at: datetime
    fresh_until: datetime
    status: ObservationStatus
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("value", mode="before")
    @classmethod
    def reject_float_values(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Observation values must be Decimal-safe and may not be floats")
        return value

    @field_validator("observed_at", "retrieved_at", "fresh_until")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Observation timestamps must be timezone-aware UTC values")
        return value.astimezone(UTC)

    @field_validator("quote_currency")
    @classmethod
    def normalize_quote_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()

    @model_validator(mode="after")
    def validate_status_and_value(self) -> "Observation":
        if self.status in {ObservationStatus.FRESH, ObservationStatus.STALE} and self.value is None:
            raise ValueError("Fresh or stale observations must carry an explicit value")
        if self.status == ObservationStatus.FRESH and self.fresh_until <= self.retrieved_at:
            raise ValueError("Fresh observations must have fresh_until after retrieved_at")
        return self

    def status_at(self, moment: datetime) -> ObservationStatus:
        normalized = self.normalize_utc(moment)
        if self.status != ObservationStatus.FRESH:
            return self.status
        if normalized is None or normalized > self.fresh_until:
            return ObservationStatus.STALE
        return ObservationStatus.FRESH
