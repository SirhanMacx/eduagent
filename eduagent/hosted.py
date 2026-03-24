"""Hosted (multi-tenant) version of the EDUagent FastAPI app.

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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from eduagent.auth import APIKeyAuthMiddleware

logger = logging.getLogger(__name__)


def create_hosted_app() -> FastAPI:
    """Create a hosted, multi-tenant FastAPI app wrapping the core EDUagent server.

    Returns a FastAPI instance configured with:
    - API key authentication middleware
    - CORS for web clients
    - Health check endpoint at /health
    - All existing API routes from the core server
    """
    from eduagent.api.server import app as base_app, lifespan

    hosted = FastAPI(
        title="EDUagent Hosted API",
        description="Multi-tenant hosted version of EDUagent",
        version="0.1.3",
        lifespan=lifespan,
    )

    # CORS — allow all origins for web client access
    hosted.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API key auth — exempt health check and docs
    hosted.add_middleware(
        APIKeyAuthMiddleware,
        exempt_paths=["/health", "/docs", "/openapi.json", "/redoc"],
    )

    # Health check endpoint (no auth required)
    @hosted.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint for load balancers and monitoring."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "eduagent",
                "version": "0.1.3",
            }
        )

    # Mount all routes from the base app
    for route in base_app.routes:
        hosted.routes.append(route)

    return hosted


# Module-level app instance for uvicorn
app = create_hosted_app()
