from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.exc import OperationalError

from scripts import check_simulation_setup as setup


@pytest.fixture
def setup_engine(settings, monkeypatch):
    engine = Mock()
    monkeypatch.setattr(setup, "Settings", lambda: settings)
    monkeypatch.setattr(setup, "create_db_engine", lambda _: engine)
    return engine


def test_setup_reports_pending_migration_separately_from_worker_schema(
    setup_engine, monkeypatch, capsys
):
    monkeypatch.setattr(setup, "database_revisions", lambda _: {"0015"})
    monkeypatch.setattr(setup, "check_worker_schema", lambda _: True)
    assert setup.main([]) == 1
    output = capsys.readouterr().out
    assert "Database connectivity: OK" in output
    assert "Worker schema: ready" in output
    assert "Pending migrations" in output
    setup_engine.dispose.assert_called_once()


def test_apply_upgrades_to_head_and_rechecks_runtime(setup_engine, monkeypatch):
    heads = set(
        setup.ScriptDirectory.from_config(
            setup.Config(str(setup.BACKEND_DIR / "alembic.ini"))
        ).get_heads()
    )
    revisions = Mock(side_effect=[{"0009"}, heads])
    upgrade = Mock()
    monkeypatch.setattr(setup, "database_revisions", revisions)
    monkeypatch.setattr(setup.command, "upgrade", upgrade)
    monkeypatch.setattr(setup, "check_worker_schema", lambda _: True)
    assert setup.main(["--apply"]) == 0
    assert upgrade.call_args.args[1] == "head"
    assert revisions.call_count == 2


def test_setup_rejects_unknown_revision_before_applying(setup_engine, monkeypatch):
    monkeypatch.setattr(setup, "database_revisions", lambda _: {"unknown"})
    upgrade = Mock()
    monkeypatch.setattr(setup.command, "upgrade", upgrade)
    assert setup.main(["--apply"]) == 1
    upgrade.assert_not_called()


def test_setup_failure_hides_driver_message(setup_engine, monkeypatch, capsys):
    def fail(_):
        raise OperationalError(
            "private SQL", {}, RuntimeError("private connection reset")
        )

    monkeypatch.setattr(setup, "database_revisions", fail)
    assert setup.main([]) == 1
    output = capsys.readouterr().out
    assert "connection dropped" in output
    assert "private" not in output
    setup_engine.dispose.assert_called_once()


@pytest.mark.parametrize("missing_table", [False, True])
def test_worker_schema_detects_missing_metadata_or_adaptation_table(
    monkeypatch, capsys, missing_table
):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    inspector = Mock()
    inspector.has_table.side_effect = lambda name, **_: (
        not (missing_table and name == "persona_adaptations")
    )
    models = {model.__tablename__: model for model in setup.WORKER_MODELS}

    def columns(name, **_):
        return [
            {"name": column.name}
            for column in models[name].__table__.columns
            if missing_table or column.name != "stage"
        ]

    inspector.get_columns.side_effect = columns
    monkeypatch.setattr(setup, "inspect", lambda _: inspector)
    assert setup.check_worker_schema(engine) is False
    output = capsys.readouterr().out
    assert ("persona_adaptations" if missing_table else "stage") in output
    for call in connection.execute.call_args_list:
        assert "WHERE false" in str(call.args[0])
