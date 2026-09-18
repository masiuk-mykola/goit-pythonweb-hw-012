from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError

from src.conf.config import config
from src.database.models import User, UserRole
from src.services import auth
from src.services.cache import cache_user, get_cached_user, invalidate_user


@pytest.fixture
def db_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hash",
        avatar=None,
        confirmed=True,
        role=UserRole.USER,
    )


def test_hash_roundtrip():
    hasher = auth.Hash()
    hashed = hasher.get_password_hash("secret")

    assert hasher.verify_password("secret", hashed)
    assert not hasher.verify_password("wrong", hashed)


def test_tokens_have_their_own_scopes():
    access = auth.create_access_token({"sub": "u"})
    refresh = auth.create_refresh_token({"sub": "u"})

    assert auth._decode_token(access, auth.ACCESS_SCOPE)["sub"] == "u"
    assert auth._decode_token(refresh, auth.REFRESH_SCOPE)["sub"] == "u"
    assert auth._decode_token(refresh, auth.ACCESS_SCOPE) is None
    assert auth._decode_token("garbage", auth.ACCESS_SCOPE) is None


def test_tokens_are_unique():
    assert auth.create_refresh_token({"sub": "u"}) != auth.create_refresh_token(
        {"sub": "u"}
    )


def test_get_email_from_token():
    token = auth.create_email_token({"sub": "a@example.com"})

    assert auth.get_email_from_token(token) == "a@example.com"


def test_get_email_from_token_rejects_access_token():
    with pytest.raises(HTTPException) as exc:
        auth.get_email_from_token(auth.create_access_token({"sub": "a@example.com"}))
    assert exc.value.status_code == 422


def test_reset_token_payload():
    token = auth.create_reset_token("a@example.com", "hash")

    email, fingerprint = auth.get_reset_token_payload(token)

    assert email == "a@example.com"
    assert fingerprint == auth.password_fingerprint("hash")
    assert fingerprint != auth.password_fingerprint("other-hash")


def test_reset_token_payload_invalid():
    token = jwt.encode(
        {"sub": "a@example.com", "scope": auth.RESET_SCOPE},
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        auth.get_reset_token_payload(token)
    assert exc.value.status_code == 400


async def test_get_current_user_loads_from_db_and_caches(redis_client, db_user):
    token = auth.create_access_token({"sub": db_user.username})
    with patch.object(
        auth.UserService, "get_user_by_username", AsyncMock(return_value=db_user)
    ) as get_user:
        first = await auth.get_current_user(token, AsyncMock(), redis_client)
        second = await auth.get_current_user(token, AsyncMock(), redis_client)

    get_user.assert_awaited_once()  # другий виклик узяв користувача з кешу
    assert first is db_user
    assert second.id == db_user.id
    assert second.role == UserRole.USER
    assert await redis_client.get("user:testuser") is not None


async def test_get_current_user_invalid_token(redis_client):
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user("bad-token", AsyncMock(), redis_client)
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_user(redis_client):
    token = auth.create_access_token({"sub": "ghost"})
    with patch.object(
        auth.UserService, "get_user_by_username", AsyncMock(return_value=None)
    ):
        with pytest.raises(HTTPException) as exc:
            await auth.get_current_user(token, AsyncMock(), redis_client)
    assert exc.value.status_code == 401


async def test_get_current_admin_user(db_user):
    db_user.role = UserRole.ADMIN
    assert await auth.get_current_admin_user(db_user) is db_user


async def test_get_current_admin_user_forbidden(db_user):
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_admin_user(db_user)
    assert exc.value.status_code == 403


async def test_verify_refresh_token(db_user):
    token = auth.create_refresh_token({"sub": db_user.username})
    db_user.refresh_token = token
    with patch.object(
        auth.UserService, "get_user_by_username", AsyncMock(return_value=db_user)
    ):
        assert await auth.verify_refresh_token(token, AsyncMock()) is db_user

        db_user.refresh_token = "rotated"
        assert await auth.verify_refresh_token(token, AsyncMock()) is None

    assert await auth.verify_refresh_token("garbage", AsyncMock()) is None


async def test_cache_roundtrip_and_invalidate(redis_client, db_user):
    await cache_user(redis_client, db_user)

    cached = await get_cached_user(redis_client, db_user.username)
    assert cached.email == db_user.email
    assert cached.hashed_password is None  # хеш пароля не кешується

    await invalidate_user(redis_client, db_user.username)
    assert await get_cached_user(redis_client, db_user.username) is None


async def test_cache_survives_redis_errors(db_user):
    broken = AsyncMock()
    broken.get.side_effect = RedisError("down")
    broken.set.side_effect = RedisError("down")
    broken.delete.side_effect = RedisError("down")

    assert await get_cached_user(broken, "testuser") is None
    await cache_user(broken, db_user)
    await invalidate_user(broken, "testuser")
