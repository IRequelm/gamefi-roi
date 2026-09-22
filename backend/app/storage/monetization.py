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
    ContentPerformancePlatform,
    ContentPerformanceRecord,
    InboundLandingEvent,
    MONETIZATION_METHODOLOGY_VERSION,
    MonetizationMetrics,
    MonetizationMetricValue,
    OutboundClickEvent,
    ReferralLifecycleStatus,
    ReferralProgram,
    ReferralTask,
    ReferralTaskStatus,
    ReferralTaskType,
    RevenueAttribution,
    RevenueAttributionStatus,
    SponsoredPlacement,
    SponsoredPlacementStatus,
)
from app.storage.models.monetization import (
    ContentPerformanceRecordModel,
    InboundLandingEventRecord,
    OutboundClickEventRecord,
    ReferralProgramRecord,
    ReferralTaskRecord,
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

    def record_landing_visit(
        self,
        *,
        landing_path: str,
        referrer_domain: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        channel: str | None = None,
        coarse_session_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> InboundLandingEvent:
        event_time = _normalize_utc(occurred_at or datetime.now(UTC))
        detected_channel = _clean_token(channel, fallback="other") if channel else normalize_acquisition_channel(
            utm_source=utm_source,
            referrer_domain=referrer_domain,
        )
        record = InboundLandingEventRecord(
            event_id=str(uuid4()),
            landing_path=_clean_path(landing_path),
            referrer_domain=_clean_domain(referrer_domain),
            utm_source=_clean_optional(utm_source),
            utm_medium=_clean_optional(utm_medium),
            utm_campaign=_clean_optional(utm_campaign),
            channel=detected_channel,
            coarse_session_id=_clean_optional(coarse_session_id),
            occurred_at=event_time,
            created_at=datetime.now(UTC),
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(record)
            session.commit()
            return _landing_from_record(record)

    def landing_visits(self, *, landing_path: str | None = None) -> list[InboundLandingEvent]:
        stmt = select(InboundLandingEventRecord).order_by(InboundLandingEventRecord.occurred_at)
        if landing_path is not None:
            stmt = stmt.where(InboundLandingEventRecord.landing_path == landing_path)
        with Session(self.engine) as session:
            return [_landing_from_record(record) for record in session.scalars(stmt).all()]

    def save_content_performance(
        self,
        *,
        platform: ContentPerformancePlatform | str,
        content_id: str,
        period_start: datetime,
        period_end: datetime,
        impressions: int | None = None,
        views: int | None = None,
        engagements: int | None = None,
        link_clicks: int | None = None,
        profile_visits: int | None = None,
        followers_gained: int | None = None,
        subscribers_gained: int | None = None,
        average_retention_percent: Decimal | str | None = None,
        evidence_url: str | None = None,
        evidence_reference: str | None = None,
        notes: str | None = None,
        imported_at: datetime | None = None,
    ) -> ContentPerformanceRecord:
        selected_platform = _performance_platform(platform)
        clean_content_id = _clean_optional(content_id, limit=255)
        if clean_content_id is None:
            raise MonetizationPersistenceError("content_id is required")
        start = _normalize_utc(period_start)
        end = _normalize_utc(period_end)
        if end < start:
            raise MonetizationPersistenceError("period_end must be greater than or equal to period_start")
        counts = {
            "impressions": impressions,
            "views": views,
            "engagements": engagements,
            "link_clicks": link_clicks,
            "profile_visits": profile_visits,
            "followers_gained": followers_gained,
            "subscribers_gained": subscribers_gained,
        }
        if not any(value is not None for value in counts.values()) and average_retention_percent is None:
            raise MonetizationPersistenceError("At least one platform metric is required")
        for name, value in counts.items():
            if value is not None and (not isinstance(value, int) or value < 0):
                raise MonetizationPersistenceError(f"{name} must be a non-negative integer")
        retention = Decimal(str(average_retention_percent)) if average_retention_percent is not None else None
        if retention is not None and (retention < 0 or retention > 100):
            raise MonetizationPersistenceError("average_retention_percent must be between 0 and 100")
        clean_evidence_url = _clean_url_text(evidence_url)
        if clean_evidence_url is not None and not clean_evidence_url.lower().startswith("https://"):
            raise MonetizationPersistenceError("evidence_url must use https")
        clean_evidence_reference = _clean_optional(evidence_reference, limit=2048)
        if clean_evidence_url is None and clean_evidence_reference is None:
            raise MonetizationPersistenceError("Content performance requires an evidence URL or reference")
        performance_id = str(
            uuid5(
                NAMESPACE_URL,
                "gamefi-roi-content-performance|{}|{}|{}|{}".format(
                    selected_platform.value,
                    clean_content_id,
                    start.isoformat(),
                    end.isoformat(),
                ),
            )
        )
        now = datetime.now(UTC)
        with Session(self.engine, expire_on_commit=False) as session:
            record = session.get(ContentPerformanceRecordModel, performance_id)
            if record is None:
                record = ContentPerformanceRecordModel(
                    performance_id=performance_id,
                    platform=selected_platform.value,
                    content_id=clean_content_id,
                    period_start=start,
                    period_end=end,
                    created_at=now,
                )
                session.add(record)
            record.platform = selected_platform.value
            record.content_id = clean_content_id
            record.period_start = start
            record.period_end = end
            record.impressions = impressions
            record.views = views
            record.engagements = engagements
            record.link_clicks = link_clicks
            record.profile_visits = profile_visits
            record.followers_gained = followers_gained
            record.subscribers_gained = subscribers_gained
            record.average_retention_percent = str(retention) if retention is not None else None
            record.evidence_url = clean_evidence_url
            record.evidence_reference = clean_evidence_reference
            record.notes = _clean_optional(notes, limit=4096)
            record.imported_at = _normalize_utc(imported_at or now)
            session.commit()
            return _content_performance_from_record(record)

    def content_performance(
        self,
        *,
        platform: ContentPerformancePlatform | str | None = None,
        content_id: str | None = None,
    ) -> list[ContentPerformanceRecord]:
        stmt = select(ContentPerformanceRecordModel).order_by(
            ContentPerformanceRecordModel.period_start,
            ContentPerformanceRecordModel.platform,
            ContentPerformanceRecordModel.content_id,
        )
        if platform is not None:
            stmt = stmt.where(ContentPerformanceRecordModel.platform == _performance_platform(platform).value)
        if content_id is not None:
            stmt = stmt.where(ContentPerformanceRecordModel.content_id == _clean_optional(content_id, limit=255))
        with Session(self.engine) as session:
            return [_content_performance_from_record(record) for record in session.scalars(stmt).all()]

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
        official_url: str | None = None,
        referral_url: str | None = None,
        referral_code: str | None = None,
        referral_url_template: str | None = None,
        program_type: str | None = None,
        commission_description: str | None = None,
        eligibility_notes: str | None = None,
        geographic_restrictions: str | None = None,
        evidence_url: str | None = None,
        evidence: dict[str, Any] | None = None,
        applied_at: datetime | None = None,
        verified_at: datetime | None = None,
        last_checked_at: datetime | None = None,
        expires_at: datetime | None = None,
        operator_notes: str | None = None,
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
            record.official_url = _clean_url_text(official_url)
            record.referral_url = _clean_url_text(referral_url)
            record.referral_code = _clean_optional(referral_code, limit=255)
            record.referral_url_template = _clean_url_text(referral_url_template)
            record.program_type = _clean_optional(program_type)
            record.commission_description = _clean_optional(commission_description, limit=2048)
            record.eligibility_notes = _clean_optional(eligibility_notes, limit=2048)
            record.geographic_restrictions = _clean_optional(geographic_restrictions, limit=1024)
            record.evidence_url = _clean_url_text(evidence_url)
            record.evidence_json = dict(evidence or {})
            record.applied_at = _normalize_utc(applied_at) if applied_at else None
            record.verified_at = _normalize_utc(verified_at) if verified_at else None
            record.last_checked_at = _normalize_utc(last_checked_at) if last_checked_at else None
            record.expires_at = _normalize_utc(expires_at) if expires_at else None
            record.operator_notes = _clean_optional(operator_notes, limit=4096)
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

    def referral_programs(self) -> list[ReferralProgram]:
        stmt = select(ReferralProgramRecord).order_by(ReferralProgramRecord.destination_slug)
        with Session(self.engine) as session:
            return [_referral_program_from_record(record) for record in session.scalars(stmt).all()]

    def upsert_referral_task(
        self,
        *,
        opportunity_id: str,
        task_type: ReferralTaskType | str,
        reason: str,
        destination_slug: str | None = None,
        due_at: datetime | None = None,
        notes: str | None = None,
    ) -> ReferralTask:
        task_kind = _task_type(task_type)
        now = datetime.now(UTC)
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(ReferralTaskRecord)
                .where(
                    ReferralTaskRecord.opportunity_id == opportunity_id,
                    ReferralTaskRecord.task_type == task_kind.value,
                    ReferralTaskRecord.status == ReferralTaskStatus.OPEN.value,
                )
                .order_by(ReferralTaskRecord.created_at)
            )
            record = existing or ReferralTaskRecord(
                task_id=str(uuid5(NAMESPACE_URL, f"gamefi-roi-referral-task|{opportunity_id}|{task_kind.value}")),
                opportunity_id=opportunity_id,
                task_type=task_kind.value,
                status=ReferralTaskStatus.OPEN.value,
                created_at=now,
                updated_at=now,
                reason="",
            )
            record.destination_slug = _clean_optional(destination_slug, limit=255)
            record.reason = reason[:2048]
            record.due_at = _normalize_utc(due_at) if due_at else None
            record.notes = _clean_optional(notes, limit=4096)
            record.updated_at = now
            if existing is None:
                session.add(record)
            session.commit()
            return _referral_task_from_record(record)

    def resolve_referral_task(
        self,
        *,
        opportunity_id: str,
        task_type: ReferralTaskType | str,
        status: ReferralTaskStatus | str = ReferralTaskStatus.RESOLVED,
    ) -> None:
        task_kind = _task_type(task_type)
        task_status = _task_status(status)
        now = datetime.now(UTC)
        with Session(self.engine) as session:
            records = session.scalars(
                select(ReferralTaskRecord).where(
                    ReferralTaskRecord.opportunity_id == opportunity_id,
                    ReferralTaskRecord.task_type == task_kind.value,
                    ReferralTaskRecord.status == ReferralTaskStatus.OPEN.value,
                )
            ).all()
            for record in records:
                record.status = task_status.value
                record.updated_at = now
                record.resolved_at = now
            session.commit()

    def referral_tasks(
        self,
        *,
        status: ReferralTaskStatus | str | None = None,
        opportunity_id: str | None = None,
    ) -> list[ReferralTask]:
        stmt = select(ReferralTaskRecord).order_by(
            ReferralTaskRecord.status,
            ReferralTaskRecord.due_at,
            ReferralTaskRecord.created_at,
            ReferralTaskRecord.task_id,
        )
        if status is not None:
            stmt = stmt.where(ReferralTaskRecord.status == _task_status(status).value)
        if opportunity_id is not None:
            stmt = stmt.where(ReferralTaskRecord.opportunity_id == opportunity_id)
        with Session(self.engine) as session:
            return [_referral_task_from_record(record) for record in session.scalars(stmt).all()]

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
        settlement_reference_id: str | None = None,
        notes: str | None = None,
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
            settlement_reference_id=_clean_optional(settlement_reference_id, limit=255),
            notes=_clean_optional(notes, limit=4096),
            evidence_json=dict(evidence or {}),
            imported_at=_normalize_utc(imported_at or datetime.now(UTC)),
            created_at=datetime.now(UTC),
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(record)
            session.commit()
            return _revenue_attribution_from_record(record)

    def revenue_attributions(
        self,
        *,
        destination_slug: str | None = None,
        attribution_status: RevenueAttributionStatus | str | None = None,
    ) -> list[RevenueAttribution]:
        stmt = select(RevenueAttributionRecord).order_by(RevenueAttributionRecord.imported_at)
        if destination_slug is not None:
            stmt = stmt.where(RevenueAttributionRecord.destination_slug == destination_slug)
        if attribution_status is not None:
            stmt = stmt.where(RevenueAttributionRecord.attribution_status == _attribution_status(attribution_status).value)
        with Session(self.engine) as session:
            return [_revenue_attribution_from_record(record) for record in session.scalars(stmt).all()]

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


def _landing_from_record(record: InboundLandingEventRecord) -> InboundLandingEvent:
    return InboundLandingEvent(
        event_id=record.event_id,
        landing_path=record.landing_path,
        referrer_domain=record.referrer_domain,
        utm_source=record.utm_source,
        utm_medium=record.utm_medium,
        utm_campaign=record.utm_campaign,
        channel=record.channel,
        coarse_session_id=record.coarse_session_id,
        occurred_at=_normalize_utc(record.occurred_at),
        created_at=_normalize_utc(record.created_at),
    )


def _content_performance_from_record(record: ContentPerformanceRecordModel) -> ContentPerformanceRecord:
    return ContentPerformanceRecord(
        performance_id=record.performance_id,
        platform=ContentPerformancePlatform(record.platform),
        content_id=record.content_id,
        period_start=_normalize_utc(record.period_start),
        period_end=_normalize_utc(record.period_end),
        impressions=record.impressions,
        views=record.views,
        engagements=record.engagements,
        link_clicks=record.link_clicks,
        profile_visits=record.profile_visits,
        followers_gained=record.followers_gained,
        subscribers_gained=record.subscribers_gained,
        average_retention_percent=(Decimal(record.average_retention_percent) if record.average_retention_percent is not None else None),
        evidence_url=record.evidence_url,
        evidence_reference=record.evidence_reference,
        notes=record.notes,
        imported_at=_normalize_utc(record.imported_at),
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
        official_url=record.official_url,
        referral_url=record.referral_url,
        referral_code=record.referral_code,
        referral_url_template=record.referral_url_template,
        program_type=record.program_type,
        commission_description=record.commission_description,
        eligibility_notes=record.eligibility_notes,
        geographic_restrictions=record.geographic_restrictions,
        evidence_url=record.evidence_url,
        evidence=MappingProxyType(dict(record.evidence_json)),
        applied_at=_normalize_utc(record.applied_at) if record.applied_at else None,
        verified_at=_normalize_utc(record.verified_at) if record.verified_at else None,
        last_checked_at=_normalize_utc(record.last_checked_at) if record.last_checked_at else None,
        expires_at=_normalize_utc(record.expires_at) if record.expires_at else None,
        operator_notes=record.operator_notes,
        created_at=_normalize_utc(record.created_at),
        updated_at=_normalize_utc(record.updated_at),
    )


def _referral_task_from_record(record: ReferralTaskRecord) -> ReferralTask:
    return ReferralTask(
        task_id=record.task_id,
        opportunity_id=record.opportunity_id,
        destination_slug=record.destination_slug,
        task_type=ReferralTaskType(record.task_type),
        reason=record.reason,
        status=ReferralTaskStatus(record.status),
        due_at=_normalize_utc(record.due_at) if record.due_at else None,
        notes=record.notes,
        created_at=_normalize_utc(record.created_at),
        updated_at=_normalize_utc(record.updated_at),
        resolved_at=_normalize_utc(record.resolved_at) if record.resolved_at else None,
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
        settlement_reference_id=record.settlement_reference_id,
        notes=record.notes,
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


def _performance_platform(value: ContentPerformancePlatform | str) -> ContentPerformancePlatform:
    try:
        return value if isinstance(value, ContentPerformancePlatform) else ContentPerformancePlatform(str(value).upper())
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported content performance platform: {value}") from exc


def _task_type(value: ReferralTaskType | str) -> ReferralTaskType:
    try:
        return value if isinstance(value, ReferralTaskType) else ReferralTaskType(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported referral task type: {value}") from exc


def _task_status(value: ReferralTaskStatus | str) -> ReferralTaskStatus:
    try:
        return value if isinstance(value, ReferralTaskStatus) else ReferralTaskStatus(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported referral task status: {value}") from exc


def _clean_optional(value: str | None, *, limit: int = 128) -> str | None:
    if value is None:
        return None
    text = str(value).strip()[:limit]
    return text or None


def _clean_url_text(value: str | None) -> str | None:
    return _clean_optional(value, limit=2048)


def _clean_token(value: str | None, *, fallback: str) -> str:
    text = _clean_optional(value)
    if text is None:
        return fallback
    cleaned = "".join(char for char in text if char.isalnum() or char in ("_", "-", "."))
    return cleaned[:128] or fallback


def _clean_path(value: str) -> str:
    text = str(value).strip()
    if not text.startswith("/"):
        text = f"/{text}"
    return text.split("?", 1)[0].split("#", 1)[0][:512]


def _clean_domain(value: str | None) -> str | None:
    text = _clean_optional(value)
    if text is None:
        return None
    lowered = text.lower().strip(".")
    cleaned = "".join(char for char in lowered if char.isalnum() or char in ("-", "."))
    return cleaned[:255] or None


def normalize_acquisition_channel(*, utm_source: str | None, referrer_domain: str | None) -> str:
    source = (utm_source or "").strip().lower()
    domain = (referrer_domain or "").strip().lower()
    evidence = source or domain
    if not evidence:
        return "direct"
    if "chatgpt.com" in evidence or source in {"chatgpt", "openai"}:
        return "chatgpt"
    if "perplexity" in evidence:
        return "perplexity"
    if "google" in evidence:
        return "google"
    if "bing" in evidence or "microsoft" in evidence:
        return "bing"
    if source in {"x", "twitter"} or "x.com" in domain or "twitter.com" in domain:
        return "x"
    if "reddit" in evidence:
        return "reddit"
    if source:
        return "other"
    return "referral"


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
