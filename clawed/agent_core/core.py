"""Agent-first Gateway — control-plane pre-router + agent loop.

This replaces the legacy intent-router Gateway with an agent loop.
Deterministic paths (file ingestion, onboarding, approval callbacks)
are handled without touching the LLM. Only natural-language messages
go through the agent tool-use loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from clawed._legacy_gateway import ActivityEvent, GatewayStats
from clawed.agent_core.approvals import ApprovalManager
from clawed.agent_core.context import AgentContext
from clawed.agent_core.loop import LLMInterface, run_agent_loop
from clawed.agent_core.prompt import build_system_prompt
from clawed.agent_core.tools.base import ToolRegistry
from clawed.config import has_config
from clawed.gateway_response import GatewayResponse
from clawed.models import AppConfig

logger = logging.getLogger(__name__)


class _LLMClientAdapter:
    """Adapts the existing clawed.agent module's LLM calling to LLMInterface.

    Instead of re-implementing API calls, wraps the existing
    ``_call_with_native_tools`` / ``_call_with_ollama_tools`` functions
    from ``clawed.agent``.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str = "",
    ) -> dict[str, Any]:
        # The legacy agent functions operate on the global TOOL_DEFINITIONS.
        # We temporarily monkey-patch them so the registry schemas are used
        # instead. Since these functions read TOOL_DEFINITIONS at call time,
        # we swap the module-level list.
        import clawed.agent as _agent_mod
        from clawed.agent import _call_with_native_tools, _call_with_ollama_tools
        from clawed.models import LLMProvider

        original_defs = _agent_mod.TOOL_DEFINITIONS
        _agent_mod.TOOL_DEFINITIONS = tools or []
        try:
            if self._config.provider in (LLMProvider.ANTHROPIC, LLMProvider.OPENAI):
                return await _call_with_native_tools(messages, system, self._config)
            else:
                return await _call_with_ollama_tools(messages, system, self._config)
        finally:
            _agent_mod.TOOL_DEFINITIONS = original_defs


class Gateway:
    """Agent-first Gateway — sits behind the feature-flag shim."""

    def __init__(self, config: Optional[AppConfig] = None, llm: Optional[LLMInterface] = None):
        self.config = config or AppConfig.load()
        self.event_bus: asyncio.Queue[ActivityEvent] = asyncio.Queue(maxsize=500)
        self.active_sessions: dict[str, dict] = {}
        self._stats = GatewayStats()
        self._running = False
        self._llm = llm  # Injectable for testing

        # Control-plane handlers (reuse existing deterministic handlers)
        from clawed.handlers.ingest import IngestHandler
        from clawed.handlers.onboard import OnboardHandler

        self._ingest = IngestHandler()
        self._onboard = OnboardHandler()

        # Agent subsystems
        self._approval_manager = ApprovalManager()
        self._registry = ToolRegistry()
        self._registry.discover(Path(__file__).parent / "tools")

        # Load custom teacher tools from ~/.eduagent/tools/
        import os

        custom_tools_dir = Path(
            os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent"))
        ) / "tools"
        self._registry.discover_custom(custom_tools_dir)

        # Callback handlers for deterministic paths
        from clawed.handlers.export import ExportHandler
        from clawed.handlers.feedback import FeedbackHandler

        self._export = ExportHandler()
        self._feedback = FeedbackHandler()

    # ------------------------------------------------------------------
    # Public interface (matches legacy Gateway exactly)
    # ------------------------------------------------------------------

    async def handle(
        self,
        message: str,
        teacher_id: str,
        files: list[Path] | None = None,
    ) -> GatewayResponse:
        """Process any message from any transport."""
        self._stats.messages_today += 1
        self.active_sessions[teacher_id] = {
            "last_activity": datetime.now().isoformat(),
        }
        await self.emit("message_received", {
            "teacher_id": teacher_id,
            "text": message[:200],
        })

        try:
            # 1. Files → ingest (deterministic, no LLM)
            if files:
                return await self._ingest.handle(teacher_id, files)

            # 2. Onboarding state machine (deterministic, no LLM)
            if self._onboard.is_onboarding(teacher_id):
                return await self._onboard.step(teacher_id, message)

            # 3. First-run detection
            if not has_config():
                return await self._onboard.step(teacher_id, message)

            # 4. Natural-language → agent loop
            return await self._agent_loop(message, teacher_id)

        except Exception as e:
            logger.error("Gateway error: %s", e)
            self._stats.errors_today += 1
            await self.emit("error", {"teacher_id": teacher_id, "message": str(e)})
            return GatewayResponse(
                text="I ran into an issue processing that. Please try again."
            )

    async def handle_callback(self, callback_data: str, teacher_id: str) -> GatewayResponse:
        """Handle button press callbacks (approval, rate, export, etc.)."""
        parts = callback_data.split(":")

        # Approval callbacks
        if parts[0] == "approve" and len(parts) >= 2:
            approval_id = parts[1]
            pa = self._approval_manager.approve(approval_id)
            if pa:
                return GatewayResponse(text=f"Approved: {pa.action_description}")
            return GatewayResponse(text="Approval not found or already processed.")

        if parts[0] == "reject" and len(parts) >= 2:
            approval_id = parts[1]
            pa = self._approval_manager.reject(approval_id)
            if pa:
                return GatewayResponse(text=f"Rejected: {pa.action_description}")
            return GatewayResponse(text="Approval not found or already processed.")

        # Legacy rating callbacks
        if parts[0] == "rate" and len(parts) >= 3:
            lesson_id = parts[1]
            rating_str = parts[2]
            if rating_str == "0_prompt":
                return self._feedback.rating_prompt(lesson_id)
            try:
                rating = int(rating_str)
            except ValueError:
                return GatewayResponse(text="Invalid rating.")
            return await self._feedback.rate(lesson_id, teacher_id, rating)

        # Legacy action callbacks
        if parts[0] == "action" and len(parts) >= 3:
            action = parts[1]
            lesson_id = parts[2]
            if action.startswith("export_"):
                fmt = action.replace("export_", "")
                return await self._export.export(lesson_id, teacher_id, fmt)

        return GatewayResponse(text="Unknown action.")

    async def stats(self) -> dict:
        """Return live stats. Kept async for backward compat."""
        s = self._stats
        return {
            "messages_today": s.messages_today,
            "generations_today": s.generations_today,
            "errors_today": s.errors_today,
            "uptime_seconds": s.uptime_seconds,
            "active_sessions": len(self.active_sessions),
        }

    async def emit(self, event_type: str, data: dict | None = None) -> None:
        """Emit an event for TUI consumption. Public for backward compat."""
        event = ActivityEvent(
            timestamp=time.time(),
            event_type=event_type,
            actor=data.get("teacher_id", "system") if data else "system",
            message=data.get("text", data.get("message", event_type)) if data else event_type,
            data=data or {},
        )
        if self.event_bus.full():
            try:
                self.event_bus.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.event_bus.put(event)

    # Backward compatibility methods

    async def process_message(
        self, text: str, teacher_id: str = "cli", teacher_name: str = "Teacher",
    ) -> str:
        """Backward-compatible: process message and return text string."""
        r = await self.handle(text, teacher_id)
        return r.text

    async def start(self) -> None:
        """Backward-compatible start (no-op -- transports start themselves)."""
        self._running = True
        await self.emit("system", {"message": "Gateway started"})

    async def stop(self) -> None:
        """Shut down the gateway."""
        self._running = False
        await self.emit("system", {"message": "Gateway stopped"})

    async def handle_system_event(
        self,
        event_type: str,
        teacher_id: str = "local-teacher",
        payload: dict | None = None,
    ) -> GatewayResponse:
        """Handle a system event (scheduled task, cron trigger, etc.).

        Routes through the agent loop with context about what triggered it.
        """
        await self.emit(event_type, payload or {})

        # Build a descriptive message for the agent
        task_name = (payload or {}).get("task_name", event_type)
        message = (
            f"[SYSTEM] Scheduled task '{task_name}' has fired. "
            "Check what needs to be done and take action."
        )

        try:
            return await self._agent_loop(message, teacher_id)
        except Exception as e:
            logger.error("System event handling failed: %s", e)
            return GatewayResponse(
                text=f"System event '{event_type}' received but could not be processed: {e}",
            )

    # ------------------------------------------------------------------
    # Agent loop — the core reasoning path
    # ------------------------------------------------------------------

    async def _agent_loop(self, message: str, teacher_id: str) -> GatewayResponse:
        """Load context, build prompt, and run the agent tool-use loop."""
        # 1. Load teacher context from canonical sources
        teacher_profile = self._load_teacher_profile()
        persona_dict = self._load_persona(teacher_profile)
        session_history = self._load_session_history(teacher_id)

        # 1b. Load 3-layer memory context
        from clawed.agent_core.memory.loader import load_memory_context

        memory_ctx = load_memory_context(teacher_id, message)

        teacher_name = (
            (persona_dict or {}).get("name")
            or (teacher_profile or {}).get("name")
            or "Teacher"
        )

        identity_summary = ""
        if persona_dict:
            parts = []
            if persona_dict.get("subject_area"):
                parts.append(persona_dict["subject_area"])
            if persona_dict.get("grade_levels"):
                parts.append(f"grades {', '.join(persona_dict['grade_levels'])}")
            if persona_dict.get("teaching_style"):
                style = persona_dict["teaching_style"]
                if isinstance(style, str):
                    parts.append(style.replace("_", " "))
            identity_summary = ", ".join(parts)

        # 2. Build system prompt
        system = build_system_prompt(
            teacher_name=teacher_name,
            identity_summary=memory_ctx["identity_summary"] or identity_summary,
            improvement_context=memory_ctx["improvement_context"],
            curriculum_summary=memory_ctx["curriculum_summary"],
            relevant_episodes=memory_ctx["relevant_episodes"],
            tool_names=self._registry.tool_names(),
        )

        # 3. Build AgentContext for tools
        context = AgentContext(
            teacher_id=teacher_id,
            config=self.config,
            teacher_profile=teacher_profile or {},
            persona=persona_dict,
            session_history=session_history,
            improvement_context=memory_ctx["improvement_context"],
        )

        # 4. Get or create LLM adapter
        llm = self._llm or _LLMClientAdapter(self.config)

        # 5. Run the agent loop
        await self.emit("generation_started", {
            "teacher_id": teacher_id,
            "intent": "agent_loop",
        })

        result = await run_agent_loop(
            message=message,
            system=system,
            context=context,
            llm=llm,
            registry=self._registry,
            conversation_history=session_history,
        )

        # 6. Save conversation context
        self._save_session_context(teacher_id, message, result.text)

        # 7. Store exchange as episodic memory
        try:
            from clawed.agent_core.memory.episodes import EpisodicMemory

            mem = EpisodicMemory()
            mem.store(teacher_id, f"Teacher: {message}\nClaw-ED: {result.text[:500]}")
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Context loading helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_teacher_profile() -> dict[str, Any] | None:
        """Load teacher profile from the database."""
        try:
            from clawed.database import Database
            db = Database()
            return db.get_default_teacher()
        except Exception as e:
            logger.debug("Could not load teacher profile: %s", e)
            return None

    @staticmethod
    def _load_persona(teacher_profile: dict[str, Any] | None) -> dict[str, Any] | None:
        """Parse persona from teacher profile's persona_json field."""
        if not teacher_profile or not teacher_profile.get("persona_json"):
            return None
        try:
            return json.loads(teacher_profile["persona_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("Could not parse persona_json: %s", e)
            return None

    @staticmethod
    def _load_session_history(teacher_id: str) -> list[dict[str, Any]]:
        """Load conversation history from TeacherSession."""
        try:
            from clawed.state import TeacherSession
            session = TeacherSession.load(teacher_id)
            return session.get_context_for_llm(max_turns=4)
        except Exception as e:
            logger.debug("Could not load session history: %s", e)
            return []

    @staticmethod
    def _load_improvement_context() -> str:
        """Load improvement context from the memory engine."""
        try:
            from clawed.memory_engine import build_improvement_context
            return build_improvement_context()
        except Exception as e:
            logger.debug("Could not load improvement context: %s", e)
            return ""

    @staticmethod
    def _save_session_context(teacher_id: str, user_msg: str, assistant_msg: str) -> None:
        """Save conversation turn to TeacherSession."""
        try:
            from clawed.state import TeacherSession
            session = TeacherSession.load(teacher_id)
            session.add_context("user", user_msg)
            session.add_context("assistant", assistant_msg[:500])
            session.save()
        except Exception as e:
            logger.debug("Could not save session context: %s", e)
