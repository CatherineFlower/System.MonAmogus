"""Authentication helpers for admin area."""

from __future__ import annotations

import hmac
import os
from hashlib import sha256

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SESSION_COOKIE_NAME = "admin_session"
SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "change-me-admin-secret")


def hash_password(password: str) -> str:
    """Hash plain text password."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check whether plain text password matches hash."""
    return pwd_context.verify(password, password_hash)


def build_session_cookie(username: str) -> str:
    """Create signed session cookie payload."""
    signature = hmac.new(SESSION_SECRET.encode(), username.encode(), sha256).hexdigest()
    return f"{username}:{signature}"


def parse_session_cookie(value: str) -> str | None:
    """Validate and parse signed session cookie payload."""
    if ":" not in value:
        return None
    username, signature = value.split(":", 1)
    expected = hmac.new(SESSION_SECRET.encode(), username.encode(), sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return username


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    """Dependency guard for protected /admin endpoints."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})

    username = parse_session_cookie(cookie)
    if not username:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})

    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    return admin


def is_admin_request(request: Request, db: Session) -> bool:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return False

    username = parse_session_cookie(cookie)
    if not username:
        return False

    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    return admin is not None


def ensure_default_admin(db: Session) -> None:
    """Create default admin account for MVP if no admin user exists."""
    existing = db.query(AdminUser).first()
    if existing:
        return

    default_admin = AdminUser(username="admin", password_hash=hash_password("admin"))
    db.add(default_admin)
    db.commit()
