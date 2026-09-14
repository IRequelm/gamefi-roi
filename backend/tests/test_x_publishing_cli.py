"""Regression coverage for direct local X operator invocation."""

from __future__ import annotations

import json
from pathlib import Path

from app.distribution import x_publishing_cli


def test_authorize_url_loads_ignored_local_env(monkeypatch, tmp_path: Path, capsys) -> None:
    """The direct CLI must see the same OAuth configuration as the worker."""

    (tmp_path / ".env").write_text(
        "GAMEFI_X_CLIENT_ID=test-client-id\n"
        "GAMEFI_X_REDIRECT_URI=http://127.0.0.1:8765/callback\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GAMEFI_X_CLIENT_ID", raising=False)
    monkeypatch.delenv("GAMEFI_X_REDIRECT_URI", raising=False)

    assert x_publishing_cli.main(["authorize-url"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "client_id=test-client-id" in payload["authorization_url"]
    assert payload["external_action_required"] is True
