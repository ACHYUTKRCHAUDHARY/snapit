"""Application entry points."""

import uvicorn
from fastapi import FastAPI

from snappe.adapters.database import Database
from snappe.adapters.http import create_app
from snappe.config import Settings
from snappe.interfaces.handover import router as handover_router
from snappe.interfaces.privacy import router as privacy_router
from snappe.interfaces.profiles import router as profiles_router
from snappe.interfaces.webhook import router as webhook_router


def run() -> None:
    """Run the HTTP application."""
    uvicorn.run("snappe.main:app", host="0.0.0.0", port=8000, reload=False)  # noqa: S104  # nosec B104


def create_full_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Create the application with all interface routers attached."""
    application = create_app(settings=settings, database=database)
    application.include_router(profiles_router)
    application.include_router(webhook_router)
    application.include_router(handover_router)
    application.include_router(privacy_router)
    return application


app = create_full_app()
