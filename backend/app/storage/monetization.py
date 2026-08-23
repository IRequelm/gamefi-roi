"""Repository for commercial monetization records.

This repository deliberately does not import or mutate ROI snapshots, scores,
observations, or ranking services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import Engine, and_, desc, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.monetization.models import (
    MONETIZATION_METHODOLOGY_VERSION,
    MonetizationMetrics,
    MonetizationMetricValue,
    OutboundClickEvent,
    ReferralLifecycleStatus,
    ReferralProgram,
    RevenueAttribution,
    RevenueAttributionStatus,
    SponsoredPlacement,
    SponsoredPlacementStatus,
)
from app.storage.models.monetization import (
    OutboundClickEventRecord,
    ReferralProgramRecord,
    RevenueAttributionRecord,
    SponsoredPlacementRecord,
)
from app.strategies.catalog import OutboundDestination


class MonetizationPersistenceError(ValueError):
    """Raised when commercial metadata cannot be safely persisted."""


class MonetizationRepository:
    def __init__(self, bind: Engine | Connection) -> None:
        self.engine = bind

    def record_outbound_click(
        self,
        *,
        destination: OutboundDestination,
        target_url_kind: str,
        occurred_at: datetime | None = None,
        source_page: str | None = None,
        placement: str | None = None,
        coarse_session_id: str | None = None,
        user_agent_category: str = "unknown",
    ) -> OutboundClickEvent:
        event_time = _normalize_utc(occurred_at or datetime.now(UTC))
        now = datetime.now(UTC)
        record = OutboundClickEventRecord(
            event_id=str(uuid4()),
            destination_slug=destination.destination_slug,
            destination_id=destination.destination_id,
            opportunity_id=destination.opportunity_id,
            opportunity_type=destination.opportunity_type,
            game_id=destination.game_id,
            strategy_id=destination.strategy_id,
            destination_type=destination.destination_type,
            referral_status=_referral_status(destination.referral_status).value,
            commercial_relationship=destination.commercial_relationship,
            is_affiliate=destination.is_affiliate,
            target_url_kind=target_url_kind,
            source_page=_clean_optional(source_page),
            placement=_clean_optional(placement),
            coarse_session_id=_clean_optional(coarse_session_id),
            user_agent_category=_clean_token(user_agent_category, fallback="unknown"),
            occurred_at=event_time,
            created_at=now,
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(record)
            session.commit()
            return _click_from_record(record)

    def outbound_clicks(self, *, destination_slug: str | None = None) -> list[OutboundClickEvent]:
        stmt = select(OutboundClickEventRecord).order_by(OutboundClickEventRecord.occurred_at)
        if destination_slug is not None:
            stmt = stmt.where(OutboundClickEventRecord.destination_slug == destination_slug)
        with Session(self.engine) as session:
            return [_click_from_record(record) for record in session.scalars(stmt).all()]

    def save_referral_program(
        self,
        *,
        destination_slug: str,
        opportunity_id: str | None = None,
        strategy_id: str | None = None,
        affiliate_program: str | None = None,
        referral_status: ReferralLifecycleStatus | str = ReferralLifecycleStatus.NONE,
        commercial_relationship: str = "none",
        disclosure_text: str,
        verification_status: str = "unverified",
        evidence: dict[str, Any] | None = None,
        verified_at: datetime | None = None,
        last_checked_at: datetime | None = None,
    ) -> ReferralProgram:
        status = _referral_status(referral_status)
        now = datetime.now(UTC)
        program_id = str(uuid5(NAMESPACE_URL, f"gamefi-roi-referral-program|{destination_slug}"))
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(ReferralProgramRecord).where(ReferralProgramRecord.destination_slug == destination_slug)
            )
            record = existing or ReferralProgramRecord(
                program_id=program_id,
                destination_slug=destination_slug,
                created_at=now,
                updated_at=now,
                evidence_json={},
                disclosure_text="",
                commercial_relationship="none",
                referral_status=ReferralLifecycleStatus.NONE.value,
                verification_status="unverified",
            )
            record.opportunity_id = opportunity_id
            record.strategy_id = strategy_id
            record.affiliate_program = _clean_optional(affiliate_program)
            record.referral_status = status.value
            record.commercial_relationship = _clean_token(commercial_relationship, fallback="none")
            record.disclosure_text = disclosure_text
            record.verification_status = _clean_token(verification_status, fallback="unverified")
            record.evidence_json = dict(evidence or {})
            record.verified_at = _normalize_utc(verified_at) if verified_at else None
            record.last_checked_at = _normalize_utc(last_checked_at) if last_checked_at else None
            record.updated_at = now
            if existing is None:
                session.add(record)
            session.commit()
            return _referral_program_from_record(record)

    def get_referral_program(self, destination_slug: str) -> ReferralProgram | None:
        with Session(self.engine) as session:
            record = session.scalar(
                select(ReferralProgramRecord).where(ReferralProgramRecord.destination_slug == destination_slug)
            )
            return None if record is None else _referral_program_from_record(record)

    def save_revenue_attribution(
        self,
        *,
        destination_slug: str,
        click_period_start: datetime,
        click_period_end: datetime,
        attribution_status: RevenueAttributionStatus | str,
        opportunity_id: str | None = None,
        strategy_id: str | None = None,
        verified_conversion_count: int | None = None,
        revenue_amount: Decimal | str | None = None,
        revenue_currency: str | None = None,
        source_program: str | None = None,
        evidence: dict[str, Any] | None = None,
        imported_at: datetime | None = None,
    ) -> RevenueAttribution:
        status = _attribution_status(attribution_status)
        start = _normalize_utc(click_period_start)
        end = _normalize_utc(click_period_end)
        if end < start:
            raise MonetizationPersistenceError("click_period_end must be greater than or equal to click_period_start")
        if verified_conversion_count is not None and verified_conversion_count < 0:
            raise MonetizationPersistenceError("verified_conversion_count cannot be negative")
        amount = None if revenue_amount is None else Decimal(str(revenue_amount))
        currency = _clean_optional(revenue_currency)
        if (amount is None) != (currency is None):
            raise MonetizationPersistenceError("revenue_amount and revenue_currency must be provided together")

        record = RevenueAttributionRecord(
            attribution_id=str(uuid4()),
            destination_slug=destination_slug,
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            attribution_status=status.value,
            click_period_start=start,
            click_period_end=end,
            verified_conversion_count=verified_conversion_count,
            revenue_amount=str(amount) if amount is not None else None,
            revenue_currency=currency,
            source_program=_clean_optional(source_program),
            evidence_json=dict(evidence or {}),
            imported_at=_normalize_utc(imported_at or datetime.now(UTC)),
            created_at=datetime.now(UTC),
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(record)
            session.commit()
            return _revenue_attribution_from_record(record)

    def save_sponsored_placement(
        self,
        *,
        opportunity_id: str,
        surface: str,
        status: SponsoredPlacementStatus | str,
        label: str,
        disclosure_text: str,
        strategy_id: str | None = None,
        campaign_name: str | None = None,
        sponsor_name: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        audit_trail: dict[str, Any] | None = None,
    ) -> SponsoredPlacement:
        placement_status = _placement_status(status)
        now = datetime.now(UTC)
        placement_id = str(uuid5(NAMESPACE_URL, f"gamefi-roi-sponsored-placement|{opportunity_id}|{surface}|{label}"))
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.get(SponsoredPlacementRecord, placement_id)
            record = existing or SponsoredPlacementRecord(
                placement_id=placement_id,
                opportunity_id=opportunity_id,
                surface=surface,
                status=placement_status.value,
                label=label,
                disclosure_text=disclosure_text,
                audit_trail_json={},
                created_at=now,
                updated_at=now,
            )
            record.strategy_id = strategy_id
            record.surface = _clean_token(surface, fallback="unknown")
            record.status = placement_status.value
            record.label = label
            record.disclosure_text = disclosure_text
            record.campaign_name = _clean_optional(campaign_name)
            record.sponsor_name = _clean_optional(sponsor_name)
            record.starts_at = _normalize_utc(starts_at) if starts_at else None
            record.ends_at = _normalize_utc(ends_at) if ends_at else None
            record.audit_trail_json = dict(audit_trail or {})
            record.updated_at = now
            if existing is None:
                session.add(record)
            session.commit()
            return _sponsored_placement_from_record(record)

    def active_sponsored_placements(self, *, surface: str, at: datetime | None = None) -> list[SponsoredPlacement]:
        moment = _normalize_utc(at or datetime.now(UTC))
        stmt = (
            select(SponsoredPlacementRecord)
            .where(
                SponsoredPlacementRecord.surface == surface,
                SponsoredPlacementRecord.status == SponsoredPlacementStatus.ACTIVE.value,
                and_(
                    (SponsoredPlacementRecord.starts_at.is_(None) | (SponsoredPlacementRecord.starts_at <= moment)),
                    (SponsoredPlacementRecord.ends_at.is_(None) | (SponsoredPlacementRecord.ends_at > moment)),
                ),
            )
            .order_by(desc(SponsoredPlacementRecord.updated_at), SponsoredPlacementRecord.placement_id)
        )
        with Session(self.engine) as session:
            return [_sponsored_placement_from_record(record) for record in session.scalars(stmt).all()]

    def metrics(
        self,
        *,
        destination_slug: str | None = None,
        impressions: int | None = None,
    ) -> MonetizationMetrics:
        with Session(self.engine) as session:
            click_stmt = select(func.count(OutboundClickEventRecord.event_id))
            session_stmt = select(func.count(func.distinct(OutboundClickEventRecord.coarse_session_id))).where(
                OutboundClickEventRecord.coarse_session_id.is_not(None)
            )
            revenue_stmt = select(RevenueAttributionRecord).where(
                RevenueAttributionRecord.attribution_status == RevenueAttributionStatus.VERIFIED.value
            )
            if destination_slug is not None:
                click_stmt = click_stmt.where(OutboundClickEventRecord.destination_slug == destination_slug)
                session_stmt = session_stmt.where(OutboundClickEventRecord.destination_slug == destination_slug)
                revenue_stmt = revenue_stmt.where(RevenueAttributionRecord.destination_slug == destination_slug)
            outbound_clicks = int(session.scalar(click_stmt) or 0)
            coarse_sessions = int(session.scalar(session_stmt) or 0)
            verified_records = list(session.scalars(revenue_stmt).all())

        total_revenue: Decimal | None = None
        currency: str | None = None
        conversion_count: int | None = None
        for record in verified_records:
            if record.revenue_amount is not None:
                amount = Decimal(record.revenue_amount)
                total_revenue = amount if total_revenue is None else total_revenue + amount
                currency = record.revenue_currency or currency
            if record.verified_conversion_count is not None:
                conversion_count = (
                    record.verified_conversion_count
                    if conversion_count is None
                    else conversion_count + record.verified_conversion_count
                )

        return MonetizationMetrics(
            methodology_version=MONETIZATION_METHODOLOGY_VERSION,
            destination_slug=destination_slug,
            outbound_clicks=outbound_clicks,
            coarse_sessions=(
                MonetizationMetricValue(str(coarse_sessions), "available")
                if coarse_sessions > 0
                else MonetizationMetricValue(
                    None,
                    "unavailable",
                    "Privacy-minimal click tracking does not require session identifiers.",
                )
            ),
            click_through_rate=_ratio_or_unavailable(
                numerator=Decimal(outbound_clicks),
                denominator=Decimal(impressions) if impressions is not None else None,
                missing_reason="CTR requires a verified impression denominator.",
            ),
            verified_conversions=(
                MonetizationMetricValue(str(conversion_count), "available")
                if conversion_count is not None
                else MonetizationMetricValue(None, "unavailable", "No verified conversion import exists.")
            ),
            verified_revenue=(
                MonetizationMetricValue(f"{total_revenue} {currency}".strip(), "available")
                if total_revenue is not None and currency is not None
                else MonetizationMetricValue(None, "unavailable", "No verified revenue import exists.")
            ),
            earnings_per_click=_decimal_metric_or_unavailable(
                numerator=total_revenue,
                denominator=Decimal(outbound_clicks),
                suffix=currency,
                missing_reason="EPC requires verified revenue and outbound clicks.",
            ),
            verified_conversion_rate=_ratio_or_unavailable(
                numerator=Decimal(conversion_count) if conversion_count is not None else None,
                denominator=Decimal(outbound_clicks),
                missing_reason="Conversion rate requires verified conversions and outbound clicks.",
            ),
        )


def _click_from_record(record: OutboundClickEventRecord) -> OutboundClickEvent:
    return OutboundClickEvent(
        event_id=record.event_id,
        destination_slug=record.destination_slug,
        destination_id=record.destination_id,
        opportunity_id=record.opportunity_id,
        opportunity_type=record.opportunity_type,
        game_id=record.game_id,
        strategy_id=record.strategy_id,
        destination_type=record.destination_type,
        referral_status=ReferralLifecycleStatus(record.referral_status),
        commercial_relationship=record.commercial_relationship,
        is_affiliate=record.is_affiliate,
        target_url_kind=record.target_url_kind,
        source_page=record.source_page,
        placement=record.placement,
        coarse_session_id=record.coarse_session_id,
        user_agent_category=record.user_agent_category,
        occurred_at=_normalize_utc(record.occurred_at),
        created_at=_normalize_utc(record.created_at),
    )


def _referral_program_from_record(record: ReferralProgramRecord) -> ReferralProgram:
    return ReferralProgram(
        program_id=record.program_id,
        destination_slug=record.destination_slug,
        opportunity_id=record.opportunity_id,
        strategy_id=record.strategy_id,
        affiliate_program=record.affiliate_program,
        referral_status=ReferralLifecycleStatus(record.referral_status),
        commercial_relationship=record.commercial_relationship,
        disclosure_text=record.disclosure_text,
        verification_status=record.verification_status,
        evidence=MappingProxyType(dict(record.evidence_json)),
        verified_at=_normalize_utc(record.verified_at) if record.verified_at else None,
        last_checked_at=_normalize_utc(record.last_checked_at) if record.last_checked_at else None,
        created_at=_normalize_utc(record.created_at),
        updated_at=_normalize_utc(record.updated_at),
    )


def _revenue_attribution_from_record(record: RevenueAttributionRecord) -> RevenueAttribution:
    return RevenueAttribution(
        attribution_id=record.attribution_id,
        destination_slug=record.destination_slug,
        opportunity_id=record.opportunity_id,
        strategy_id=record.strategy_id,
        attribution_status=RevenueAttributionStatus(record.attribution_status),
        click_period_start=_normalize_utc(record.click_period_start),
        click_period_end=_normalize_utc(record.click_period_end),
        verified_conversion_count=record.verified_conversion_count,
        revenue_amount=Decimal(record.revenue_amount) if record.revenue_amount is not None else None,
        revenue_currency=record.revenue_currency,
        source_program=record.source_program,
        evidence=MappingProxyType(dict(record.evidence_json)),
        imported_at=_normalize_utc(record.imported_at),
        created_at=_normalize_utc(record.created_at),
    )


def _sponsored_placement_from_record(record: SponsoredPlacementRecord) -> SponsoredPlacement:
    return SponsoredPlacement(
        placement_id=record.placement_id,
        opportunity_id=record.opportunity_id,
        strategy_id=record.strategy_id,
        surface=record.surface,
        status=SponsoredPlacementStatus(record.status),
        label=record.label,
        disclosure_text=record.disclosure_text,
        campaign_name=record.campaign_name,
        sponsor_name=record.sponsor_name,
        starts_at=_normalize_utc(record.starts_at) if record.starts_at else None,
        ends_at=_normalize_utc(record.ends_at) if record.ends_at else None,
        audit_trail=MappingProxyType(dict(record.audit_trail_json)),
        created_at=_normalize_utc(record.created_at),
        updated_at=_normalize_utc(record.updated_at),
    )


def _ratio_or_unavailable(
    *,
    numerator: Decimal | None,
    denominator: Decimal | None,
    missing_reason: str,
) -> MonetizationMetricValue:
    if numerator is None or denominator is None or denominator == 0:
        return MonetizationMetricValue(None, "unavailable", missing_reason)
    return MonetizationMetricValue(str(numerator / denominator), "available")


def _decimal_metric_or_unavailable(
    *,
    numerator: Decimal | None,
    denominator: Decimal,
    suffix: str | None,
    missing_reason: str,
) -> MonetizationMetricValue:
    if numerator is None or denominator == 0:
        return MonetizationMetricValue(None, "unavailable", missing_reason)
    value = str(numerator / denominator)
    return MonetizationMetricValue(f"{value} {suffix}".strip(), "available")


def _referral_status(value: ReferralLifecycleStatus | str) -> ReferralLifecycleStatus:
    try:
        return value if isinstance(value, ReferralLifecycleStatus) else ReferralLifecycleStatus(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported referral status: {value}") from exc


def _attribution_status(value: RevenueAttributionStatus | str) -> RevenueAttributionStatus:
    try:
        return value if isinstance(value, RevenueAttributionStatus) else RevenueAttributionStatus(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported attribution status: {value}") from exc


def _placement_status(value: SponsoredPlacementStatus | str) -> SponsoredPlacementStatus:
    try:
        return value if isinstance(value, SponsoredPlacementStatus) else SponsoredPlacementStatus(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported sponsored placement status: {value}") from exc


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()[:128]
    return text or None


def _clean_token(value: str | None, *, fallback: str) -> str:
    text = _clean_optional(value)
    if text is None:
        return fallback
    cleaned = "".join(char for char in text if char.isalnum() or char in ("_", "-", "."))
    return cleaned[:128] or fallback


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
