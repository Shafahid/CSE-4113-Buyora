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
from app.api.routes.image_analyses import router as image_analyses_router
from app.api.routes.market_analyses import router as market_analyses_router
from app.api.routes.personas import router as personas_router
from app.api.routes.platform_variants import router as platform_variants_router
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
    application.include_router(image_analyses_router)
    application.include_router(market_analyses_router)
    application.include_router(posts_router)
    application.include_router(platform_variants_router)
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

    original_openapi = application.openapi

    def documented_openapi():
        schema = original_openapi()
        schemas = schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schemas["SellerSession"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.session_cookie_name,
            "description": (
                "Log in through /auth/login. Browser requests use "
                "the HttpOnly session cookie."
            ),
        }
        for path, methods in schema["paths"].items():
            if not any(
                part in path
                for part in (
                    "competitor-evidence",
                    "/images",
                    "/market-analyses",
                    "/variants",
                )
            ):
                continue
            for method, operation in methods.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operation["security"] = [{"SellerSession": []}]
                responses = operation.setdefault("responses", {})
                responses.setdefault(
                    "401", {"description": "Missing or invalid session"}
                )
                responses.setdefault(
                    "404", {"description": "Resource missing or inaccessible"}
                )
                if method in {"post", "put", "patch", "delete"}:
                    responses.setdefault(
                        "403", {"description": "Origin is not trusted"}
                    )
                if "/market-analyses" in path:
                    operation["description"] = (
                        operation.get("description", "")
                        + "\n\nStatuses: pending, processing, completed, failed. "
                        "Requests return 503 while the processor is unavailable."
                    ).strip()
                    if method == "post":
                        responses.setdefault(
                            "503",
                            {
                                "description": "Market processor unavailable",
                                "content": {
                                    "application/json": {
                                        "example": {
                                            "detail": (
                                                "Market analysis service "
                                                "is not configured"
                                            )
                                        }
                                    }
                                },
                            },
                        )
                if "/analyses" in path:
                    if method == "post":
                        responses.setdefault(
                            "503",
                            {"description": "Image analysis processing is unavailable"},
                        )
                    if method == "post" and "202" in responses:
                        responses["202"].setdefault("content", {}).setdefault(
                            "application/json", {}
                        )["example"] = {
                            "id": 42,
                            "product_id": 7,
                            "original_image_id": 11,
                            "language": "en",
                            "status": "pending",
                            "analysis_result": None,
                            "error_message": None,
                            "created_at": "2025-11-20T12:00:00Z",
                            "updated_at": "2025-11-20T12:00:00Z",
                            "completed_at": None,
                            "processing_available": True,
                            "image_revision": "a" * 64,
                            "is_current_image": True,
                        }
                    operation["description"] = (
                        operation.get("description", "")
                        + "\n\nStatuses: pending, processing, completed, failed. "
                        "New requests return 503 until processing is connected. "
                        "Accepted requests have processing_available=true. "
                        "Historical revisions have is_current_image=false; "
                        "null means the legacy revision is unknown."
                    ).strip()
                if "/variants" in path:
                    if method == "post" and path.endswith("/variants"):
                        responses.setdefault(
                            "503",
                            {"description": "Platform generation unavailable"},
                        )
                    operation["description"] = (
                        operation.get("description", "")
                        + "\n\nStatuses: pending, processing, ready, failed. "
                        "Generation returns 503 until durable processing is connected; "
                        "seller-written variants remain available."
                    ).strip()
        return schema

    application.openapi = documented_openapi

    @application.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"message": "Welcome to Buyora API"}

    return application
