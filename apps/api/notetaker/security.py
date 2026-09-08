from hashlib import sha256
from hmac import compare_digest
from fastapi import HTTPException, Request
from .models import Session, now


def digest(value: str):
    return sha256(value.encode()).hexdigest()


def error(status: int, code: str, message: str):
    raise HTTPException(status, detail={"code": code, "message": message, "retryable": status >= 500})


def authenticate(db, token: str | None):
    session = db.get(Session, digest(token)) if token else None
    if not session or session.revoked or session.expires_at <= now():
        error(401, "session_required", "Reopen your workspace to continue.")
    return session


def mutation(request: Request, session: Session | None = None):
    if request.headers.get("origin") != request.app.state.settings.web_origin:
        error(403, "origin_rejected", "This request did not come from your workspace.")
    if session and not compare_digest(digest(request.headers.get("x-csrf-token", "")), session.csrf_hash):
        error(403, "csrf_rejected", "Refresh your workspace and try again.")
