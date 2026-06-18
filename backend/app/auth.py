"""Authentication module for Mas Shevach 360.

Implements:
- Code name gate (POKER) — required before login
- User/password authentication (tomer/gur)
- JWT token generation and validation
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Secret key for JWT (use env var in production)
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "mas-shevach-360-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Code name required to access the system
VALID_CODE_NAME = "POKER"

# Hash the password at module level
_TOMER_HASH = bcrypt.hashpw(b"gur", bcrypt.gensalt()).decode("utf-8")

# Hardcoded user for this app
VALID_USERS = {
    "tomer": {
        "username": "tomer",
        "hashed_password": _TOMER_HASH,
        "full_name": "Tomer Gur",
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
