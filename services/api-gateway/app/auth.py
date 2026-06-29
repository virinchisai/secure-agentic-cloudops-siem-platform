"""Authentication utilities: JWT, password hashing, users, roles."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Roles & permissions
# ---------------------------------------------------------------------------

class Role(str, Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


# Maps each role to the set of HTTP methods it may use.
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.admin: {"GET", "POST", "PUT", "DELETE", "PATCH"},
    Role.analyst: {"GET", "POST"},
    Role.viewer: {"GET"},
}


def check_role_permission(role: str, method: str) -> bool:
    """Return True if *role* is allowed to use *method*."""
    try:
        r = Role(role)
    except ValueError:
        return False
    return method.upper() in ROLE_PERMISSIONS.get(r, set())


# ---------------------------------------------------------------------------
# User model & demo database
# ---------------------------------------------------------------------------

class User(BaseModel):
    username: str
    hashed_password: str
    role: Role


DEMO_USERS: dict[str, User] = {
    "admin": User(
        username="admin",
        hashed_password=pwd_context.hash("admin123"),
        role=Role.admin,
    ),
    "analyst": User(
        username="analyst",
        hashed_password=pwd_context.hash("analyst123"),
        role=Role.analyst,
    ),
    "viewer": User(
        username="viewer",
        hashed_password=pwd_context.hash("viewer123"),
        role=Role.viewer,
    ),
}


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and return the payload.  Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = DEMO_USERS.get(username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
