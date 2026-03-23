"""SkillLibrary — loads and resolves subject skills for prompt injection."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Iterator

from eduagent.skills.base import SubjectSkill


class SkillLibrary:
    """Registry of subject-specific pedagogy skills.

    Discovers all skill modules in the ``eduagent.skills`` package at
    instantiation time and indexes them by canonical subject name and aliases.
    """

    def __init__(self) -> None:
        self._skills: dict[str, SubjectSkill] = {}
        self._alias_map: dict[str, str] = {}
        self._load_all()

    # ── Discovery ──────────────────────────────────────────────────────

    def _load_all(self) -> None:
        """Walk ``eduagent.skills`` and import every module that exposes a ``skill`` attribute."""
        package_dir = Path(__file__).parent
        for info in pkgutil.iter_modules([str(package_dir)]):
            if info.name in ("base", "library", "__init__"):
                continue
            mod = importlib.import_module(f"eduagent.skills.{info.name}")
            skill: SubjectSkill | None = getattr(mod, "skill", None)
            if skill is None:
                continue
            self._skills[skill.subject] = skill
            # Register aliases
            for alias in skill.aliases:
                self._alias_map[alias.lower()] = skill.subject

    # ── Lookup ─────────────────────────────────────────────────────────

    def get(self, subject: str) -> SubjectSkill | None:
        """Resolve a subject name (or alias) to a SubjectSkill, or ``None``."""
        key = subject.lower().strip()
        # Direct match
        if key in self._skills:
            return self._skills[key]
        # Alias match
        canonical = self._alias_map.get(key)
        if canonical:
            return self._skills[canonical]
        return None

    def list_skills(self) -> list[SubjectSkill]:
        """Return all registered skills sorted by display name."""
        return sorted(self._skills.values(), key=lambda s: s.display_name)

    def subjects(self) -> list[str]:
        """Return canonical subject keys."""
        return sorted(self._skills.keys())

    def __iter__(self) -> Iterator[SubjectSkill]:
        return iter(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, subject: str) -> bool:
        return self.get(subject) is not None

    # ── Prompt injection helpers ───────────────────────────────────────

    def inject_system_context(self, subject: str) -> str:
        """Return the full system context block for *subject*, or empty string."""
        skill = self.get(subject)
        return skill.to_system_context() if skill else ""

    def inject_lesson_context(self, subject: str) -> str:
        """Return the compact lesson injection for *subject*, or empty string."""
        skill = self.get(subject)
        return skill.to_lesson_injection() if skill else ""
