"""Protected operator console for referral operations."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import Engine

from app.api.dependencies import get_database_engine
from app.config.settings import Settings, get_settings
from app.monetization.models import ReferralCoverageState, ReferralLifecycleStatus, RevenueAttributionStatus
from app.monetization.referral_operations import (
    ReferralOperationsService,
    ReferralValidationError,
)
from app.storage.monetization import MonetizationPersistenceError, MonetizationRepository
from app.strategies.catalog import get_opportunity, primary_destination_for_opportunity

router = APIRouter(prefix="/operator", include_in_schema=False)
security = HTTPBasic(auto_error=False)

NOINDEX_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}


def require_operator(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    if not settings.operator_username or not settings.operator_password:
        raise HTTPException(
            status_code=503,
            detail="Operator console credentials are not configured.",
            headers=NOINDEX_HEADERS,
        )
    if credentials is None:
        raise HTTPException(status_code=401, detail="Operator authentication required.", headers=_auth_headers())
    username_ok = secrets.compare_digest(credentials.username, settings.operator_username)
    password_ok = secrets.compare_digest(credentials.password, settings.operator_password)
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid operator credentials.", headers=_auth_headers())
    return credentials.username


@router.get("")
@router.get("/")
@router.get("/referrals")
def referral_dashboard(
    request: Request,
    _operator: str = Depends(require_operator),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    service = _service(engine, settings)
    state_filter = _state_filter(request.query_params.get("state"))
    opportunity_type = request.query_params.get("opportunity_type") or None
    rows = service.coverage_rows(state_filter=state_filter, opportunity_type=opportunity_type)
    summary = service.coverage_summary()
    tasks = MonetizationRepository(engine).referral_tasks(status="OPEN")
    body = f"""
      <section class="page-head operator-head">
        <p class="eyebrow">Operator Console</p>
        <h1>Referral Operations</h1>
        <p class="lede">Manage commercial metadata without changing ROI, Risk, Confidence, snapshots, or organic rankings.</p>
      </section>
      {_summary_cards(summary)}
      <section class="section-panel">
        <div class="section-header"><h2>Referral Work Queue</h2><span class="badge info">{len(rows)} visible</span></div>
        <div class="section-body button-row">{_filter_links()}</div>
        <div class="operator-table-wrap">
          <table class="operator-table">
            <thead><tr><th>Opportunity</th><th>Type</th><th>Status</th><th>Official</th><th>Program</th><th>Last checked</th><th>Next action</th><th>Priority</th><th>Edit</th></tr></thead>
            <tbody>{''.join(_queue_row(row) for row in rows)}</tbody>
          </table>
        </div>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Open Tasks</h2><span class="badge warning">{len(tasks)} open</span></div>
        <div class="section-body contributor-list">{''.join(_task_card(task) for task in tasks) or '<p class="muted">No open referral tasks.</p>'}</div>
        <form method="post" action="/operator/referrals/health"><button class="button" type="submit">Run referral health check</button></form>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Revenue Entry</h2></div>
        <div class="section-body"><a class="secondary-button" href="/operator/revenue">Enter verified partner results</a></div>
      </section>
    """
    return _operator_response("Referral Operations | GamCryp", body)


@router.post("/referrals/health")
def run_referral_health(
    _operator: str = Depends(require_operator),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> RedirectResponse:
    _service(engine, settings).run_health_check()
    return RedirectResponse("/operator/referrals", status_code=303, headers=NOINDEX_HEADERS)


@router.get("/referrals/{opportunity_id}")
def referral_editor(
    opportunity_id: str,
    _operator: str = Depends(require_operator),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    return _render_editor(opportunity_id, settings=settings, engine=engine)


@router.post("/referrals/{opportunity_id}")
async def save_referral(
    opportunity_id: str,
    request: Request,
    _operator: str = Depends(require_operator),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> Response:
    form = await _form(request)
    destination = primary_destination_for_opportunity(opportunity_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="No editable destination for opportunity.", headers=NOINDEX_HEADERS)
    try:
        _service(engine, settings).save_program(
            destination_slug=destination.destination_slug,
            referral_status=form.get("referral_status", ReferralLifecycleStatus.RESEARCH_REQUIRED.value),
            official_url=form.get("official_url"),
            referral_url=form.get("referral_url"),
            referral_code=form.get("referral_code"),
            referral_url_template=form.get("referral_url_template"),
            affiliate_program=form.get("affiliate_program"),
            program_type=form.get("program_type"),
            commission_description=form.get("commission_description"),
            eligibility_notes=form.get("eligibility_notes"),
            geographic_restrictions=form.get("geographic_restrictions"),
            evidence_url=form.get("evidence_url"),
            evidence_reference=form.get("evidence_reference"),
            applied_at=_parse_dt(form.get("applied_at")),
            verified_at=_parse_dt(form.get("verified_at")),
            last_checked_at=_parse_dt(form.get("last_checked_at")),
            expires_at=_parse_dt(form.get("expires_at")),
            operator_notes=form.get("operator_notes"),
        )
    except (ReferralValidationError, MonetizationPersistenceError) as exc:
        return _render_editor(opportunity_id, settings=settings, engine=engine, error=str(exc), status_code=400)
    return RedirectResponse(f"/operator/referrals/{opportunity_id}", status_code=303, headers=NOINDEX_HEADERS)


@router.get("/revenue")
def revenue_form(
    _operator: str = Depends(require_operator),
    engine: Engine = Depends(get_database_engine),
) -> HTMLResponse:
    repository = MonetizationRepository(engine)
    body = _revenue_form(repository)
    return _operator_response("Revenue Entry | GamCryp", body)


@router.post("/revenue")
async def save_revenue(
    request: Request,
    _operator: str = Depends(require_operator),
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_database_engine),
) -> Response:
    form = await _form(request)
    try:
        _service(engine, settings).save_revenue_attribution(
            destination_slug=form.get("destination_slug", ""),
            click_period_start=_parse_dt_required(form.get("click_period_start"), "click_period_start"),
            click_period_end=_parse_dt_required(form.get("click_period_end"), "click_period_end"),
            verified_conversion_count=_parse_int(form.get("verified_conversion_count")),
            revenue_amount=form.get("revenue_amount") or None,
            revenue_currency=form.get("revenue_currency") or None,
            settlement_reference_id=form.get("settlement_reference_id"),
            evidence_reference=form.get("evidence_reference"),
            notes=form.get("notes"),
            attribution_status=form.get("attribution_status", RevenueAttributionStatus.PENDING.value),
        )
    except (ValueError, MonetizationPersistenceError) as exc:
        return _operator_response("Revenue Entry | GamCryp", _revenue_form(MonetizationRepository(engine), error=str(exc)), status_code=400)
    return RedirectResponse("/operator/revenue", status_code=303, headers=NOINDEX_HEADERS)


def _service(engine: Engine, settings: Settings) -> ReferralOperationsService:
    return ReferralOperationsService(
        MonetizationRepository(engine),
        reverify_days=settings.referral_reverify_days,
        pending_recheck_days=settings.referral_pending_recheck_days,
    )


def _render_editor(
    opportunity_id: str,
    *,
    settings: Settings,
    engine: Engine,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    opportunity = get_opportunity(opportunity_id)
    destination = primary_destination_for_opportunity(opportunity_id)
    if opportunity is None or destination is None:
        raise HTTPException(status_code=404, detail="Unknown opportunity or destination.", headers=NOINDEX_HEADERS)
    repository = MonetizationRepository(engine)
    program = repository.get_referral_program(destination.destination_slug)
    row = _service(engine, settings).coverage_rows()
    selected = next(item for item in row if item.opportunity.opportunity_id == opportunity_id)
    body = f"""
      <section class="page-head operator-head">
        <p class="eyebrow">Referral Editor</p>
        <h1>{escape(opportunity.name)}</h1>
        <p class="lede">Current coverage: {_badge(selected.coverage_state.value, selected.coverage_state.value.lower())}</p>
        {'<p class="alert">' + escape(error) + '</p>' if error else ''}
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Edit Commercial Metadata</h2></div>
        <form class="operator-form" method="post" action="/operator/referrals/{escape(opportunity_id)}">
          {_input('Official URL', 'official_url', program.official_url if program else destination.official_url)}
          {_input('Referral URL', 'referral_url', program.referral_url if program else '')}
          {_input('Referral code', 'referral_code', program.referral_code if program else '')}
          {_input('Referral URL template', 'referral_url_template', program.referral_url_template if program else '')}
          {_input('Program name', 'affiliate_program', program.affiliate_program if program else '')}
          {_input('Program type', 'program_type', program.program_type if program else '')}
          {_textarea('Commission/reward description', 'commission_description', program.commission_description if program else '')}
          {_textarea('Eligibility notes', 'eligibility_notes', program.eligibility_notes if program else '')}
          {_textarea('Geographic restrictions', 'geographic_restrictions', program.geographic_restrictions if program else '')}
          {_select_status(program.referral_status if program else ReferralLifecycleStatus.RESEARCH_REQUIRED)}
          {_input('Evidence/source URL', 'evidence_url', program.evidence_url if program else '')}
          {_input('Evidence/reference', 'evidence_reference', str(program.evidence.get('source', '')) if program else '')}
          {_input('Applied at UTC', 'applied_at', _dt_value(program.applied_at if program else None))}
          {_input('Verified at UTC', 'verified_at', _dt_value(program.verified_at if program else None))}
          {_input('Last checked at UTC', 'last_checked_at', _dt_value(program.last_checked_at if program else None))}
          {_input('Expiration UTC', 'expires_at', _dt_value(program.expires_at if program else None))}
          {_textarea('Operator notes', 'operator_notes', program.operator_notes if program else '')}
          <div class="button-row"><button class="button" type="submit">Save referral metadata</button><a class="secondary-button" href="/operator/referrals">Back to queue</a></div>
        </form>
      </section>
    """
    return _operator_response("Referral Editor | GamCryp", body, status_code=status_code)


def _revenue_form(repository: MonetizationRepository, *, error: str | None = None) -> str:
    records = repository.revenue_attributions()
    return f"""
      <section class="page-head operator-head">
        <p class="eyebrow">Operator Console</p>
        <h1>Manual Revenue Entry</h1>
        <p class="lede">Enter only partner-verified conversions/revenue. Pending imports are retained but never counted as verified.</p>
        {'<p class="alert">' + escape(error) + '</p>' if error else ''}
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>New Attribution Record</h2></div>
        <form class="operator-form" method="post" action="/operator/revenue">
          {_input('Destination slug', 'destination_slug', '')}
          {_select_attribution_status()}
          {_input('Period start UTC', 'click_period_start', '')}
          {_input('Period end UTC', 'click_period_end', '')}
          {_input('Verified conversions', 'verified_conversion_count', '')}
          {_input('Revenue amount', 'revenue_amount', '')}
          {_input('Revenue currency', 'revenue_currency', 'USD')}
          {_input('Settlement/reference ID', 'settlement_reference_id', '')}
          {_input('Evidence/source', 'evidence_reference', '')}
          {_textarea('Notes', 'notes', '')}
          <button class="button" type="submit">Save revenue record</button>
        </form>
      </section>
      <section class="section-panel">
        <div class="section-header"><h2>Recent Revenue Records</h2><span class="badge info">{len(records)} stored</span></div>
        <div class="section-body contributor-list">{''.join(_revenue_card(record) for record in records) or '<p class="muted">No revenue attribution records yet.</p>'}</div>
      </section>
    """


def _operator_response(title: str, body: str, *, status_code: int = 200) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="/assets/styles.css">
  </head>
  <body>
    <header class="site-header"><a class="brand" href="/operator/referrals"><span class="brand-name">GamCryp Operator</span><span class="brand-tagline">Referral operations</span></a></header>
    <main id="app"><div class="page-shell operator-shell">{body}</div></main>
  </body>
</html>"""
    return HTMLResponse(html, status_code=status_code, headers=NOINDEX_HEADERS)


def _summary_cards(summary) -> str:
    return f"""
      <section class="summary-grid">
        {_summary('Published', str(summary.total_published_opportunities))}
        {_summary('Referral active', str(summary.referral_active_count))}
        {_summary('Missing', str(summary.referral_missing_count))}
        {_summary('Pending', str(summary.referral_pending_count))}
        {_summary('No program found', str(summary.no_program_found_count))}
        {_summary('Expired', str(summary.expired_count))}
        {_summary('Reverify', str(summary.reverify_count))}
        {_summary('Coverage', f'{summary.referral_coverage_percentage.quantize(Decimal("0.01"))}%')}
      </section>
    """


def _queue_row(row) -> str:
    program = row.program
    destination = row.destination
    official = destination.official_url if destination else "Unavailable"
    return f"""
      <tr>
        <td>{escape(row.opportunity.name)}</td>
        <td>{escape(row.opportunity.opportunity_type)}</td>
        <td>{_badge(row.coverage_state.value, row.coverage_state.value.lower())}</td>
        <td><a href="{escape(official)}" rel="noopener noreferrer">{escape(official)}</a></td>
        <td>{escape(program.affiliate_program if program and program.affiliate_program else 'None')}</td>
        <td>{escape(_dt_value(program.last_checked_at if program else None) or 'Never')}</td>
        <td>{escape(row.next_action)}</td>
        <td>{row.priority}</td>
        <td><a class="secondary-button" href="/operator/referrals/{escape(row.opportunity.opportunity_id)}">Edit</a></td>
      </tr>
    """


def _filter_links() -> str:
    states = [state.value for state in ReferralCoverageState]
    type_links = ("GAME", "DEPIN_NODE", "POINTS")
    return "".join(f'<a class="secondary-button" href="/operator/referrals?state={state}">{state}</a>' for state in states) + "".join(
        f'<a class="secondary-button" href="/operator/referrals?opportunity_type={kind}">{kind}</a>' for kind in type_links
    )


def _task_card(task) -> str:
    due = _dt_value(task.due_at) or "No due date"
    return f'<article class="contributor"><strong>{escape(task.task_type.value)}</strong><span>{escape(task.opportunity_id)} | {escape(task.reason)}</span><small>{escape(due)}</small></article>'


def _revenue_card(record) -> str:
    amount = f"{record.revenue_amount} {record.revenue_currency}".strip() if record.revenue_amount is not None else "No revenue"
    return f'<article class="contributor"><strong>{escape(record.destination_slug)}</strong><span>{escape(record.attribution_status.value)} | {escape(amount)} | conversions={escape(str(record.verified_conversion_count))}</span><small>{escape(record.settlement_reference_id or "No settlement reference")}</small></article>'


def _summary(label: str, value: str) -> str:
    return f'<div class="summary-item"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _badge(label: str, class_name: str = "") -> str:
    return f'<span class="badge {escape(class_name.lower())}">{escape(label)}</span>'


def _input(label: str, name: str, value: str | None) -> str:
    return f'<label class="field"><span>{escape(label)}</span><input name="{escape(name)}" value="{escape(value or "")}"></label>'


def _textarea(label: str, name: str, value: str | None) -> str:
    return f'<label class="field"><span>{escape(label)}</span><textarea name="{escape(name)}">{escape(value or "")}</textarea></label>'


def _select_status(selected: ReferralLifecycleStatus) -> str:
    options = "".join(
        f'<option value="{status.value}" {"selected" if status is selected else ""}>{status.value}</option>'
        for status in ReferralLifecycleStatus
    )
    return f'<label class="field"><span>Status</span><select name="referral_status">{options}</select></label>'


def _select_attribution_status() -> str:
    options = "".join(f'<option value="{status.value}">{status.value}</option>' for status in RevenueAttributionStatus)
    return f'<label class="field"><span>Attribution status</span><select name="attribution_status">{options}</select></label>'


async def _form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1].strip() for key, values in parsed.items()}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if len(text) == 10:
        return datetime.fromisoformat(text).replace(tzinfo=UTC)
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def _parse_dt_required(value: str | None, name: str) -> datetime:
    parsed = _parse_dt(value)
    if parsed is None:
        raise ValueError(f"{name} is required")
    return parsed


def _parse_int(value: str | None) -> int | None:
    if value in {None, ""}:
        return None
    number = int(value)
    if number < 0:
        raise ValueError("numeric values cannot be negative")
    return number


def _dt_value(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _state_filter(value: str | None) -> ReferralCoverageState | None:
    if not value:
        return None
    return ReferralCoverageState(value)


def _auth_headers() -> dict[str, str]:
    headers = dict(NOINDEX_HEADERS)
    headers["WWW-Authenticate"] = "Basic"
    return headers
