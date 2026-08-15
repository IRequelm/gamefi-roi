from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app


def test_health_endpoint_reports_skeleton_status(monkeypatch) -> None:
    monkeypatch.setenv("GAMEFI_ENVIRONMENT", "test")
    monkeypatch.setenv("GAMEFI_ALLOW_SQLITE_FOR_TESTS", "true")
    monkeypatch.setenv("GAMEFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "GameFi ROI API",
        "environment": "test",
        "version": "0.1.0",
    }
