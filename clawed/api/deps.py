"""Shared dependencies for API routes — breaks the server <-> routes circular import.

Route modules import get_db from here (not from server.py).
server.py also imports from here for its lifespan handler.
"""
from __future__ import annotations

from clawed.database import Database


class _NoOpLimiter:
    """No-op rate limiter. Personal agent doesn't need rate limiting."""

    def limit(self, *args, **kwargs):
        """Return a decorator that does nothing."""
        def decorator(func):
            return func
        return decorator


limiter = _NoOpLimiter()

# Shared database connection
_db: Database | None = None


def get_db() -> Database:
    """Get or create the shared Database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def set_db(db: Database | None) -> None:
    """Set the shared Database instance (used by lifespan handler)."""
    global _db
    _db = db
