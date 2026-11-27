import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.api.router import api_router
from app.api.routes.auth import router as auth_router
from app.api.routes.competitor_evidence import router as competitor_evidence_router
from app.api.routes.execution import router as execution_router
from app.api.routes.personas import router as personas_router
from app.api.routes.posts import router as posts_router
from app.api.routes.products import router as products_router
from app.api.routes.simulations import router as simulations_router
from app.core.config import Settings
from app.db.session import create_db_engine
from app.services.simulation_worker import worker_loop


def create_app(settings: Settings | None = None) -> FastAPI:
    # Validate configuration at startup, without opening a database connection.
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(settings)
        application.state.session_factory = sessionmaker(
            bind=engine, expire_on_commit=False
        )
        worker = None
        # The worker also processes deterministic fallback-only runs, so an API
        # key is not a prerequisite for starting it.
        if settings.simulation_worker_enabled:
            worker = asyncio.create_task(
                worker_loop(application.state.session_factory, settings)
            )
        try:
            yield
        finally:
            if worker:
                worker.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker
            engine.dispose()

    application = FastAPI(title="Buyora API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.include_router(auth_router)
    application.include_router(competitor_evidence_router)
    application.include_router(products_router)
    application.include_router(posts_router)
    application.include_router(simulations_router)
    application.include_router(personas_router)
    application.include_router(execution_router)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(api_router)

    @application.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"message": "Welcome to Buyora API"}

    return application
