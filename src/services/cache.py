"""Redis cache for authenticated users.

``get_current_user`` looks users up here first so that an authorized request
does not hit the database every time. Only non-sensitive scalar fields are
cached; the password hash and refresh token never leave the database.
"""

import json
import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from src.conf.config import config
from src.database.models import User, UserRole

logger = logging.getLogger(__name__)

redis_client: redis.Redis = redis.from_url(config.REDIS_URL, decode_responses=True)

CACHED_FIELDS = ("id", "username", "email", "avatar", "confirmed", "role")


async def get_redis() -> redis.Redis:
    """FastAPI dependency returning the shared Redis client.

    Returns:
        redis.asyncio.Redis: Client configured from ``REDIS_URL``.
    """
    return redis_client


def _user_key(username: str) -> str:
    return f"user:{username}"


async def get_cached_user(r: redis.Redis, username: str) -> User | None:
    """Return a user from the cache.

    The result is a detached :class:`~src.database.models.User` instance built
    from the cached fields; it is not attached to any database session.

    Args:
        r: Redis client.
        username: Username stored in the ``sub`` claim of the access token.

    Returns:
        User | None: Cached user, or ``None`` on a cache miss or Redis error.
    """
    try:
        raw = await r.get(_user_key(username))
    except RedisError as err:
        logger.warning("Redis unavailable, reading user from DB: %s", err)
        return None
    if raw is None:
        return None
    data = json.loads(raw)
    data["role"] = UserRole(data["role"])
    return User(**data)


async def cache_user(r: redis.Redis, user: User) -> None:
    """Store a user in the cache for ``USER_CACHE_TTL_SECONDS``.

    Args:
        r: Redis client.
        user: User loaded from the database.
    """
    data = {field: getattr(user, field) for field in CACHED_FIELDS}
    data["role"] = UserRole(data["role"]).value
    try:
        await r.set(
            _user_key(user.username),
            json.dumps(data),
            ex=config.USER_CACHE_TTL_SECONDS,
        )
    except RedisError as err:
        logger.warning("Failed to cache user %s: %s", user.username, err)


async def invalidate_user(r: redis.Redis, username: str) -> None:
    """Remove a user from the cache after their data changed.

    Args:
        r: Redis client.
        username: Username of the user to evict.
    """
    try:
        await r.delete(_user_key(username))
    except RedisError as err:
        logger.warning("Failed to invalidate cached user %s: %s", username, err)
