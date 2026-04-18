from fastapi import FastAPI

from app.api.routes.health_routes import router as health_router
from app.core.config import get_settings


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
    )

    application.include_router(health_router)

    return application


app = create_app()

