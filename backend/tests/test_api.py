from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import DbSession, get_db
from app.main import create_app


@pytest.fixture
def application(settings: Settings, tmp_path: Path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'sessions.db'}")
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    return create_app(settings), engine


def test_welcome_liveness_and_docs_need_no_database_connection(application) -> None:
    app, engine = application
    connected = Mock()
    event.listen(engine, "connect", connected)

    with TestClient(app) as client:
        assert client.get("/").json() == {"message": "Welcome to Buyora API"}
        assert client.get("/api/v1/health/live").json() == {"status": "ok"}
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
    connected.assert_not_called()


def test_readiness_executes_database_query_and_disposes_engine(application) -> None:
    app, engine = application
    disposed = Mock()
    event.listen(engine, "engine_disposed", disposed)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    disposed.assert_called_once()


def test_readiness_failure_is_503_without_connection_details(application) -> None:
    app, _ = application
    session = Mock()
    session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("postgresql://postgres:private-password@private-host/db"),
    )
    app.dependency_overrides[get_db] = lambda: session

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "private-password" not in response.text
    assert "private-host" not in response.text


@pytest.mark.parametrize(
    ("commit", "fail", "expected_status", "expected_count"),
    [(False, False, 200, 0), (True, False, 200, 1), (False, True, 409, 0)],
)
def test_request_sessions_only_persist_explicit_commits(
    application, commit, fail, expected_status, expected_count
) -> None:
    app, engine = application
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE session_test (id INTEGER PRIMARY KEY)"))

    @app.post("/test-session")
    def write(db: DbSession):
        db.execute(text("INSERT INTO session_test (id) VALUES (1)"))
        if fail:
            raise HTTPException(status_code=409, detail="Simulated failure")
        if commit:
            db.commit()
        return {"ok": True}

    with TestClient(app) as client:
        assert client.post("/test-session").status_code == expected_status
        with engine.connect() as connection:
            count = connection.scalar(text("SELECT COUNT(*) FROM session_test"))
            assert count == expected_count


def test_cors_allows_only_configured_origins(application) -> None:
    app, _ = application
    with TestClient(app) as client:
        allowed = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://unconfigured.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers
