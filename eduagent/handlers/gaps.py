"""Curriculum gap analysis handler. Extracted from tg.py lines 1030-1127."""
from __future__ import annotations
import logging
from eduagent.gateway_response import GatewayResponse
from eduagent.openclaw_plugin import handle_message

logger = logging.getLogger(__name__)

class GapsHandler:
    async def analyze(self, teacher_id: str) -> GatewayResponse:
        try:
            response = await handle_message("curriculum gap analysis", teacher_id=teacher_id)
            return GatewayResponse(text=response)
        except Exception as e:
            logger.error("Gap analysis failed: %s", e)
            return GatewayResponse(text="Gap analysis failed. Make sure you have lessons and standards configured.")
