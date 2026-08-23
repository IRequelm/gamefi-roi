"""Operator referral workflow logic.

This module deliberately works only with catalog metadata and monetization
records. It does not import ROI snapshots, risk/confidence scoring, or ranking
services.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from ipaddress import ip_address
from urllib.parse import quote, urlsplit

from app.monetization.models import (
    REFERRAL_OPERATIONS_VERSION,
    MonetizationMetrics,
    ReferralCoverageState,
    ReferralLifecycleStatus,
    ReferralProgram,
    ReferralTask,
    ReferralTaskType,
    RevenueAttribution,
    RevenueAttributionStatus,
)
from app.storage.monetization import MonetizationPersistenceError, MonetizationRepository
from app.strategies.catalog import (
    OpportunityCatalogEntry,
    OutboundDestination,
    get_outbound_destination,
    list_opportunities,
    primary_destination_for_opportunity,
)


class ReferralValidationError(ValueError):
    """Raised when operator-provided referral metadata is unsafe."""


@dataclass(frozen=True)
class ReferralCoverageRow:
    opportunity: OpportunityCatalogEntry
    destination: OutboundDestination | None
    program: ReferralProgram | None
    coverage_state: ReferralCoverageState
    next_action: str
    priority: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ReferralCoverageSummary:
    total_published_opportunities: int
    referral_active_count: int
    referral_missing_count: int
    referral_pending_count: int
    no_program_found_count: int
    expired_count: int
    reverify_count: int
    referral_coverage_percentage: Decimal


@dataclass(frozen=True)
class ReferralHealthResult:
    rows: tuple[ReferralCoverageRow, ...]
    tasks: tuple[ReferralTask, ...]


class ReferralOperationsService:
    def __init__(
        self,
        repository: MonetizationRepository,
        *,
        reverify_days: int = 30,
        pending_recheck_days: int = 14,
    ) -> None:
        self.repository = repository
        self.reverify_days = reverify_days
        self.pending_recheck_days = pending_recheck_days

    def coverage_rows(
        self,
        *,
        at: datetime | None = None,
        state_filter: ReferralCoverageState | None = None,
        opportunity_type: str | None = None,
    ) -> tuple[ReferralCoverageRow, ...]:
        moment = _normalize_utc(at or datetime.now(UTC))
        programs = {program.destination_slug: program for program in self.repository.referral_programs()}
        rows = []
        for opportunity in published_opportunities():
            if opportunity_type is not None and opportunity.opportunity_type != opportunity_type:
                continue
            destination = primary_destination_for_opportunity(opportunity.opportunity_id)
            program = programs.get(destination.destination_slug) if destination is not None else None
            row = self._coverage_row(opportunity, destination, program, at=moment)
            if state_filter is None or row.coverage_state is state_filter:
                rows.append(row)
        return tuple(sorted(rows, key=lambda row: (row.priority, row.opportunity.name)))

    def coverage_summary(self, *, at: datetime | None = None) -> ReferralCoverageSummary:
        rows = self.coverage_rows(at=at)
        total = len(rows)
        active = sum(row.coverage_state is ReferralCoverageState.REFERRAL_ACTIVE for row in rows)
        missing = sum(row.coverage_state is ReferralCoverageState.REFERRAL_MISSING for row in rows)
        pending = sum(row.coverage_state is ReferralCoverageState.REFERRAL_PENDING for row in rows)
        no_program = sum(row.coverage_state is ReferralCoverageState.NO_PROGRAM_FOUND for row in rows)
        expired = sum(row.coverage_state is ReferralCoverageState.REFERRAL_EXPIRED for row in rows)
        reverify = sum(row.coverage_state is ReferralCoverageState.REFERRAL_REVERIFY for row in rows)
        percentage = Decimal(0) if total == 0 else (Decimal(active) / Decimal(total) * Decimal(100))
        return ReferralCoverageSummary(
            total_published_opportunities=total,
            referral_active_count=active,
            referral_missing_count=missing,
            referral_pending_count=pending,
            no_program_found_count=no_program,
            expired_count=expired,
            reverify_count=reverify,
            referral_coverage_percentage=percentage,
        )

    def run_health_check(self, *, at: datetime | None = None) -> ReferralHealthResult:
        moment = _normalize_utc(at or datetime.now(UTC))
        tasks: list[ReferralTask] = []
        rows = self.coverage_rows(at=moment)
        for row in rows:
            task = self._task_for_row(row, at=moment)
            if task is not None:
                tasks.append(task)
            if row.coverage_state is ReferralCoverageState.REFERRAL_ACTIVE:
                self._resolve_gap_tasks(row.opportunity.opportunity_id)
        return ReferralHealthResult(rows=rows, tasks=tuple(tasks))

    def save_program(
        self,
        *,
        destination_slug: str,
        referral_status: ReferralLifecycleStatus | str,
        official_url: str | None = None,
        referral_url: str | None = None,
        referral_code: str | None = None,
        referral_url_template: str | None = None,
        affiliate_program: str | None = None,
        program_type: str | None = None,
        commission_description: str | None = None,
        eligibility_notes: str | None = None,
        geographic_restrictions: str | None = None,
        evidence_url: str | None = None,
        evidence_reference: str | None = None,
        applied_at: datetime | None = None,
        verified_at: datetime | None = None,
        last_checked_at: datetime | None = None,
        expires_at: datetime | None = None,
        operator_notes: str | None = None,
    ) -> ReferralProgram:
        destination = get_outbound_destination(destination_slug)
        if destination is None:
            raise ReferralValidationError(f"Unknown outbound destination: {destination_slug}")

        status = _referral_status(referral_status)
        clean_official_url = official_url or destination.official_url
        validate_destination_url(clean_official_url, expected_url=destination.official_url, label="official_url")
        assembled_referral_url = assemble_referral_url(
            referral_url=referral_url,
            referral_code=referral_code,
            referral_url_template=referral_url_template,
        )
        if assembled_referral_url:
            validate_destination_url(
                assembled_referral_url,
                expected_url=clean_official_url,
                label="referral_url",
            )
        if status is ReferralLifecycleStatus.ACTIVE and not assembled_referral_url:
            raise ReferralValidationError("ACTIVE referral status requires a validated referral URL or template+code")
        if status in {ReferralLifecycleStatus.ACTIVE, ReferralLifecycleStatus.VERIFIED} and not (evidence_url or evidence_reference):
            raise ReferralValidationError("Active or verified referral programs require evidence/source reference")

        program = self.repository.save_referral_program(
            destination_slug=destination.destination_slug,
            opportunity_id=destination.opportunity_id,
            strategy_id=destination.strategy_id,
            affiliate_program=affiliate_program,
            referral_status=status,
            commercial_relationship="affiliate" if status is ReferralLifecycleStatus.ACTIVE else "none",
            disclosure_text=_disclosure_for(status, affiliate_program),
            verification_status="verified" if status is ReferralLifecycleStatus.ACTIVE else "operator_review",
            official_url=clean_official_url,
            referral_url=assembled_referral_url,
            referral_code=referral_code,
            referral_url_template=referral_url_template,
            program_type=program_type,
            commission_description=commission_description,
            eligibility_notes=eligibility_notes,
            geographic_restrictions=geographic_restrictions,
            evidence_url=evidence_url,
            evidence={"source": evidence_reference} if evidence_reference else {},
            applied_at=applied_at,
            verified_at=verified_at,
            last_checked_at=last_checked_at,
            expires_at=expires_at,
            operator_notes=operator_notes,
        )
        self.run_health_check()
        return program

    def save_revenue_attribution(
        self,
        *,
        destination_slug: str,
        click_period_start: datetime,
        click_period_end: datetime,
        verified_conversion_count: int | None,
        revenue_amount: Decimal | str | None,
        revenue_currency: str | None,
        settlement_reference_id: str | None,
        evidence_reference: str | None,
        notes: str | None = None,
        attribution_status: RevenueAttributionStatus | str = RevenueAttributionStatus.PENDING,
    ) -> RevenueAttribution:
        destination = get_outbound_destination(destination_slug)
        if destination is None:
            raise MonetizationPersistenceError(f"Unknown outbound destination: {destination_slug}")
        status = _attribution_status(attribution_status)
        if status is RevenueAttributionStatus.VERIFIED and not (settlement_reference_id or evidence_reference):
            raise MonetizationPersistenceError("Verified revenue requires settlement/reference or evidence")
        return self.repository.save_revenue_attribution(
            destination_slug=destination.destination_slug,
            opportunity_id=destination.opportunity_id,
            strategy_id=destination.strategy_id,
            click_period_start=click_period_start,
            click_period_end=click_period_end,
            attribution_status=status,
            verified_conversion_count=verified_conversion_count,
            revenue_amount=revenue_amount,
            revenue_currency=revenue_currency,
            source_program=evidence_reference,
            settlement_reference_id=settlement_reference_id,
            notes=notes,
            evidence={"operator_source": evidence_reference} if evidence_reference else {},
        )

    def metrics(self, *, destination_slug: str | None = None, impressions: int | None = None) -> MonetizationMetrics:
        return self.repository.metrics(destination_slug=destination_slug, impressions=impressions)

    def _coverage_row(
        self,
        opportunity: OpportunityCatalogEntry,
        destination: OutboundDestination | None,
        program: ReferralProgram | None,
        *,
        at: datetime,
    ) -> ReferralCoverageRow:
        if destination is None:
            return ReferralCoverageRow(
                opportunity=opportunity,
                destination=None,
                program=None,
                coverage_state=ReferralCoverageState.REFERRAL_MISSING,
                next_action="Add an official destination before referral research.",
                priority=10,
                warnings=("No outbound destination exists.",),
            )
        if program is None:
            return ReferralCoverageRow(
                opportunity=opportunity,
                destination=destination,
                program=None,
                coverage_state=ReferralCoverageState.REFERRAL_MISSING,
                next_action="Research whether a referral or affiliate program exists.",
                priority=20,
                warnings=("No explicit referral program record exists.",),
            )

        warnings: list[str] = []
        status = program.referral_status
        if program.expires_at and program.expires_at <= at:
            status = ReferralLifecycleStatus.EXPIRED
            warnings.append("Stored referral expiration has passed.")
        if status is ReferralLifecycleStatus.ACTIVE and _verification_is_old(program, at=at, days=self.reverify_days):
            warnings.append("Active referral verification is older than the configured threshold.")
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_REVERIFY, "Reverify the program and referral link.", 30, tuple(warnings))
        if status is ReferralLifecycleStatus.ACTIVE:
            if not program.referral_url:
                warnings.append("Active status is missing a referral URL.")
                return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_REVERIFY, "Add or validate the referral URL.", 25, tuple(warnings))
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_ACTIVE, "Monitor during routine weekly review.", 90, tuple(warnings))
        if status is ReferralLifecycleStatus.PENDING:
            if _pending_is_old(program, at=at, days=self.pending_recheck_days):
                warnings.append("Pending application is older than the configured recheck threshold.")
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_PENDING, "Recheck pending affiliate application.", 40, tuple(warnings))
        if status is ReferralLifecycleStatus.VERIFIED:
            if not program.referral_url:
                warnings.append("Verified program is missing a referral URL.")
            return ReferralCoverageRow(
                opportunity,
                destination,
                program,
                ReferralCoverageState.REFERRAL_REVERIFY,
                "Verify the referral link and activate it when safe.",
                30,
                tuple(warnings),
            )
        if status is ReferralLifecycleStatus.EXPIRED:
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_EXPIRED, "Replace or pause the expired referral link.", 10, tuple(warnings))
        if status is ReferralLifecycleStatus.PAUSED:
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_PAUSED, "Review why the referral is paused.", 35, tuple(warnings))
        if status is ReferralLifecycleStatus.NO_PROGRAM_FOUND:
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.NO_PROGRAM_FOUND, "Recheck periodically for a new program.", 80, tuple(warnings))
        if status in {ReferralLifecycleStatus.RESEARCH_REQUIRED, ReferralLifecycleStatus.DISCOVERED, ReferralLifecycleStatus.APPLICATION_REQUIRED}:
            action = "Apply to the referral program." if status is ReferralLifecycleStatus.APPLICATION_REQUIRED else "Research referral availability."
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_RESEARCH_REQUIRED, action, 45, tuple(warnings))
        if status is ReferralLifecycleStatus.REVERIFY:
            return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_REVERIFY, "Reverify program evidence and link.", 30, tuple(warnings))
        return ReferralCoverageRow(opportunity, destination, program, ReferralCoverageState.REFERRAL_MISSING, "Research whether a referral or affiliate program exists.", 20, tuple(warnings))

    def _task_for_row(self, row: ReferralCoverageRow, *, at: datetime) -> ReferralTask | None:
        destination_slug = row.destination.destination_slug if row.destination else None
        if row.coverage_state is ReferralCoverageState.REFERRAL_MISSING:
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.FIND_REFERRAL_PROGRAM,
                reason=row.next_action,
            )
        if row.program and row.program.referral_status is ReferralLifecycleStatus.APPLICATION_REQUIRED:
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.APPLY_TO_PROGRAM,
                reason=row.next_action,
            )
        if row.coverage_state is ReferralCoverageState.REFERRAL_PENDING:
            due = (row.program.applied_at or row.program.last_checked_at or row.program.created_at) + timedelta(days=self.pending_recheck_days) if row.program else at
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.RECHECK_PENDING_APPLICATION,
                reason=row.next_action,
                due_at=due,
            )
        if row.program and row.program.referral_status is ReferralLifecycleStatus.VERIFIED:
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.VERIFY_REFERRAL_LINK,
                reason=row.next_action,
            )
        if row.coverage_state is ReferralCoverageState.REFERRAL_REVERIFY:
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.REVERIFY_PROGRAM,
                reason=row.next_action,
            )
        if row.coverage_state is ReferralCoverageState.REFERRAL_EXPIRED:
            return self.repository.upsert_referral_task(
                opportunity_id=row.opportunity.opportunity_id,
                destination_slug=destination_slug,
                task_type=ReferralTaskType.REPLACE_EXPIRED_LINK,
                reason=row.next_action,
            )
        return None

    def _resolve_gap_tasks(self, opportunity_id: str) -> None:
        for task_type in (
            ReferralTaskType.FIND_REFERRAL_PROGRAM,
            ReferralTaskType.APPLY_TO_PROGRAM,
            ReferralTaskType.RECHECK_PENDING_APPLICATION,
            ReferralTaskType.VERIFY_REFERRAL_LINK,
            ReferralTaskType.REVERIFY_PROGRAM,
            ReferralTaskType.REPLACE_EXPIRED_LINK,
        ):
            self.repository.resolve_referral_task(opportunity_id=opportunity_id, task_type=task_type)


def published_opportunities() -> tuple[OpportunityCatalogEntry, ...]:
    return tuple(opportunity for opportunity in list_opportunities() if opportunity.status in {"active", "candidate"})


def program_for_destination(repository: MonetizationRepository, destination_slug: str) -> ReferralProgram | None:
    return repository.get_referral_program(destination_slug)


def destination_with_operator_referral(
    destination: OutboundDestination,
    program: ReferralProgram | None,
    *,
    at: datetime | None = None,
) -> OutboundDestination:
    moment = _normalize_utc(at or datetime.now(UTC))
    if program is None:
        return destination
    official_url = program.official_url or destination.official_url
    validate_destination_url(official_url, expected_url=destination.official_url, label="official_url")
    referral_url = program.referral_url
    if (
        program.referral_status is ReferralLifecycleStatus.ACTIVE
        and referral_url
        and (program.expires_at is None or program.expires_at > moment)
    ):
        validate_destination_url(referral_url, expected_url=official_url, label="referral_url")
        return replace(
            destination,
            official_url=official_url,
            referral_url=referral_url,
            referral_code=program.referral_code,
            affiliate_program=program.affiliate_program,
            is_affiliate=True,
            commercial_relationship="affiliate",
            disclosure_text=program.disclosure_text,
            referral_status=ReferralLifecycleStatus.ACTIVE.value,
            expires_at=program.expires_at,
        )
    return replace(destination, official_url=official_url, referral_url=None, referral_status=program.referral_status.value)


def assemble_referral_url(
    *,
    referral_url: str | None,
    referral_code: str | None,
    referral_url_template: str | None,
) -> str | None:
    if referral_url:
        return referral_url.strip()
    if referral_code and referral_url_template:
        if "{code}" not in referral_url_template:
            raise ReferralValidationError("Referral URL template must contain {code}")
        return referral_url_template.replace("{code}", quote(referral_code.strip(), safe=""))
    return None


def validate_destination_url(value: str, *, expected_url: str, label: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ReferralValidationError(f"{label} must use https")
    if not parsed.netloc or not parsed.hostname:
        raise ReferralValidationError(f"{label} must include a valid host")
    if parsed.scheme in {"javascript", "data"}:
        raise ReferralValidationError(f"{label} cannot use unsafe URL schemes")
    host = parsed.hostname.lower()
    if _is_private_or_local_host(host):
        raise ReferralValidationError(f"{label} cannot point to localhost or private-network destinations")
    expected = urlsplit(expected_url)
    if not expected.hostname or _domain_root(host) != _domain_root(expected.hostname.lower()):
        raise ReferralValidationError(f"{label} host must match the reviewed official-domain relationship")


def _is_private_or_local_host(host: str) -> bool:
    if host in {"localhost", "0.0.0.0"} or host.endswith(".local"):
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local or address.is_reserved


def _domain_root(host: str) -> str:
    parts = host.strip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _verification_is_old(program: ReferralProgram, *, at: datetime, days: int) -> bool:
    checked = program.last_checked_at or program.verified_at
    if checked is None:
        return True
    return checked + timedelta(days=days) <= at


def _pending_is_old(program: ReferralProgram, *, at: datetime, days: int) -> bool:
    checked = program.last_checked_at or program.applied_at or program.created_at
    return checked + timedelta(days=days) <= at


def _disclosure_for(status: ReferralLifecycleStatus, affiliate_program: str | None) -> str:
    if status is ReferralLifecycleStatus.ACTIVE:
        name = affiliate_program or "configured referral program"
        return f"Referral/affiliate link via {name}. Commercial relationship does not affect ROI, Risk, Confidence, or organic rankings."
    return "Official outbound link fallback remains active. Referral work is tracked in the operator console."


def _referral_status(value: ReferralLifecycleStatus | str) -> ReferralLifecycleStatus:
    try:
        return value if isinstance(value, ReferralLifecycleStatus) else ReferralLifecycleStatus(str(value))
    except ValueError as exc:
        raise ReferralValidationError(f"Unsupported referral status: {value}") from exc


def _attribution_status(value: RevenueAttributionStatus | str) -> RevenueAttributionStatus:
    try:
        return value if isinstance(value, RevenueAttributionStatus) else RevenueAttributionStatus(str(value))
    except ValueError as exc:
        raise MonetizationPersistenceError(f"Unsupported attribution status: {value}") from exc


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
