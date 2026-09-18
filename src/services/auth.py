"""Authentication: password hashing, JWT tokens and current-user dependencies.

All tokens are signed JWTs with a ``scope`` claim so that a token issued for
one purpose (e.g. email verification) cannot be used for another (e.g. API
access).
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import config
from src.database.db import get_db
from src.database.models import User, UserRole
from src.services.cache import cache_user, get_cached_user, get_redis
from src.services.users import UserService

ACCESS_SCOPE = "access_token"
REFRESH_SCOPE = "refresh_token"
EMAIL_SCOPE = "email_verification"
RESET_SCOPE = "password_reset"


class Hash:
    """Password hashing helper (Argon2 via ``pwdlib``)."""

    password_hash = PasswordHash.recommended()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Check a plain password against a stored hash.

        Args:
            plain_password: Password entered by the user.
            hashed_password: Hash stored in the database.

        Returns:
            bool: ``True`` if the password matches.
        """
        return self.password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a plain password.

        Args:
            password: Plain password.

        Returns:
            str: Argon2 hash.
        """
        return self.password_hash.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _create_token(data: dict, scope: str, expires_in: int) -> str:
    now = datetime.now(UTC)
    to_encode = {
        **data,
        "scope": scope,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _decode_token(token: str, scope: str) -> dict | None:
    """Decode a token and check its scope.

    Returns:
        dict | None: Payload, or ``None`` if the token is invalid, expired,
        has another scope or no ``sub`` claim.
    """
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
    except InvalidTokenError:
        return None
    if payload.get("scope") != scope or payload.get("sub") is None:
        return None
    return payload


def create_access_token(data: dict) -> str:
    """Create a short-lived access token.

    Args:
        data: Claims to include, normally ``{"sub": username}``.

    Returns:
        str: Encoded JWT valid for ``JWT_EXPIRATION_SECONDS``.
    """
    return _create_token(data, ACCESS_SCOPE, config.JWT_EXPIRATION_SECONDS)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token.

    Args:
        data: Claims to include, normally ``{"sub": username}``.

    Returns:
        str: Encoded JWT valid for ``REFRESH_TOKEN_EXPIRATION_SECONDS``.
    """
    return _create_token(data, REFRESH_SCOPE, config.REFRESH_TOKEN_EXPIRATION_SECONDS)


def create_email_token(data: dict) -> str:
    """Create an email verification token.

    Args:
        data: Claims to include, normally ``{"sub": email}``.

    Returns:
        str: Encoded JWT valid for ``EMAIL_TOKEN_EXPIRATION_SECONDS``.
    """
    return _create_token(data, EMAIL_SCOPE, config.EMAIL_TOKEN_EXPIRATION_SECONDS)


def password_fingerprint(hashed_password: str) -> str:
    """Short fingerprint of a password hash embedded in reset tokens.

    Once the password changes the fingerprint no longer matches, so a reset
    token can be used only once.

    Args:
        hashed_password: Current password hash.

    Returns:
        str: First 16 hex chars of SHA-256 of the hash.
    """
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def create_reset_token(email: str, hashed_password: str) -> str:
    """Create a single-use password reset token.

    Args:
        email: Email of the user resetting the password.
        hashed_password: Current password hash of the user.

    Returns:
        str: Encoded JWT valid for ``RESET_TOKEN_EXPIRATION_SECONDS``.
    """
    return _create_token(
        {"sub": email, "pwd": password_fingerprint(hashed_password)},
        RESET_SCOPE,
        config.RESET_TOKEN_EXPIRATION_SECONDS,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
) -> User:
    """FastAPI dependency returning the user authenticated by the access token.

    The user is read from the Redis cache when present; otherwise it is loaded
    from the database and cached.

    Args:
        token: Bearer access token.
        db: Database session.
        r: Redis client.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: 401 if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = _decode_token(token, ACCESS_SCOPE)
    if payload is None:
        raise credentials_exception
    username = payload["sub"]

    user = await get_cached_user(r, username)
    if user is not None:
        return user

    user = await UserService(db).get_user_by_username(username)
    if user is None:
        raise credentials_exception
    await cache_user(r, user)
    return user


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency allowing only users with the ``admin`` role.

    Args:
        user: The authenticated user.

    Returns:
        User: The same user if they are an admin.

    Raises:
        HTTPException: 403 if the user is not an admin.
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user


async def verify_refresh_token(token: str, db: AsyncSession) -> User | None:
    """Validate a refresh token against the one stored for the user.

    Args:
        token: Refresh token sent by the client.
        db: Database session.

    Returns:
        User | None: Owner of the token, or ``None`` if the token is invalid,
        expired or was already rotated/revoked.
    """
    payload = _decode_token(token, REFRESH_SCOPE)
    if payload is None:
        return None
    user = await UserService(db).get_user_by_username(payload["sub"])
    if user is None or user.refresh_token != token:
        return None
    return user


def get_email_from_token(token: str) -> str:
    """Extract the email from an email verification token.

    Args:
        token: Email verification token.

    Returns:
        str: Email address.

    Raises:
        HTTPException: 422 if the token is invalid or has another scope.
    """
    payload = _decode_token(token, EMAIL_SCOPE)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid email verification token",
        )
    return payload["sub"]


def get_reset_token_payload(token: str) -> tuple[str, str]:
    """Extract the email and password fingerprint from a reset token.

    Args:
        token: Password reset token.

    Returns:
        tuple[str, str]: ``(email, password_fingerprint)``.

    Raises:
        HTTPException: 400 if the token is invalid, expired or has another scope.
    """
    payload = _decode_token(token, RESET_SCOPE)
    if payload is None or payload.get("pwd") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return payload["sub"], payload["pwd"]
