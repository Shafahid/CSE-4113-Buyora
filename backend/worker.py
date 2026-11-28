"""Run Buyora's durable simulation worker as a separate process."""

import asyncio
import logging

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import create_db_engine
from app.services.ai.jobs import worker_loop as optional_worker_loop
from app.services.simulation_worker import worker_loop


async def serve() -> None:
    settings = Settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tasks = [asyncio.create_task(worker_loop(factory, settings))]
    if settings.phase2_ai_enabled:
        tasks.append(asyncio.create_task(optional_worker_loop(factory, settings)))
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
