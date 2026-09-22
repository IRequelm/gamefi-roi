"""Email approval workflow for autonomous discovery candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
import hashlib
import imaplib
import os
import re
import smtplib
import ssl
import tempfile
from pathlib import Path
from typing import Literal

from app.discovery.engine import AdmissionDecision, DiscoveryRecord


class DiscoveryApprovalError(RuntimeError):
    """A configured approval operation could not be completed."""


ApprovalCommand = Literal["APPROVE", "REJECT"]


@dataclass(frozen=True)
class ApprovalCommandResult:
    command: ApprovalCommand
    token: str


@dataclass(frozen=True)
class DiscoveryApprovalEmailConfig:
    enabled: bool = False
    to_address: str = ""
    from_address: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    outbox_dir: Path = Path("data/local/discovery/approval_outbox")

    @classmethod
    def from_environment(cls) -> "DiscoveryApprovalEmailConfig":
        return cls(
            enabled=os.getenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            to_address=os.getenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO", "").strip(),
            from_address=os.getenv("GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM", "").strip(),
            smtp_host=os.getenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_HOST", "smtp.gmail.com").strip(),
            smtp_port=int(os.getenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_PORT", "587")),
            smtp_username=os.getenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD", ""),
            imap_host=os.getenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_HOST", "imap.gmail.com").strip(),
            imap_port=int(os.getenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_PORT", "993")),
            imap_username=os.getenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_USERNAME", "").strip(),
            imap_password=os.getenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_PASSWORD", ""),
            imap_folder=os.getenv("GAMEFI_DISCOVERY_APPROVAL_IMAP_FOLDER", "INBOX").strip() or "INBOX",
            outbox_dir=Path(os.getenv("GAMEFI_DISCOVERY_APPROVAL_OUTBOX_DIR", "data/local/discovery/approval_outbox")),
        )

    def validate_smtp(self) -> None:
        missing = [name for name, value in {
            "GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO": self.to_address,
            "GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM": self.from_address,
            "GAMEFI_DISCOVERY_APPROVAL_SMTP_USERNAME": self.smtp_username,
            "GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD": self.smtp_password,
        }.items() if not value]
        if missing:
            raise DiscoveryApprovalError("discovery approval email is enabled but SMTP configuration is missing: " + ", ".join(missing))

    def validate_imap(self) -> None:
        missing = [name for name, value in {
            "GAMEFI_DISCOVERY_APPROVAL_IMAP_USERNAME": self.imap_username,
            "GAMEFI_DISCOVERY_APPROVAL_IMAP_PASSWORD": self.imap_password,
        }.items() if not value]
        if missing:
            raise DiscoveryApprovalError("discovery approval polling is enabled but IMAP configuration is missing: " + ", ".join(missing))

    def readiness_status(self) -> str:
        """Return a secret-free operational state for health/reporting."""
        if not self.enabled:
            return "DISABLED"
        smtp_missing = not all((self.to_address, self.from_address, self.smtp_username, self.smtp_password))
        imap_missing = not all((self.imap_username, self.imap_password))
        if not smtp_missing and not imap_missing:
            return "READY"
        if smtp_missing and imap_missing:
            return "INCOMPLETE_SMTP_IMAP"
        return "INCOMPLETE_SMTP" if smtp_missing else "INCOMPLETE_IMAP"

    def missing_configuration(self) -> dict[str, list[str]]:
        """Return missing variable names without exposing credential values."""
        return {
            "smtp": [name for name, value in {
                "GAMEFI_DISCOVERY_APPROVAL_EMAIL_TO": self.to_address,
                "GAMEFI_DISCOVERY_APPROVAL_EMAIL_FROM": self.from_address,
                "GAMEFI_DISCOVERY_APPROVAL_SMTP_USERNAME": self.smtp_username,
                "GAMEFI_DISCOVERY_APPROVAL_SMTP_PASSWORD": self.smtp_password,
            }.items() if not value],
            "imap": [name for name, value in {
                "GAMEFI_DISCOVERY_APPROVAL_IMAP_USERNAME": self.imap_username,
                "GAMEFI_DISCOVERY_APPROVAL_IMAP_PASSWORD": self.imap_password,
            }.items() if not value],
        }


def create_approval_token() -> str:
    import secrets
    return secrets.token_urlsafe(24)


def hash_approval_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_approval_command(text: str) -> ApprovalCommandResult | None:
    """Parse only an explicit command; ordinary prose cannot approve a candidate."""
    normalized = " ".join(text.split())
    match = re.search(r"(?<!\w)(SITEYE[_ ]+EKLE|ADD[_ ]+TO[_ ]+SITE|REDDET|REJECT)\s+([A-Za-z0-9_-]{20,})(?![A-Za-z0-9_-])", normalized, flags=re.IGNORECASE)
    if not match:
        return None
    command_text = match.group(1).upper().replace("_", " ")
    command = "APPROVE" if command_text in {"SITEYE EKLE", "ADD TO SITE"} else "REJECT"
    return ApprovalCommandResult(command, match.group(2))


class DiscoveryApprovalMailer:
    def __init__(self, config: DiscoveryApprovalEmailConfig):
        self.config = config

    def send(self, record: DiscoveryRecord, decision: AdmissionDecision, token: str, *, now: datetime | None = None) -> None:
        if not self.config.enabled:
            return
        self.config.validate_smtp()
        current = (now or datetime.now(UTC)).astimezone(UTC)
        message = EmailMessage()
        message["Subject"] = f"GamCryp discovery approval: {record.canonical_name}"
        message["From"] = self.config.from_address
        message["To"] = self.config.to_address
        evidence = "\n".join(f"- {item.fact}: {item.source_url}" for item in record.evidence if item.verified) or "- No verified evidence yet"
        missing = ", ".join(decision.missing_evidence) or "none"
        message.set_content(
            "GamCryp discovery candidate review\n\n"
            f"Candidate: {record.canonical_name}\nSource: {record.discovery_source}\nScore: {record.discovery_score}\n"
            f"Proposed action: {decision.outcome}\nMissing evidence: {missing}\nOfficial URL: {record.official_url or 'none'}\n"
            f"Requested at: {current.isoformat()}\n\nVerified evidence:\n{evidence}\n\n"
            "To add this candidate to the site, reply with this exact command:\n"
            f"SITEYE_EKLE {token}\n\nTo reject it:\nREDDET {token}\n\n"
            "This approval is not an ROI estimate or investment advice. MODELED candidates are not published as financial outcomes until reproducible data and ROI evidence are verified."
        )
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=20) as client:
                client.starttls(context=context)
                client.login(self.config.smtp_username, self.config.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise DiscoveryApprovalError("discovery approval email delivery failed") from exc

    def send_lead_digest(self, suggestions: list[dict[str, object]], *, now: datetime | None = None) -> None:
        """Notify the operator of new research leads without asserting identity or ROI."""
        if not self.config.enabled or not suggestions:
            return
        self.config.validate_smtp()
        current = (now or datetime.now(UTC)).astimezone(UTC)
        lines = [
            "GamCryp discovery leads",
            "",
            "These are research leads from trend signals, not verified projects, official URLs, earnings, or ROI claims.",
            "A separate token-bound approval email is sent only after official evidence is verified.",
            f"Generated at: {current.isoformat()}",
            "",
        ]
        for index, suggestion in enumerate(suggestions, start=1):
            lines.extend([
                f"{index}. {suggestion.get('candidate_name', 'unknown')}",
                f"   source: {suggestion.get('discovery_source', 'unknown')}",
                f"   signal: {suggestion.get('trend_value', 'n/a')}",
                f"   reason: {suggestion.get('reason', 'research required')}",
                f"   source locator: {suggestion.get('source_locator', 'none')}",
                f"   search locator: {suggestion.get('search_locator', 'none')}",
                "",
            ])
        message = EmailMessage()
        message["Subject"] = f"GamCryp discovery leads ({len(suggestions)})"
        message["From"] = self.config.from_address
        message["To"] = self.config.to_address
        message.set_content("\n".join(lines))
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=20) as client:
                client.starttls(context=context)
                client.login(self.config.smtp_username, self.config.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise DiscoveryApprovalError("discovery lead email delivery failed") from exc

    def send_research_lead(self, lead: dict[str, object], token: str, *, now: datetime | None = None) -> None:
        """Send a token-bound approval email for a still-unverified trend lead."""
        if not self.config.enabled:
            return
        self.config.validate_smtp()
        message = self.build_research_lead_message(lead, token, now=now)
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=20) as client:
                client.starttls(context=context)
                client.login(self.config.smtp_username, self.config.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise DiscoveryApprovalError("research candidate approval email delivery failed") from exc

    def build_research_lead_message(self, lead: dict[str, object], token: str, *, now: datetime | None = None) -> EmailMessage:
        """Build the exact approval message without sending it."""
        current = (now or datetime.now(UTC)).astimezone(UTC)
        name = str(lead.get("canonical_name") or "unknown")
        source = str(lead.get("discovery_source") or "unknown")
        query = str(lead.get("discovery_query") or name)
        reason = str(lead.get("why_discovered") or "Trend signal requires research.")
        source_locator = str(lead.get("source_locator") or "none")
        search_locator = str(lead.get("search_locator") or "none")
        message = EmailMessage()
        message["Subject"] = f"GamCryp research candidate approval: {name}"
        if self.config.from_address:
            message["From"] = self.config.from_address
        if self.config.to_address:
            message["To"] = self.config.to_address
        message.set_content(
            "GamCryp research candidate review\n\n"
            f"Candidate: {name}\nDiscovery source: {source}\nQuery: {query}\n"
            f"Why it was found: {reason}\nSource locator: {source_locator}\nSearch locator: {search_locator}\n"
            f"Requested at: {current.isoformat()}\n\n"
            "This is a trend lead, not proof of an official project, earnings, safety, or ROI. "
            "If approved, GamCryp will add a clearly labelled research-candidate page with ROI unavailable. "
            "It will not be treated as an official source or financial model until evidence is verified.\n\n"
            "To add this research candidate to the site, reply with this exact command:\n"
            f"SITEYE_EKLE {token}\n\n"
            "To reject it:\n"
            f"REDDET {token}\n"
        )
        return message

    def write_research_lead_draft(self, lead: dict[str, object], token: str, *, now: datetime | None = None) -> Path:
        """Write an unsent token-bound .eml draft to the ignored local outbox."""
        message = self.build_research_lead_message(lead, token, now=now)
        discovery_id = str(lead.get("discovery_id") or lead.get("canonical_name") or "lead")
        filename = hashlib.sha256(discovery_id.encode("utf-8")).hexdigest()[:24] + ".eml"
        directory = self.config.outbox_dir
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / filename
        descriptor, temporary = tempfile.mkstemp(prefix=f".{filename}.", dir=str(directory), suffix=".tmp")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(message.as_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target


class DiscoveryApprovalInbox:
    def __init__(self, config: DiscoveryApprovalEmailConfig):
        self.config = config

    def poll(self, repository, *, limit: int = 25) -> list[dict[str, str]]:
        if not self.config.enabled:
            return []
        self.config.validate_imap()
        processed: list[dict[str, str]] = []
        with imaplib.IMAP4_SSL(self.config.imap_host, self.config.imap_port) as mailbox:
            mailbox.login(self.config.imap_username, self.config.imap_password)
            status, _ = mailbox.select(self.config.imap_folder, readonly=False)
            if status != "OK":
                raise DiscoveryApprovalError("could not select discovery approval mailbox folder")
            status, data = mailbox.search(None, "UNSEEN")
            if status != "OK":
                raise DiscoveryApprovalError("could not search discovery approval mailbox")
            for message_id in (data[0] or b"").split()[-limit:]:
                status, fetched = mailbox.fetch(message_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = next((part[1] for part in fetched if isinstance(part, tuple) and isinstance(part[1], bytes)), None)
                if raw is None:
                    continue
                command = parse_approval_command(_message_text(message_from_bytes(raw, policy=default)))
                if command is None:
                    continue
                result = repository.decide_token(command.token, approve=command.command == "APPROVE")
                if result["status"] in {"approved", "rejected"}:
                    mailbox.store(message_id, "+FLAGS", "\\Seen")
                    processed.append({"token": command.token, "status": result["status"], "discovery_id": result["discovery_id"]})
        return processed


def _message_text(message) -> str:
    if message.is_multipart():
        return "\n".join(
            part.get_content()
            for part in message.walk()
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition", "").startswith("attachment")
        )
    return message.get_content() if message.get_content_type() == "text/plain" else ""
