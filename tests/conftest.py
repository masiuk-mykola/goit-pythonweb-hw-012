import os

# Налаштування мають бути в оточенні до імпорту застосунку
os.environ.update(
    {
        "DB_URL": "sqlite+aiosqlite:///:memory:",
        "JWT_SECRET": "test-secret-key-that-is-at-least-32-bytes",
        "MAIL_FROM": "noreply@example.com",
        "CLD_NAME": "test",
        "CLD_API_KEY": "test",
        "CLD_API_SECRET": "test",
        "REDIS_URL": "redis://localhost:6379/15",
    }
)

from unittest.mock import AsyncMock  # noqa: E402

import fakeredis  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from main import app  # noqa: E402
from src.database.db import get_db  # noqa: E402
from src.database.models import Base, User, UserRole  # noqa: E402
from src.services.auth import Hash, create_access_token  # noqa: E402
from src.services.cache import get_redis  # noqa: E402
from src.services.limiter import limiter  # noqa: E402

TEST_PASSWORD = "12345678"

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    """Fresh schema for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def redis_client():
    r = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture(autouse=True)
def mock_emails(monkeypatch):
    """Replace email senders with mocks so tests never talk to SMTP."""
    verification = AsyncMock()
    reset = AsyncMock()
    monkeypatch.setattr("src.api.auth.send_verification_email", verification)
    monkeypatch.setattr("src.api.auth.send_reset_password_email", reset)
    return {"verification": verification, "reset": reset}


@pytest_asyncio.fixture
async def client(redis_client):
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    limiter.enabled = False
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    limiter.enabled = True


async def _create_user(
    session, username: str, email: str, role: UserRole, confirmed: bool = True
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=Hash().get_password_hash(TEST_PASSWORD),
        confirmed=confirmed,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user(db_session) -> User:
    return await _create_user(db_session, "deadpool", "deadpool@example.com", UserRole.USER)


@pytest_asyncio.fixture
async def admin(db_session) -> User:
    return await _create_user(db_session, "admin", "admin@example.com", UserRole.ADMIN)


@pytest.fixture
def user_headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user.username})}"}


@pytest.fixture
def admin_headers(admin) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': admin.username})}"}
