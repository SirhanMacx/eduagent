"""Gateway chat route — teacher chat endpoint that routes through the Gateway.

This is the HTTP interface that transports (TUI, future mobile, etc.) use to
talk to the running Claw-ED gateway. Unlike /api/chat (student chatbot),
this accepts freeform teacher messages and returns full gateway responses.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from clawed.api.deps import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])

# Module-level gateway instance — initialized on first request
_gateway = None


def _get_gateway():
    global _gateway
    if _gateway is None:
        from clawed.gateway import Gateway
        _gateway = Gateway()
    return _gateway


class GatewayChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    teacher_id: str = Field(default="local-teacher", max_length=200)


@router.post("/gateway/chat")
@limiter.limit("30/minute")
async def gateway_chat(request: Request, req: GatewayChatRequest):
    """Send a message through the Claw-ED gateway and get a response.

    This is the primary endpoint for transport clients (TUI, etc.)
    that connect to a running `clawed serve` instance.
    """
    gateway = _get_gateway()

    try:
        result = await gateway.handle(req.message, req.teacher_id)
    except Exception:
        logger.error("Gateway chat failed", exc_info=True)
        return JSONResponse(
            {"error": "Something went wrong. Please try again."},
            status_code=500,
        )

    # Serialize GatewayResponse to JSON
    buttons = []
    if result.button_rows or result.buttons:
        rows = result.button_rows or [result.buttons]
        buttons = [
            {"label": b.label, "callback_data": b.callback_data, "url": b.url}
            for row in rows
            for b in row
        ]

    return {
        "text": result.text,
        "files": [str(f) for f in result.files],
        "buttons": buttons,
    }
