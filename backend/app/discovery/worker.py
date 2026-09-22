"""Restart-safe, no-publish discovery intelligence worker."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import get_settings
from app.discovery.approval import DiscoveryApprovalEmailConfig, DiscoveryApprovalInbox, DiscoveryApprovalMailer
from app.discovery.approval import parse_approval_command
from app.discovery.content_intelligence import build_editorial_brief
from app.discovery.engine import DiscoveryRecord
from app.discovery.providers import CoinGeckoMarketProvider, GoogleNewsResearchProvider, GoogleTrendsProvider, ProviderResult, UnavailableProvider, XDiscoveryProvider
from app.storage.database import create_database_engine
from app.storage.discovery import DiscoveryRepository
from app.storage.metadata import Base


@dataclass(frozen=True)
class DiscoveryWorkerConfig:
    state_file: Path = Path("data/local/discovery/worker_state.json")
    interval_seconds: int = 21600

    @classmethod
    def from_environment(cls) -> "DiscoveryWorkerConfig":
        return cls(
            state_file=Path(os.getenv("GAMEFI_DISCOVERY_WORKER_STATE_FILE", "data/local/discovery/worker_state.json")),
            interval_seconds=int(os.getenv("GAMEFI_DISCOVERY_WORKER_INTERVAL_SECONDS", "21600")),
        )


class DiscoveryWorker:
    def __init__(self, *, config: DiscoveryWorkerConfig | None = None) -> None:
        self.config = config or DiscoveryWorkerConfig.from_environment()

    def run_once(self) -> dict[str, object]:
        google_trends = GoogleTrendsProvider().probe()
        trends_have_candidate_leads = bool(_candidate_suggestions((google_trends,)))
        google_news = (
            GoogleNewsResearchProvider().probe()
            if google_trends.status in {"QUERY_EMPTY", "BLOCKED"} or not trends_have_candidate_leads
            else ProviderResult(
                "google_news",
                "SKIPPED_TRENDS_LIVE",
                google_trends.retrieved_at,
                limitation="Google Trends returned usable live signals; Google News fallback was not needed.",
            )
        )
        results = (
            google_trends,
            google_news,
            CoinGeckoMarketProvider().query(),
            UnavailableProvider("youtube_data_api", "No authorized live API credentials configured.").probe(),
            XDiscoveryProvider().probe(),
        )
        now = datetime.now(UTC)
        approval_email_config = DiscoveryApprovalEmailConfig.from_environment()
        suggestions = _candidate_suggestions(results)
        candidate_email_status, emailed_keys, drafted_keys = self._notify_new_suggestions(suggestions, now=now)
        payload: dict[str, object] = {
            "state_version": "discovery-worker-v1",
            "updated_at": now.isoformat(),
            "publish_performed": False,
            "providers": [_provider_payload(result) for result in results],
            "candidate_suggestions": suggestions,
            "candidate_email_status": candidate_email_status,
            "approval_email_status": approval_email_config.readiness_status(),
            "emailed_candidate_keys": emailed_keys,
            "drafted_candidate_keys": drafted_keys,
            "approval_processed": self._poll_approvals(),
            "source_failures": [result.limitation for result in results if result.status == "BLOCKED" and result.limitation],
        }
        _atomic_write(self.config.state_file, payload)
        return payload

    def _notify_new_suggestions(self, suggestions: list[dict[str, object]], *, now: datetime) -> tuple[str, list[str], list[str]]:
        previous = _read_json(self.config.state_file)
        old_keys = {str(value) for value in previous.get("emailed_candidate_keys", []) if isinstance(value, str)}
        config = DiscoveryApprovalEmailConfig.from_environment()
        old_drafted_keys = {str(value) for value in previous.get("drafted_candidate_keys", []) if isinstance(value, str)}
        new_suggestions = [
            item for item in suggestions
            if _suggestion_key(item) not in old_keys
            and (config.enabled or _suggestion_key(item) not in old_drafted_keys)
        ]
        if not new_suggestions:
            status = "outbox" if old_drafted_keys and not config.enabled else "none"
            return (status, sorted(old_keys), sorted(old_drafted_keys))
        engine = None
        emailed_keys = set(old_keys)
        drafted_keys = set(old_drafted_keys)
        try:
            engine = create_database_engine(get_settings())
            mailer = DiscoveryApprovalMailer(config) if config.enabled else None
            repository = DiscoveryRepository(engine, approval_mailer=mailer)
            drafts_written = 0
            for suggestion in new_suggestions:
                key = _suggestion_key(suggestion)
                needs_draft = not config.enabled and key not in drafted_keys
                lead, token, is_new = repository.upsert_research_lead(suggestion, rotate_pending_token=config.enabled or needs_draft)
                if config.enabled:
                    if token and mailer is not None:
                        mailer.send_research_lead(lead, token, now=now)
                    # A key is marked handled only after SMTP accepts the
                    # message, or when the existing lead is already no longer
                    # pending and therefore needs no second email. Persisted-
                    # but-undelivered leads remain eligible for token rotation
                    # and retry later.
                    emailed_keys.add(_suggestion_key(suggestion))
                elif token and (is_new or needs_draft):
                    DiscoveryApprovalMailer(config).write_research_lead_draft(lead, token, now=now)
                    drafted_keys.add(key)
                    drafts_written += 1
        except Exception as exc:
            return (f"blocked:{type(exc).__name__}", sorted(emailed_keys)[-200:], sorted(drafted_keys)[-200:])
        finally:
            if engine is not None:
                engine.dispose()
        updated = sorted(emailed_keys)[-200:]
        if config.enabled:
            return ("sent", updated, sorted(drafted_keys)[-200:])
        return ("outbox" if drafts_written or drafted_keys else "disabled", updated, sorted(drafted_keys)[-200:])

    @staticmethod
    def _poll_approvals() -> list[dict[str, str]]:
        config = DiscoveryApprovalEmailConfig.from_environment()
        if not config.enabled:
            return []
        engine = None
        try:
            engine = create_database_engine(get_settings())
            repository = DiscoveryRepository(engine, approval_mailer=DiscoveryApprovalMailer(config))
            return DiscoveryApprovalInbox(config).poll(repository)
        except Exception:
            # Discovery and approval must remain fail-closed; a mailbox or
            # database outage cannot create a catalog entry or block provider
            # telemetry from being persisted.
            return []
        finally:
            if engine is not None:
                engine.dispose()

    def run_forever(self) -> None:
        if self.config.interval_seconds < 300:
            raise ValueError("discovery worker interval must be at least 300 seconds")
        while True:
            self.run_once()
            time.sleep(self.config.interval_seconds)


def _provider_payload(result: ProviderResult) -> dict[str, object]:
    return {
        "provider": result.provider,
        "status": result.status,
        "retrieved_at": result.retrieved_at.isoformat(),
        "signals": list(result.signals),
        "limitation": result.limitation,
    }


def _candidate_suggestions(results: tuple[ProviderResult, ...]) -> list[dict[str, object]]:
    """Expose research leads without admitting them to the product catalog."""
    suggestions: list[dict[str, object]] = []
    seen: set[str] = set()
    for result in results:
        for signal in result.signals:
            if signal.get("name") == "related_query":
                name = str(signal.get("keyword") or "").strip()
                if result.provider == "google_news" or signal.get("status") == "LIVE_GOOGLE_NEWS_RESEARCH_LEAD":
                    reason = (
                        "Google News article lead; it is not trend volume. Verify official identity, participation, "
                        "rewards, and exit path before approval."
                    )
                else:
                    reason = "Google Trends related query; verify official identity, participation, rewards, and exit path before approval."
            elif signal.get("name") == "social_momentum":
                account = str(signal.get("source_account") or "").strip()
                name = f"X lead @{account}" if account else ""
                reason = (
                    "X engagement lead; extract and verify the official project before approval. "
                    f"Post excerpt: {str(signal.get('candidate_hint') or '').strip()}"
                )
            else:
                continue
            if result.provider == "google_news":
                candidate_hint = str(signal.get("candidate_hint") or "").strip()
                if not candidate_hint:
                    continue
                name = candidate_hint
                if _generic_candidate_name(name):
                    continue
            if result.provider == "google_trends" and not _researchable_trend_query(name):
                continue
            key = name.casefold()
            if not name or key in seen or len(name) < 3:
                continue
            seen.add(key)
            suggestions.append({
                "candidate_name": name,
                "discovery_source": result.provider,
                "discovery_query": str(signal.get("keyword") or name),
                "trend_value": signal.get("value"),
                "source_locator": signal.get("source_locator"),
                "search_locator": signal.get("search_locator"),
                "status": "RESEARCH_REQUIRED",
                "reason": reason,
            })
            if len(suggestions) >= 25:
                return suggestions
    return suggestions


def _researchable_trend_query(value: str) -> bool:
    """Reject category/explainer queries that cannot identify a candidate."""
    normalized = " ".join(value.casefold().split())
    if not normalized:
        return False
    generic = {
        "gamefi",
        "depin",
        "crypto node",
        "gpu compute",
        "storage node",
        "crypto nodes",
        "storage nodes",
    }
    if normalized in generic:
        return False
    return not any(
        re.search(pattern, normalized)
        for pattern in (
            r"^what\s+is\b",
            r"^how\s+(?:does|do|to)\b",
            r"\bexplained\b",
            r"\btop\s+\d*\s*(?:crypto|depin|gamefi)",
            r"\b(?:news|price|market\s+cap|price\s+prediction)\b",
        )
    )


def _generic_candidate_name(value: str) -> bool:
    """Keep broad protocol/category names out of the site-candidate queue."""
    return " ".join(value.casefold().split()) in {
        "bitcoin",
        "ethereum",
        "solana",
        "crypto",
        "blockchain",
        "gamefi",
        "depin",
        "web3",
        "visa",
        "next-gen game design",
    }


def _suggestion_key(suggestion: dict[str, object]) -> str:
    return "|".join(str(suggestion.get(field, "")).strip().casefold() for field in ("discovery_source", "candidate_name", "discovery_query"))


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _dry_run_e2e() -> dict[str, object]:
    """Exercise the discovery approval chain without SMTP, IMAP, or publication.

    This is deliberately a fixture-only operator check. It proves that a
    trend lead is persisted, a token-bound command can be parsed, and an
    explicit approval creates a research candidate with an editorial brief.
    It never writes the production database or sends a message.
    """
    from sqlalchemy import create_engine

    class CaptureMailer:
        config = DiscoveryApprovalEmailConfig(enabled=True)

        def __init__(self) -> None:
            self.body = ""

        def send_research_lead(self, lead: dict[str, object], token: str, *, now=None) -> None:
            self.body = (
                "GamCryp research candidate review\n\n"
                f"Candidate: {lead['canonical_name']}\n"
                "To add this research candidate to the site, reply with this exact command:\n"
                f"SITEYE_EKLE {token}\n"
            )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    mailer = CaptureMailer()
    repository = DiscoveryRepository(engine, approval_mailer=mailer)
    suggestion = {
        "candidate_name": "Fixture Trend Project",
        "discovery_source": "google_trends_fixture",
        "discovery_query": "Fixture Trend Project",
        "trend_value": 78,
        "reason": "Fixture-only trend signal; official evidence is still required.",
    }
    lead, token, is_new = repository.upsert_research_lead(suggestion)
    mailer.send_research_lead(lead, token)
    command = parse_approval_command(mailer.body)
    before = len(repository.dynamic_opportunities())
    decision = repository.decide_token(command.token, approve=True) if command else {"status": "not_parsed", "discovery_id": ""}
    candidates = repository.dynamic_opportunities()
    brief_record = DiscoveryRecord(
        canonical_name=str(lead["canonical_name"]),
        aliases=[],
        category="RESEARCH",
        official_url=None,
        discovery_source=str(lead["discovery_source"]),
        discovery_query=str(lead["discovery_query"]),
        evidence_strength="UNKNOWN",
        missing_evidence=list(lead.get("missing_evidence", [])),
        validation_status="RESEARCH_REQUIRED",
        discovery_score=float(lead.get("discovery_score", 0) or 0),
        why_discovered=str(lead.get("why_discovered", "")),
    )
    brief = build_editorial_brief(brief_record) if decision["status"] == "approved" else None
    engine.dispose()
    return {
        "fixture": True,
        "publish_performed": False,
        "external_email_sent": False,
        "lead_persisted": is_new,
        "approval_command_parsed": command is not None,
        "candidate_count_before": before,
        "approval_status": decision["status"],
        "candidate_count_after": len(candidates),
        "candidate": {
            "name": candidates[0].name if candidates else None,
            "opportunity_type": candidates[0].opportunity_type if candidates else None,
            "roi_unavailable": bool(candidates[0].roi_unavailable) if candidates else None,
        },
        "editorial_brief_created": brief is not None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fail-closed discovery intelligence worker.")
    parser.add_argument("--once", action="store_true", help="Run one provider cycle and exit.")
    parser.add_argument("--dry-run-e2e", action="store_true", help="Exercise fixture discovery approval flow without external email or publication.")
    args = parser.parse_args()
    if args.dry_run_e2e:
        print(json.dumps(_dry_run_e2e(), indent=2, sort_keys=True))
        return
    worker = DiscoveryWorker()
    payload = worker.run_once() if args.once else worker.run_forever()
    if args.once:
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
