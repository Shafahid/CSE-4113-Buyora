"""Isolated HTTP API for the frontend integration test; never reads .env.

Invoked by frontend/tests/api-live.mjs with an ephemeral localhost port.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.pool import QueuePool  # noqa: E402

import app.main as main_module  # noqa: E402
from app.api.routes import products  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.models import Base  # noqa: E402


class MemoryStorage:
    def __init__(self):
        self.objects = {}

    def upload(self, key, data, content_type):
        self.objects[key] = data

    def remove(self, key):
        self.objects.pop(key, None)

    def signed_url(self, key):
        return "https://storage.example/signed/" + key


def main():
    engine = create_engine(
        "sqlite:///file:buyora_frontend_test?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        execution_options={"schema_translate_map": {"public": None, "buyora": None}},
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    main_module.create_db_engine = lambda _: engine
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:placeholder@localhost/unused",
        session_cookie_name="buyora_session",
        session_cookie_secure=False,
        session_cookie_samesite="lax",
        session_lifetime_seconds=604800,
        cors_origins=["http://localhost:3000"],
    )
    app = main_module.create_app(settings)
    storage = MemoryStorage()
    app.dependency_overrides[products.get_storage] = lambda: storage
    products.get_storage = lambda _: storage
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")


if __name__ == "__main__":
    main()
