from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import config
from src.database.db import get_db
from src.database.models import User
from src.services.users import UserService

ACCESS_SCOPE = "access_token"
EMAIL_SCOPE = "email_verification"


class Hash:
    password_hash = PasswordHash.recommended()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.password_hash.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _create_token(data: dict, scope: str, expires_in: int) -> str:
    now = datetime.now(UTC)
    to_encode = {
        **data,
        "scope": scope,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def create_access_token(data: dict) -> str:
    return _create_token(data, ACCESS_SCOPE, config.JWT_EXPIRATION_SECONDS)


def create_email_token(data: dict) -> str:
    return _create_token(data, EMAIL_SCOPE, config.EMAIL_TOKEN_EXPIRATION_SECONDS)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
    except InvalidTokenError:
        raise credentials_exception
    username = payload.get("sub")
    if username is None or payload.get("scope") != ACCESS_SCOPE:
        raise credentials_exception

    user = await UserService(db).get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


def get_email_from_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid email verification token",
        )
    email = payload.get("sub")
    if email is None or payload.get("scope") != EMAIL_SCOPE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid email verification token",
        )
    return email
