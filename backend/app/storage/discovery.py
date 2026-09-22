"""Persistence boundary for discovery records and safe dynamic catalog overlays."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from urllib.parse import urlparse

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from app.discovery.engine import DiscoveryRecord, EvidenceRecord, Signal, evaluate_admission, normalize_entity, score_discovery, to_json
from app.discovery.approval import DiscoveryApprovalEmailConfig, DiscoveryApprovalMailer, create_approval_token, hash_approval_token
from app.storage.models.discovery import DiscoveryRecordModel, DynamicCatalogEntryModel
from app.strategies.catalog import OpportunityCatalogEntry, OpportunityGuidance, RoiUnavailableExplanation, SourceReference
from app.strategies.taxonomy import canonical_type


class DiscoveryRepository:
    def __init__(self, engine: Engine, *, approval_mailer: DiscoveryApprovalMailer | None = None) -> None:
        self.engine = engine
        if approval_mailer is not None:
            self.approval_mailer = approval_mailer
        else:
            config = DiscoveryApprovalEmailConfig.from_environment()
            self.approval_mailer = DiscoveryApprovalMailer(config) if config.enabled else None

    def upsert(self, record: DiscoveryRecord) -> tuple[DiscoveryRecord, str]:
        decision = evaluate_admission(record)
        record.validation_status = "VERIFIED" if decision.outcome.startswith("AUTO_ADD") else decision.outcome
        record.missing_evidence = list(decision.missing_evidence)
        payload = to_json(record)
        with self.engine.begin() as connection:
            existing = connection.execute(select(DiscoveryRecordModel.__table__).where(DiscoveryRecordModel.discovery_id == record.discovery_id)).mappings().first()
            is_new = existing is None
            approval_status = "PENDING" if decision.outcome.startswith("AUTO_ADD") else "NOT_REQUIRED"
            if existing is None:
                connection.execute(DiscoveryRecordModel.__table__.insert().values(
                    discovery_id=record.discovery_id, canonical_name=record.canonical_name,
                    normalized_name=normalize_entity(record.canonical_name), validation_status=record.validation_status,
                    admission_outcome=decision.outcome, discovery_score=str(record.discovery_score),
                    approval_status=approval_status,
                    first_seen_at=record.first_seen_at, last_seen_at=record.last_seen_at, payload=payload,
                ))
            else:
                connection.execute(DiscoveryRecordModel.__table__.update().where(DiscoveryRecordModel.discovery_id == record.discovery_id).values(
                    canonical_name=record.canonical_name, validation_status=record.validation_status,
                    admission_outcome=decision.outcome, discovery_score=str(record.discovery_score),
                    last_seen_at=record.last_seen_at, payload=payload,
                ))
            if decision.outcome in {"AUTO_ADD_GUIDE", "AUTO_ADD_MODELED"} and existing is not None and existing["approval_status"] == "APPROVED":
                if existing["admission_outcome"] == "RESEARCH_CANDIDATE":
                    self._retire_research_candidate(connection, payload)
                self._admit(connection, record, decision.outcome)
        if is_new and decision.outcome.startswith("AUTO_ADD") and self.approval_mailer is not None and self.approval_mailer.config.enabled:
            self.request_approval(record, decision)
        return record, decision.outcome

    def request_approval(self, record: DiscoveryRecord, decision=None) -> str:
        if self.approval_mailer is None or not self.approval_mailer.config.enabled:
            return "disabled"
        decision = decision or evaluate_admission(record)
        if not decision.outcome.startswith("AUTO_ADD"):
            return "not_required"
        token = create_approval_token()
        self.approval_mailer.send(record, decision, token)
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                DiscoveryRecordModel.__table__.update()
                .where(DiscoveryRecordModel.discovery_id == record.discovery_id)
                .values(approval_status="PENDING", approval_token_hash=hash_approval_token(token), approval_requested_at=now)
            )
        return "sent"

    def upsert_research_lead(self, suggestion: dict[str, object], *, rotate_pending_token: bool = True) -> tuple[dict[str, object], str, bool]:
        """Persist a trend lead and return a one-time approval token for a new lead.

        A lead is deliberately not a DiscoveryRecord admission.  It becomes a
        visible RESEARCH candidate only after the operator explicitly approves
        the token-bound email command; it never acquires an official URL or ROI
        claim from a trend signal alone.
        """
        name = str(suggestion.get("candidate_name") or "").strip()
        if len(name) < 3:
            raise ValueError("research lead candidate_name must contain at least three characters")
        source = str(suggestion.get("discovery_source") or "unknown").strip()
        query = str(suggestion.get("discovery_query") or name).strip()
        key = "|".join((source.casefold(), name.casefold(), query.casefold()))
        lead_id = "lead-" + sha256(key.encode("utf-8")).hexdigest()[:24]
        now = datetime.now(UTC)
        raw_value = suggestion.get("trend_value")
        score = str(raw_value) if isinstance(raw_value, (int, float, str)) else "0"
        payload: dict[str, object] = {
            "discovery_id": lead_id,
            "canonical_name": name,
            "normalized_name": normalize_entity(name),
            "aliases": [],
            "category": "RESEARCH",
            "official_url": None,
            "discovery_source": source,
            "discovery_query": query,
            "first_seen_at": now.isoformat(),
            "last_seen_at": now.isoformat(),
            "signals": [{
                "name": "search_momentum" if source in {"google_trends", "google_news"} else "social_momentum",
                "value": raw_value if isinstance(raw_value, (int, float, str)) else None,
                "source": source,
                "observed_at": now.isoformat(),
                "status": "LIVE_RESEARCH_LEAD",
                "explanation": str(suggestion.get("reason") or "Trend signal requires official-source research."),
            }],
            "evidence": [],
            "evidence_strength": "UNKNOWN",
            "missing_evidence": ["official identity", "participation requirements", "reward mechanism", "exit path"],
            "risk_flags": [],
            "validation_status": "RESEARCH_REQUIRED",
            "matched_opportunity_id": None,
            "discovery_score": score,
            "research_priority": "MEDIUM",
            "why_discovered": str(suggestion.get("reason") or "Recorded trend signal requires research."),
            "trend_value": raw_value,
            "source_locator": suggestion.get("source_locator"),
            "search_locator": suggestion.get("search_locator"),
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(DiscoveryRecordModel.__table__)
                .where(DiscoveryRecordModel.discovery_id == lead_id)
            ).mappings().first()
            if existing is not None:
                retry_token = None
                if existing["approval_status"] == "PENDING" and rotate_pending_token:
                    # A previous SMTP attempt may have failed after the lead
                    # was persisted. Rotate the one-time token so the worker
                    # can safely retry delivery without exposing or reusing a
                    # stale token.
                    retry_token = create_approval_token()
                connection.execute(
                    DiscoveryRecordModel.__table__.update()
                    .where(DiscoveryRecordModel.discovery_id == lead_id)
                    .values(
                        last_seen_at=now,
                        payload=payload,
                        discovery_score=score,
                        approval_token_hash=hash_approval_token(retry_token) if retry_token else existing["approval_token_hash"],
                        approval_requested_at=now if retry_token else existing["approval_requested_at"],
                    )
                )
                return payload, retry_token or "", False
            token = create_approval_token()
            connection.execute(
                DiscoveryRecordModel.__table__.insert().values(
                    discovery_id=lead_id,
                    canonical_name=name,
                    normalized_name=normalize_entity(name),
                    validation_status="RESEARCH_REQUIRED",
                    admission_outcome="RESEARCH_CANDIDATE",
                    discovery_score=score,
                    approval_status="PENDING",
                    approval_token_hash=hash_approval_token(token),
                    approval_requested_at=now,
                    first_seen_at=now,
                    last_seen_at=now,
                    payload=payload,
                )
            )
            return payload, token, True

    def decide_token(self, token: str, *, approve: bool) -> dict[str, str]:
        token_hash = hash_approval_token(token)
        with self.engine.begin() as connection:
            row = connection.execute(select(DiscoveryRecordModel.__table__).where(DiscoveryRecordModel.approval_token_hash == token_hash)).mappings().first()
            if row is None or row["approval_status"] != "PENDING" or not compare_digest(str(row["approval_token_hash"] or ""), token_hash):
                return {"status": "invalid", "discovery_id": ""}
            status = "APPROVED" if approve else "REJECTED"
            connection.execute(
                DiscoveryRecordModel.__table__.update()
                .where(DiscoveryRecordModel.discovery_id == row["discovery_id"])
                .values(approval_status=status, approval_decided_at=datetime.now(UTC), approval_token_hash=None)
            )
            if approve:
                if row["admission_outcome"] == "RESEARCH_CANDIDATE":
                    self._admit_research_payload(connection, row["payload"])
                else:
                    self._admit_payload(connection, row["payload"], row["admission_outcome"] or "AUTO_ADD_GUIDE")
            return {"status": status.lower(), "discovery_id": str(row["discovery_id"])}

    def enrich_research_candidate(
        self,
        discovery_id: str,
        *,
        category: str,
        official_url: str,
        evidence: list[EvidenceRecord],
    ) -> tuple[DiscoveryRecord, str]:
        """Promote an approved research lead using operator-reviewed evidence."""
        parsed_official = urlparse(official_url)
        if parsed_official.scheme != "https" or not parsed_official.netloc:
            raise ValueError("official_url must be an absolute HTTPS URL")
        if not evidence:
            raise ValueError("at least one operator-reviewed evidence record is required")
        for item in evidence:
            parsed_source = urlparse(item.source_url)
            if parsed_source.scheme != "https" or not parsed_source.netloc:
                raise ValueError("evidence source URLs must be absolute HTTPS URLs")
            if not item.verified:
                raise ValueError("enrichment accepts only verified evidence records")
            if not item.fact.strip():
                raise ValueError("evidence facts must not be empty")
        with self.engine.connect() as connection:
            row = connection.execute(
                select(DiscoveryRecordModel.__table__)
                .where(DiscoveryRecordModel.discovery_id == discovery_id)
            ).mappings().first()
        if row is None:
            raise ValueError(f"unknown discovery_id: {discovery_id}")
        if row["approval_status"] != "APPROVED":
            raise ValueError("research candidate must be explicitly approved before enrichment")
        payload = dict(row["payload"] or {})
        now = datetime.now(UTC)
        record = DiscoveryRecord(
            canonical_name=str(payload["canonical_name"]),
            aliases=list(payload.get("aliases", [])),
            category=category,
            official_url=official_url,
            discovery_source=str(payload.get("discovery_source", "unknown")),
            discovery_query=payload.get("discovery_query"),
            first_seen_at=_parse_datetime(payload.get("first_seen_at"), fallback=now),
            last_seen_at=now,
            signals=[
                Signal(
                    name=str(item.get("name", "search_momentum")),
                    value=float(item["value"]) if isinstance(item.get("value"), (int, float)) else None,
                    source=str(item.get("source", "discovery")),
                    observed_at=_parse_datetime(item.get("observed_at"), fallback=now),
                    status=str(item.get("status", "LIVE_RESEARCH_LEAD")),
                    explanation=str(item.get("explanation", "")),
                )
                for item in payload.get("signals", [])
            ],
            evidence=evidence,
            evidence_strength="STRONG" if len(evidence) >= 3 else "MEDIUM",
            risk_flags=list(payload.get("risk_flags", [])),
            validation_status="RESEARCH_REQUIRED",
            discovery_score=float(payload.get("discovery_score", 0) or 0),
            research_priority=str(payload.get("research_priority", "MEDIUM")),
            why_discovered=str(payload.get("why_discovered", "")),
            persisted_discovery_id=discovery_id,
        )
        score_discovery(record)
        return self.upsert(record)

    def records(self) -> list[dict[str, object]]:
        with self.engine.connect() as connection:
            return [dict(row["payload"]) | {"admission_outcome": row["admission_outcome"], "approval_status": row["approval_status"]} for row in connection.execute(select(DiscoveryRecordModel.__table__).order_by(DiscoveryRecordModel.discovery_score.desc())).mappings()]

    def dynamic_opportunities(self) -> tuple[OpportunityCatalogEntry, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(DynamicCatalogEntryModel.__table__).where(
                    DynamicCatalogEntryModel.status.in_(("active", "candidate"))
                )
            ).mappings().all()
        return tuple(_catalog_entry(dict(row["payload"])) for row in rows)

    def _admit(self, connection, record: DiscoveryRecord, mode: str) -> None:
        self._admit_payload(connection, to_json(record), mode)

    def _admit_payload(self, connection, record_payload: dict[str, object], mode: str) -> None:
        canonical_name = str(record_payload["canonical_name"])
        category = str(record_payload["category"])
        evidence = record_payload.get("evidence", [])
        guidance = _guidance_from_evidence(evidence, str(record_payload.get("official_url") or ""))
        opportunity_id = "discovered-" + normalize_entity(canonical_name).replace(" ", "-")
        payload = {
            "opportunity_id": opportunity_id, "opportunity_type": canonical_type(category), "name": canonical_name,
            "status": "active", "platforms": [], "chains": [], "economy_types": ["discovery"],
            "reward_asset_or_points_type": [], "value_realization_status": "unknown", "official_url": record_payload.get("official_url"),
            "source_references": [{"label": e["source_role"], "url": e["source_url"], "source_role": e["source_role"]} for e in evidence if e.get("verified")],
            "feasibility_summary": "Autonomously admitted from verified identity, participation, and reward evidence; financial model is not asserted.",
            "strategy_ids": [], "outbound_destination_slugs": [opportunity_id + "-official"], "aliases": record_payload.get("aliases", []),
            "guidance": guidance,
        }
        exists = connection.execute(
            select(DynamicCatalogEntryModel.__table__.c.opportunity_id).where(DynamicCatalogEntryModel.opportunity_id == opportunity_id)
        ).scalar_one_or_none()
        values = dict(
            opportunity_id=opportunity_id, discovery_id=str(record_payload["discovery_id"]),
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

    def _admit_research_payload(self, connection, record_payload: dict[str, object]) -> None:
        canonical_name = str(record_payload["canonical_name"])
        opportunity_id = "candidate-" + normalize_entity(canonical_name).replace(" ", "-")
        research_references = []
        source_locator = str(record_payload.get("source_locator") or "").strip()
        search_locator = str(record_payload.get("search_locator") or "").strip()
        if source_locator:
            research_references.append({
                "label": "Discovery article lead (not official)",
                "url": source_locator,
                "source_role": "OTHER_PUBLIC_EVIDENCE",
            })
        if search_locator and search_locator != source_locator:
            research_references.append({
                "label": "Discovery search source (not official)",
                "url": search_locator,
                "source_role": "OTHER_PUBLIC_EVIDENCE",
            })
        payload = {
            "opportunity_id": opportunity_id,
            "opportunity_type": "RESEARCH",
            "name": canonical_name,
            "status": "candidate",
            "platforms": [],
            "chains": [],
            "economy_types": [],
            "reward_asset_or_points_type": [],
            "value_realization_status": "unknown",
            "official_url": None,
            "source_references": research_references,
            "feasibility_summary": (
                "User-approved research candidate from a trend signal. Official identity, "
                "participation, reward, exit, and ROI evidence still require verification; "
                "this is not a recommendation."
            ),
            "strategy_ids": [],
            "outbound_destination_slugs": [],
            "aliases": record_payload.get("aliases", []),
            "discovery_source": record_payload.get("discovery_source"),
            "discovery_query": record_payload.get("discovery_query"),
            "trend_value": record_payload.get("trend_value"),
            "why_discovered": record_payload.get("why_discovered"),
            "discovery_source_locator": source_locator or None,
            "discovery_search_locator": search_locator or None,
        }
        values = dict(
            opportunity_id=opportunity_id,
            discovery_id=str(record_payload["discovery_id"]),
            admission_mode="RESEARCH",
            status="candidate",
            admitted_at=datetime.now(UTC),
            payload=payload,
        )
        exists = connection.execute(
            select(DynamicCatalogEntryModel.__table__.c.opportunity_id)
            .where(DynamicCatalogEntryModel.opportunity_id == opportunity_id)
        ).scalar_one_or_none()
        if exists is None:
            connection.execute(insert(DynamicCatalogEntryModel), values)
        else:
            connection.execute(
                DynamicCatalogEntryModel.__table__.update()
                .where(DynamicCatalogEntryModel.opportunity_id == opportunity_id)
                .values(**values)
            )

    def _retire_research_candidate(self, connection, record_payload: dict[str, object]) -> None:
        candidate_id = "candidate-" + normalize_entity(str(record_payload["canonical_name"])).replace(" ", "-")
        connection.execute(
            DynamicCatalogEntryModel.__table__.update()
            .where(DynamicCatalogEntryModel.opportunity_id == candidate_id)
            .values(status="inactive")
        )


def _parse_datetime(value: object, *, fallback: datetime) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return fallback


def _guidance_from_evidence(evidence: object, official_url: str) -> dict[str, list[str]]:
    """Build content guidance only from explicit operator-reviewed facts."""
    guidance = {"how_to_start": [], "what_you_need": [], "how_you_earn": [], "how_to_exit_or_claim": []}
    mapping = {
        "identity": "how_to_start",
        "participation": "how_to_start",
        "requirements": "what_you_need",
        "reward_mechanism": "how_you_earn",
        "exit_path": "how_to_exit_or_claim",
    }
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict) or not item.get("verified"):
                continue
            fact = str(item.get("fact") or "").strip()
            kind = str(item.get("fact_kind") or item.get("fact") or "").strip().casefold()
            field = mapping.get(kind)
            if field and fact:
                guidance[field].append(fact)
    if official_url and not guidance["how_to_start"]:
        guidance["how_to_start"].append(f"Review the operator-verified official source: {official_url}")
    return guidance


def _catalog_entry(payload: dict[str, object]) -> OpportunityCatalogEntry:
    sources = tuple(
        SourceReference(
            str(item["label"]),
            str(item["url"]),
            str(item.get("source_role") or item.get("label") or "DISCOVERY_SIGNAL"),
        )
        for item in payload.get("source_references", [])
    )
    official = str(payload.get("official_url") or sources[0].url if sources else "")
    guidance_text = (
        f"Review the official {official} destination."
        if official
        else "No official destination has been verified; research the candidate before relying on it."
    )
    raw_guidance = payload.get("guidance") if isinstance(payload.get("guidance"), dict) else {}
    guidance = OpportunityGuidance(
        how_to_start=tuple(str(value) for value in raw_guidance.get("how_to_start", ())) or (guidance_text,),
        what_you_need=tuple(str(value) for value in raw_guidance.get("what_you_need", ())) or None,
        how_you_earn=tuple(str(value) for value in raw_guidance.get("how_you_earn", ())) or None,
        how_to_exit_or_claim=tuple(str(value) for value in raw_guidance.get("how_to_exit_or_claim", ())) or None,
    )
    return OpportunityCatalogEntry(
        opportunity_id=str(payload["opportunity_id"]), opportunity_type=str(payload.get("opportunity_type", "RESEARCH")), name=str(payload["name"]), status=str(payload.get("status", "active")),
        platforms=tuple(str(v) for v in payload.get("platforms", [])), chains=tuple(str(v) for v in payload.get("chains", [])), economy_types=tuple(str(v) for v in payload.get("economy_types", [])),
        reward_asset_or_points_type=tuple(str(v) for v in payload.get("reward_asset_or_points_type", [])), value_realization_status="unknown", official_source_references=sources,
        data_feasibility_status="PARTIAL", feasibility_summary=str(payload.get("feasibility_summary", "")), strategy_ids=(), outbound_destination_slugs=tuple(str(v) for v in payload.get("outbound_destination_slugs", [])),
        guidance=guidance,
        roi_unavailable=RoiUnavailableExplanation("ROI is unavailable until reproducible economic inputs and a realizable exit route are evidenced.", ("entry_cost", "reward_value", "exit_path")),
    )
