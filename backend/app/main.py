from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.api.router import api_router
from app.core.config import Settings
from app.db.session import create_db_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    # Validate configuration at startup, without opening a database connection.
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(settings)
        application.state.session_factory = sessionmaker(
            bind=engine, expire_on_commit=False
        )
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Buyora API", version="0.1.0", lifespan=lifespan)
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
