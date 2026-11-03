"""Application entry points."""

import uvicorn

from snappe.adapters.http import create_app


def run() -> None:
    """Run the HTTP application."""
    uvicorn.run("snappe.adapters.http:app", host="0.0.0.0", port=8000, reload=False)


app = create_app()
