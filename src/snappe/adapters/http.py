"""HTTP adapter and walking-skeleton endpoints."""

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    application = FastAPI(title="Snappe.ai", version="0.1.0")

    @application.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", tags=["system"])
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @application.get("/metrics", tags=["system"], include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return application


app = create_app()
