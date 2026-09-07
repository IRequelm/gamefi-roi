from pathlib import Path

from app.distribution.manual_outbox import manual_ready_record
from app.distribution.x_email_notify import XEmailConfig, XManualEmailNotifier


def test_email_notifier_is_disabled_by_default(tmp_path: Path) -> None:
    notifier = XManualEmailNotifier(XEmailConfig(state_file=tmp_path / "state.json"))
    record = manual_ready_record(content_id="x-1", post_text="Post", source_url="https://gamcryp.com", checksum="abc")
    assert notifier.notify_if_needed(record) == "disabled"


def test_email_notifier_deduplicates_after_success(tmp_path: Path, monkeypatch) -> None:
    sent: list[str] = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, *, context):
            pass

        def login(self, username, password):
            assert username == "sender@example.com"
            assert password == "app-password"

        def send_message(self, message):
            sent.append(message.get_content())

    monkeypatch.setattr("app.distribution.x_email_notify.smtplib.SMTP", FakeSMTP)
    config = XEmailConfig(
        enabled=True,
        to_address="operator@example.com",
        from_address="sender@example.com",
        username="sender@example.com",
        password="app-password",
        state_file=tmp_path / "state.json",
    )
    notifier = XManualEmailNotifier(config)
    record = manual_ready_record(content_id="x-1", post_text="Post", source_url="https://gamcryp.com", checksum="abc")
    assert notifier.notify_if_needed(record) == "sent"
    assert notifier.notify_if_needed(record) == "unchanged"
    assert len(sent) == 1
    assert "Post" in sent[0]
