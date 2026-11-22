"""Isolated HTTP API for the frontend integration test; never reads .env.

Invoked by frontend/tests/api-live.mjs with an ephemeral localhost port.
"""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.pool import QueuePool  # noqa: E402

import app.main as main_module  # noqa: E402
from app.api.routes import products  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.models import Base  # noqa: E402
from app.services import simulation_worker  # noqa: E402
from app.services.llm import ModelFailure  # noqa: E402


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
    # File-backed SQLite waits for concurrent writers; shared in-memory cache
    # returns immediate table-lock errors under worker + progress polling.
    temporary = TemporaryDirectory(prefix="buyora-api-fixture-")
    database = Path(temporary.name) / "api.db"
    engine = create_engine(
        f"sqlite:///{database.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 15},
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
        cors_origins=["http://localhost:3000", "http://localhost:3013"],
        token_bd_api_url="https://model.example/v1",
        token_bd_api_key="test-only-not-real",
        token_bd_model="fixture-model",
        simulation_worker_enabled=True,
    )

    failed_once = set()

    async def fake_evaluation(_, inputs, profile):
        await asyncio.sleep(6 if "--visual" in sys.argv else 0.05)
        if (
            "--partial" in sys.argv
            and profile["id"] in {"cod", "skeptic"}
            and profile["id"] not in failed_once
        ):
            failed_once.add(profile["id"])
            raise ModelFailure("invalid_output")
        return {
            "scores": [70, 80, 65, 60, 55, 80, 60],
            "comment": "What is the total price including delivery?",
            "reason": "The product is practical; the total delivery cost is unclear.",
            "positive": "The product description explains its everyday use.",
            "question": "Can you confirm delivery charges and the return policy?",
            "evidence": [inputs["product"]["name"]],
        }, {"input_tokens": 100, "output_tokens": 80}

    simulation_worker.evaluate_persona = fake_evaluation
    app = main_module.create_app(settings)
    storage = MemoryStorage()
    app.dependency_overrides[products.get_storage] = lambda: storage
    products.get_storage = lambda _: storage
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")


if __name__ == "__main__":
    main()
