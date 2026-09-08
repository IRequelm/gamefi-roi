"""Provider-neutral email notification for the local X manual outbox."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from app.distribution.manual_outbox import XManualReadyRecord
from app.distribution.x_amplification import XAmplificationCandidate, XAmplificationOutbox


class XEmailNotificationError(RuntimeError):
    """A configured notification could not be delivered."""


@dataclass(frozen=True)
class XEmailConfig:
    enabled: bool = False
    to_address: str = ""
    from_address: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    state_file: Path = Path("data/local/distribution/x_email_state.json")
    amplification_state_file: Path = Path("data/local/distribution/x_amplification_email_state.json")

    @classmethod
    def from_environment(cls) -> "XEmailConfig":
        return cls(
            enabled=os.getenv("GAMEFI_X_MANUAL_EMAIL_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            to_address=os.getenv("GAMEFI_X_MANUAL_EMAIL_TO", "").strip(),
            from_address=os.getenv("GAMEFI_X_MANUAL_EMAIL_FROM", "").strip(),
            smtp_host=os.getenv("GAMEFI_X_MANUAL_EMAIL_SMTP_HOST", "smtp.gmail.com").strip(),
            smtp_port=int(os.getenv("GAMEFI_X_MANUAL_EMAIL_SMTP_PORT", "587")),
            username=os.getenv("GAMEFI_X_MANUAL_EMAIL_SMTP_USERNAME", "").strip(),
            password=os.getenv("GAMEFI_X_MANUAL_EMAIL_SMTP_PASSWORD", ""),
            state_file=Path(os.getenv("GAMEFI_X_MANUAL_EMAIL_STATE_FILE", str(cls.state_file))),
            amplification_state_file=Path(os.getenv("GAMEFI_X_AMPLIFICATION_EMAIL_STATE_FILE", str(cls.amplification_state_file))),
        )


class XManualEmailNotifier:
    def __init__(self, config: XEmailConfig):
        self.config = config

    def notify_if_needed(self, record: XManualReadyRecord | None) -> str:
        if record is None or record.published:
            return "idle"
        if not self.config.enabled:
            return "disabled"
        self._validate_config()
        if self._last_checksum() == record.checksum:
            return "unchanged"
        message = EmailMessage()
        message["Subject"] = f"GamCryp X post ready: {record.content_id}"
        message["From"] = self.config.from_address
        message["To"] = self.config.to_address
        message.set_content(
            "GamCryp manual X post is ready. Copy the exact post below into X, then confirm it locally.\n\n"
            f"Content ID: {record.content_id}\n"
            f"Checksum: {record.checksum}\n"
            f"Source: {record.source_url}\n\n"
            "--- EXACT POST TEXT ---\n"
            f"{record.post_text}\n"
            "--- END POST TEXT ---\n"
        )
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=20) as client:
                client.starttls(context=context)
                client.login(self.config.username, self.config.password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise XEmailNotificationError("manual X email delivery failed") from exc
        self._save_checksum(record.checksum)
        return "sent"

    def _validate_config(self) -> None:
        missing = [name for name, value in {
            "GAMEFI_X_MANUAL_EMAIL_TO": self.config.to_address,
            "GAMEFI_X_MANUAL_EMAIL_FROM": self.config.from_address,
            "GAMEFI_X_MANUAL_EMAIL_SMTP_USERNAME": self.config.username,
            "GAMEFI_X_MANUAL_EMAIL_SMTP_PASSWORD": self.config.password,
        }.items() if not value]
        if missing:
            raise XEmailNotificationError("manual X email is enabled but required configuration is missing: " + ", ".join(missing))

    def _last_checksum(self) -> str | None:
        try:
            payload = json.loads(self.config.state_file.read_text(encoding="utf-8"))
            return str(payload.get("last_checksum")) if payload.get("last_checksum") else None
        except (OSError, ValueError, TypeError):
            return None

    def _save_checksum(self, checksum: str) -> None:
        self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.config.state_file.name}.", dir=str(self.config.state_file.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "last_checksum": checksum}, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary_name, self.config.state_file)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


class XAmplificationEmailNotifier:
    """Bounded digest notifier for manual amplification candidates."""

    def __init__(self, config: XEmailConfig):
        self.config = config

    def notify_if_needed(self, outbox: XAmplificationOutbox) -> str:
        items = outbox.current()
        if not items:
            return "idle"
        if not self.config.enabled:
            return "disabled"
        self._validate_config()
        digest = _amplification_digest(items)
        if self._last_checksum() == digest:
            return "unchanged"
        message = EmailMessage()
        message["Subject"] = "GamCryp X Amplification"
        message["From"] = self.config.from_address
        message["To"] = self.config.to_address
        sections = []
        for item in items:
            section = (
                f"PROJECT: {item.project_name or item.opportunity_id or 'Methodology'}\n"
                f"SOURCE ACCOUNT: {item.source_account}\n"
                f"RECOMMENDATION: {item.recommendation}\n"
                f"PRIORITY: {item.priority}\n"
                f"WHY: {item.reason}\n"
                f"ORIGINAL X POST URL: {item.original_post_url}\n"
            )
            if item.suggested_quote:
                section += f"SUGGESTED QUOTE:\n{item.suggested_quote}\n"
            sections.append(section)
        message.set_content("GamCryp X Amplification\n\n" + "\n---\n".join(sections))
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=20) as client:
                client.starttls(context=context)
                client.login(self.config.username, self.config.password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise XEmailNotificationError("X amplification email delivery failed") from exc
        self._save_checksum(digest)
        return "sent"

    def _validate_config(self) -> None:
        missing = [name for name, value in {
            "GAMEFI_X_MANUAL_EMAIL_TO": self.config.to_address,
            "GAMEFI_X_MANUAL_EMAIL_FROM": self.config.from_address,
            "GAMEFI_X_MANUAL_EMAIL_SMTP_USERNAME": self.config.username,
            "GAMEFI_X_MANUAL_EMAIL_SMTP_PASSWORD": self.config.password,
        }.items() if not value]
        if missing:
            raise XEmailNotificationError("X amplification email is enabled but required configuration is missing: " + ", ".join(missing))

    def _last_checksum(self) -> str | None:
        try:
            payload = json.loads(self.config.amplification_state_file.read_text(encoding="utf-8"))
            return str(payload.get("amplification_digest")) if payload.get("amplification_digest") else None
        except (OSError, ValueError, TypeError):
            return None

    def _save_checksum(self, checksum: str) -> None:
        self.config.amplification_state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "amplification_digest": checksum}
        fd, temporary_name = tempfile.mkstemp(prefix=f".{self.config.amplification_state_file.name}.", dir=str(self.config.amplification_state_file.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary_name, self.config.amplification_state_file)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


def _amplification_digest(items: tuple[XAmplificationCandidate, ...]) -> str:
    import hashlib
    value = "|".join(item.fingerprint for item in items)
    return hashlib.sha256(value.encode()).hexdigest()
