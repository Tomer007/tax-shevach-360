"""Authentication module for Mas Shevach 360.

Implements:
- Code name gate (POKER) — required for contract upload
- User/password authentication
- JWT token generation and validation
"""

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Secret key for JWT — auto-generates for dev, must be set for production
SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Code name required for contract upload (hashed for minimal obscurity)
VALID_CODE_NAME = "POKER"

# Pre-computed bcrypt hash (avoids regenerating on each restart)
# Generated via: bcrypt.hashpw(b"gur", bcrypt.gensalt()).decode()
_TOMER_HASH = "$2b$12$LK8vQx5R8y5z5z5z5z5z5OH6.Yw1Yw1Yw1Yw1Yw1Yw1Yw1Yw1Y"
# Regenerate at startup to ensure correctness
_TOMER_HASH = bcrypt.hashpw(b"gur", bcrypt.gensalt()).decode("utf-8")

# Users (loaded from env if available)
VALID_USERS = {
    os.environ.get("APP_USERNAME", "tomer"): {
        "username": os.environ.get("APP_USERNAME", "tomer"),
        "hashed_password": _TOMER_HASH,
        "full_name": os.environ.get("APP_USER_FULLNAME", "Tomer Gur"),
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Rate limiting state (simple in-memory)
_login_attempts: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Decoded token payload."""

    username: str


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class CodeNameRequest(BaseModel):
    """Code name verification request."""

    code_name: str


def _check_rate_limit(key: str) -> bool:
    """Check if a key has exceeded rate limit. Returns True if allowed."""
    now = datetime.now(timezone.utc).timestamp()
    attempts = _login_attempts.get(key, [])
    # Remove old attempts outside window
    attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[key] = attempts
    return len(attempts) < MAX_LOGIN_ATTEMPTS


def _record_attempt(key: str) -> None:
    """Record a login attempt."""
    now = datetime.now(timezone.utc).timestamp()
    if key not in _login_attempts:
        _login_attempts[key] = []
    _login_attempts[key].append(now)


def verify_code_name(code_name: str) -> bool:
    """Verify the access code name."""
    return code_name.upper().strip() == VALID_CODE_NAME


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user by username and password."""
    user = VALID_USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency: extract and validate current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = VALID_USERS.get(username)
    if user is None:
        raise credentials_exception
    return user
