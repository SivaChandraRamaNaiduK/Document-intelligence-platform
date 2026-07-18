"""
Password hashing and JWT token creation/validation.

Passwords are hashed with bcrypt (via passlib) — never stored or compared
in plain text. Tokens are signed with HS256 using JWT_SECRET_KEY from .env.

Two token types:
- access token: short-lived (15 min default), sent on every request
- refresh token: longer-lived (7 days default), used only to get a new
  access token without forcing the user to log in again
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: uuid.UUID, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),      # "subject" = the user id this token belongs to
        "type": token_type,
        "iat": now,                # issued-at
        "exp": now + expires_delta,  # expiry
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> dict:
    """
    Decodes and validates a token's signature and expiry.
    Raises jose.JWTError if the token is invalid, tampered with, or expired.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])