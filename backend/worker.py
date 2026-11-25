"""Run Buyora's durable simulation worker as a separate process."""

import asyncio
import logging

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import create_db_engine
from app.services.simulation_worker import worker_loop


async def serve() -> None:
    settings = Settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        await worker_loop(factory, settings)
    finally:
        engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
