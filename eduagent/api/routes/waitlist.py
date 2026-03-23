"""Waitlist / email capture routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from eduagent.waitlist import WaitlistManager

router = APIRouter(tags=["waitlist"])


def _get_wl() -> WaitlistManager:
    return WaitlistManager()


class SignupRequest(BaseModel):
    email: str
    role: str = "teacher"
    notes: str = ""


@router.post("/waitlist")
async def add_signup(req: SignupRequest):
    """Add an email to the early access waitlist."""
    wl = _get_wl()
    try:
        wl.add_signup(req.email, req.role, req.notes)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        wl.close()
    wl2 = _get_wl()
    count = wl2.count()
    wl2.close()
    return {"ok": True, "count": count}


@router.get("/waitlist/count")
async def waitlist_count():
    """Return the current waitlist signup count."""
    wl = _get_wl()
    count = wl.count()
    wl.close()
    return {"count": count}
