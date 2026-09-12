"""Persistence boundary for discovery records and safe dynamic catalog overlays."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from app.discovery.engine import DiscoveryRecord, evaluate_admission, normalize_entity, to_json
from app.storage.models.discovery import DiscoveryRecordModel, DynamicCatalogEntryModel
from app.strategies.catalog import OpportunityCatalogEntry, OpportunityGuidance, RoiUnavailableExplanation, SourceReference
from app.strategies.taxonomy import canonical_type


class DiscoveryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def upsert(self, record: DiscoveryRecord) -> tuple[DiscoveryRecord, str]:
        decision = evaluate_admission(record)
        record.validation_status = "VERIFIED" if decision.outcome.startswith("AUTO_ADD") else decision.outcome
        record.missing_evidence = list(decision.missing_evidence)
        payload = to_json(record)
        with self.engine.begin() as connection:
            existing = connection.execute(select(DiscoveryRecordModel.__table__).where(DiscoveryRecordModel.discovery_id == record.discovery_id)).mappings().first()
            if existing is None:
                connection.execute(DiscoveryRecordModel.__table__.insert().values(
                    discovery_id=record.discovery_id, canonical_name=record.canonical_name,
                    normalized_name=normalize_entity(record.canonical_name), validation_status=record.validation_status,
                    admission_outcome=decision.outcome, discovery_score=str(record.discovery_score),
                    first_seen_at=record.first_seen_at, last_seen_at=record.last_seen_at, payload=payload,
                ))
            else:
                connection.execute(DiscoveryRecordModel.__table__.update().where(DiscoveryRecordModel.discovery_id == record.discovery_id).values(
                    canonical_name=record.canonical_name, validation_status=record.validation_status,
                    admission_outcome=decision.outcome, discovery_score=str(record.discovery_score),
                    last_seen_at=record.last_seen_at, payload=payload,
                ))
            if decision.outcome in {"AUTO_ADD_GUIDE", "AUTO_ADD_MODELED"}:
                self._admit(connection, record, decision.outcome)
        return record, decision.outcome

    def records(self) -> list[dict[str, object]]:
        with self.engine.connect() as connection:
            return [dict(row["payload"]) | {"admission_outcome": row["admission_outcome"]} for row in connection.execute(select(DiscoveryRecordModel.__table__).order_by(DiscoveryRecordModel.discovery_score.desc())).mappings()]

    def dynamic_opportunities(self) -> tuple[OpportunityCatalogEntry, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(DynamicCatalogEntryModel.__table__).where(DynamicCatalogEntryModel.status == "active")).mappings().all()
        return tuple(_catalog_entry(dict(row["payload"])) for row in rows)

    def _admit(self, connection, record: DiscoveryRecord, mode: str) -> None:
        opportunity_id = "discovered-" + normalize_entity(record.canonical_name).replace(" ", "-")
        payload = {
            "opportunity_id": opportunity_id, "opportunity_type": canonical_type(record.category), "name": record.canonical_name,
            "status": "active", "platforms": [], "chains": [], "economy_types": ["discovery"],
            "reward_asset_or_points_type": [], "value_realization_status": "unknown", "official_url": record.official_url,
            "source_references": [{"label": e.source_role, "url": e.source_url} for e in record.evidence if e.verified],
            "feasibility_summary": "Autonomously admitted from verified identity, participation, and reward evidence; financial model is not asserted.",
            "strategy_ids": [], "outbound_destination_slugs": [opportunity_id + "-official"], "aliases": record.aliases,
        }
        exists = connection.execute(
            select(DynamicCatalogEntryModel.__table__.c.opportunity_id).where(DynamicCatalogEntryModel.opportunity_id == opportunity_id)
        ).scalar_one_or_none()
        values = dict(
            opportunity_id=opportunity_id, discovery_id=record.discovery_id,
            admission_mode=mode.removeprefix("AUTO_ADD_"), status="active",
            admitted_at=datetime.now(UTC), payload=payload,
        )
        if exists is None:
            connection.execute(insert(DynamicCatalogEntryModel), values)
        else:
            connection.execute(
                DynamicCatalogEntryModel.__table__.update()
                .where(DynamicCatalogEntryModel.opportunity_id == opportunity_id)
                .values(**values)
            )


def _catalog_entry(payload: dict[str, object]) -> OpportunityCatalogEntry:
    sources = tuple(SourceReference(str(item["label"]), str(item["url"])) for item in payload.get("source_references", []))
    official = str(payload.get("official_url") or sources[0].url if sources else "https://example.invalid")
    return OpportunityCatalogEntry(
        opportunity_id=str(payload["opportunity_id"]), opportunity_type=str(payload.get("opportunity_type", "OTHER")), name=str(payload["name"]), status="active",
        platforms=tuple(str(v) for v in payload.get("platforms", [])), chains=tuple(str(v) for v in payload.get("chains", [])), economy_types=tuple(str(v) for v in payload.get("economy_types", [])),
        reward_asset_or_points_type=tuple(str(v) for v in payload.get("reward_asset_or_points_type", [])), value_realization_status="unknown", official_source_references=sources,
        data_feasibility_status="PARTIAL", feasibility_summary=str(payload.get("feasibility_summary", "")), strategy_ids=(), outbound_destination_slugs=tuple(str(v) for v in payload.get("outbound_destination_slugs", [])),
        guidance=OpportunityGuidance(how_to_start=(f"Review the official {official} destination.",)),
        roi_unavailable=RoiUnavailableExplanation("ROI is unavailable until reproducible economic inputs and a realizable exit route are evidenced.", ("entry_cost", "reward_value", "exit_path")),
    )
