import asyncio

import pytest
from sqlalchemy.exc import OperationalError

from app.services.simulation_worker import worker_loop


@pytest.mark.parametrize(
    "state,message,expected",
    [
        ("42P01", "private table", "alembic upgrade head"),
        ("28P01", "private password", "authentication failed"),
        (None, "connection timeout private-host", "connection timed out"),
        (None, "getaddrinfo failed private-host", "hostname could not be resolved"),
    ],
)
def test_worker_logs_actionable_database_failure_without_secrets(
    settings, monkeypatch, caplog, state, message, expected
):
    original = RuntimeError(message)
    original.sqlstate = state

    def fail(factory):
        raise OperationalError("private SQL", {"secret": "private password"}, original)

    async def stop(delay):
        raise asyncio.CancelledError

    monkeypatch.setattr("app.services.persona_jobs.claim_adaptation", fail)
    monkeypatch.setattr("app.services.simulation_worker.asyncio.sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(worker_loop(None, settings))
    assert expected in caplog.text
    assert "persona adaptation queue" in caplog.text
    assert "private" not in caplog.text


def test_standalone_worker_builds_session_factory_and_disposes_engine(
    settings, monkeypatch
):
    import worker

    seen = []

    class Engine:
        disposed = False

        def dispose(self):
            self.disposed = True

    engine = Engine()
    factory = object()

    async def run(received_factory, received_settings):
        seen.append((received_factory, received_settings))

    monkeypatch.setattr(worker, "Settings", lambda: settings)
    monkeypatch.setattr(worker, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(worker, "sessionmaker", lambda **kwargs: factory)
    monkeypatch.setattr(worker, "worker_loop", run)
    asyncio.run(worker.serve())
    assert seen == [(factory, settings)]
    assert engine.disposed
