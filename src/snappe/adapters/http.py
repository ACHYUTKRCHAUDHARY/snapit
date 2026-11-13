"""HTTP adapter and operational endpoints."""

from collections.abc import Mapping

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import Response

from snappe.adapters.database import Database
from snappe.config import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Create the FastAPI application with validated runtime dependencies."""
    runtime_settings = settings or get_settings()
    runtime_database = database or Database(runtime_settings)
    application = FastAPI(title="Snappe.ai", version="0.1.0")

    @application.get("/healthz", tags=["system"])
    async def healthz() -> Mapping[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", tags=["system"])
    async def readyz() -> Response:
        try:
            runtime_database.check_connection()
        except SQLAlchemyError:
            return Response(
                content='{"status":"not_ready","dependency":"database"}',
                status_code=503,
                media_type="application/json",
            )
        return Response(content='{"status":"ready"}', media_type="application/json")

    @application.get("/metrics", tags=["system"], include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return application


app = create_app()
