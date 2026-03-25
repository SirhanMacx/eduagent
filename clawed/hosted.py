"""Hosted (multi-tenant) version of the Claw-ED FastAPI app.

Wraps the core API server with:
- Multi-tenant support (teacher_id from API key auth)
- CORS for web clients
- Rate limiting (via slowapi, already in the base app)
- Health check endpoint

Run with:
    uvicorn eduagent.hosted:app --host 0.0.0.0 --port 8000

Or via the Dockerfile:
    docker build -t eduagent .
    docker run -p 8000:8000 eduagent
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from clawed.auth import APIKeyAuthMiddleware

logger = logging.getLogger(__name__)


def create_hosted_app() -> FastAPI:
    """Create a hosted, multi-tenant FastAPI app wrapping the core Claw-ED server.

    Returns a FastAPI instance configured with:
    - API key authentication middleware
    - CORS for web clients
    - Health check endpoint at /health
    - All existing API routes from the core server
    """
    from clawed import __version__
    from clawed.api.server import app as base_app
    from clawed.api.server import lifespan

    hosted = FastAPI(
        title="Claw-ED Hosted API",
        description="Multi-tenant hosted version of Claw-ED",
        version=__version__,
        lifespan=lifespan,
    )

    # CORS — configurable via EDUAGENT_CORS_ORIGINS env var.
    # Default is "*" (all origins) for development; restrict in production.
    origins = os.environ.get("EDUAGENT_CORS_ORIGINS", "*").split(",")
    hosted.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API key auth — exempt health check, docs, and web UI pages
    hosted.add_middleware(
        APIKeyAuthMiddleware,
        exempt_paths=[
            "/health", "/docs", "/openapi.json", "/redoc",
            "/", "/dashboard", "/landing", "/api/health",
        ],
    )

    # Health check endpoint (no auth required)
    @hosted.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint for load balancers and monitoring."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "eduagent",
                "version": __version__,
            }
        )

    # Mount all routes from the base app
    for route in base_app.routes:
        hosted.routes.append(route)

    return hosted


# Module-level app instance for uvicorn
app = create_hosted_app()
