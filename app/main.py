from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health_routes import router as health_router
from app.core.config import get_settings
from app.db.database import create_database_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    create_database_tables()
    yield


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="MVP backend for AI-driven hazard analysis and safety risk intelligence.",
        lifespan=lifespan,
    )

    application.include_router(health_router)

    return application


app = create_app()
