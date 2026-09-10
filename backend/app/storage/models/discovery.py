"""Auditable persistent records for autonomous discovery and dynamic catalog entries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.metadata import Base


class DiscoveryRecordModel(Base):
    __tablename__ = "discovery_records"

    discovery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    admission_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    discovery_score: Mapped[str] = mapped_column(String(32), nullable=False, default="0")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DynamicCatalogEntryModel(Base):
    __tablename__ = "dynamic_catalog_entries"

    opportunity_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    discovery_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    admission_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
