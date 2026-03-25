"""Shared dependencies for API routes — breaks the server <-> routes circular import.

Route modules import get_db and limiter from here (not from server.py).
server.py also imports from here for its lifespan handler.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from clawed.database import Database

# Rate limiter (shared across the app)
limiter = Limiter(key_func=get_remote_address)

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
