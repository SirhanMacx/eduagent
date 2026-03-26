"""Autonomy progression — track approval rates and offer auto-approval."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".eduagent" / "approvals"
_MIN_SAMPLES = 10
_AUTO_THRESHOLD = 0.95

# Action types that should NEVER be auto-approved — always require teacher review.
# Student-facing output and external publishing need human oversight in education.
_NEVER_AUTO_APPROVE = {
    "student_publish",
    "student_bot_config",
    "drive_upload",
    "drive_create_slides",
    "drive_create_doc",
    "share_with_students",
}


class ApprovalTracker:
    """Tracks approval/rejection rates per action type and offers auto-approval."""

    def __init__(self, approvals_dir: Path | None = None) -> None:
        self._dir = approvals_dir or _DEFAULT_DIR

    def get_rates(self) -> dict[str, dict[str, Any]]:
        """Compute approval rates per action type from resolved approvals."""
        counts: dict[str, dict[str, int]] = defaultdict(lambda: {"approved": 0, "rejected": 0})

        if not self._dir.exists():
            return {}

        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                status = data.get("status", "")
                if status not in ("approved", "rejected"):
                    continue
                action_type = data.get("action_payload", {}).get("action_type", "unknown")
                counts[action_type][status] += 1
            except (json.JSONDecodeError, OSError):
                continue

        rates = {}
        for action_type, c in counts.items():
            total = c["approved"] + c["rejected"]
            if total > 0:
                rates[action_type] = {
                    "approval_rate": c["approved"] / total,
                    "total": total,
                    "approved": c["approved"],
                    "rejected": c["rejected"],
                }
        return rates

    def should_offer_auto(self, action_type: str) -> bool:
        """Check if an action type qualifies for auto-approval offer.

        Student-facing and external-publishing actions are never auto-approved
        regardless of approval rate — teacher review is always required.
        """
        if action_type in _NEVER_AUTO_APPROVE:
            return False
        rates = self.get_rates()
        if action_type not in rates:
            return False
        r = rates[action_type]
        return r["total"] >= _MIN_SAMPLES and r["approval_rate"] >= _AUTO_THRESHOLD

    def summarize_for_prompt(self) -> str:
        """Summarize approval patterns for the system prompt."""
        rates = self.get_rates()
        if not rates:
            return ""

        parts = []
        for action_type, r in rates.items():
            if r["total"] >= _MIN_SAMPLES:
                pct = int(r["approval_rate"] * 100)
                if r["approval_rate"] >= _AUTO_THRESHOLD:
                    parts.append(
                        f"- Teacher always approves '{action_type}' ({pct}% rate, {r['total']} samples) "
                        f"— you can offer to auto-approve this action type."
                    )
                elif r["approval_rate"] >= 0.7:
                    parts.append(
                        f"- Teacher usually approves '{action_type}' ({pct}% rate)."
                    )
                else:
                    parts.append(
                        f"- Teacher often rejects '{action_type}' ({pct}% rate) — always ask first."
                    )
        return "\n".join(parts) if parts else ""
