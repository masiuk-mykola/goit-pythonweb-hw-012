from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repo(mock_session):
    return UserRepository(mock_session)


@pytest.fixture
def user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hash",
        confirmed=False,
        refresh_token="old-refresh",
    )


def _returns(mock_session, value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    mock_session.execute = AsyncMock(return_value=result)


@pytest.mark.parametrize(
    "method, arg",
    [
        ("get_user_by_id", 1),
        ("get_user_by_username", "testuser"),
        ("get_user_by_email", "TEST@example.com"),
    ],
)
async def test_get_user(repo, mock_session, user, method, arg):
    _returns(mock_session, user)

    assert await getattr(repo, method)(arg) is user
    mock_session.execute.assert_awaited_once()


async def test_get_user_by_email_is_case_insensitive(repo, mock_session):
    _returns(mock_session, None)

    await repo.get_user_by_email("TEST@Example.com")

    query = mock_session.execute.await_args.args[0]
    assert query.compile().params["email_1"] == "test@example.com"


async def test_create_user(repo, mock_session):
    body = UserCreate(username="newuser", email="New@Example.com", password="secret1")

    result = await repo.create_user(body, "hashed")

    assert result.username == "newuser"
    assert result.email == "new@example.com"
    assert result.hashed_password == "hashed"
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


async def test_confirmed_email(repo, mock_session, user):
    _returns(mock_session, user)

    await repo.confirmed_email(user.email)

    assert user.confirmed is True
    mock_session.commit.assert_awaited_once()


async def test_confirmed_email_unknown_user(repo, mock_session):
    _returns(mock_session, None)

    await repo.confirmed_email("nobody@example.com")

    mock_session.commit.assert_not_awaited()


async def test_update_avatar_url(repo, mock_session, user):
    _returns(mock_session, user)

    result = await repo.update_avatar_url(user.email, "http://img/avatar.png")

    assert result is user
    assert user.avatar == "http://img/avatar.png"
    mock_session.commit.assert_awaited_once()


async def test_update_avatar_url_unknown_user(repo, mock_session):
    _returns(mock_session, None)

    assert await repo.update_avatar_url("nobody@example.com", "url") is None
    mock_session.commit.assert_not_awaited()


async def test_update_refresh_token(repo, mock_session, user):
    await repo.update_refresh_token(user, "new-refresh")

    assert user.refresh_token == "new-refresh"
    mock_session.commit.assert_awaited_once()


async def test_update_password(repo, mock_session, user):
    _returns(mock_session, user)

    result = await repo.update_password(user.email, "new-hash")

    assert result is user
    assert user.hashed_password == "new-hash"
    assert user.refresh_token is None
    mock_session.commit.assert_awaited_once()


async def test_update_password_unknown_user(repo, mock_session):
    _returns(mock_session, None)

    assert await repo.update_password("nobody@example.com", "new-hash") is None
    mock_session.commit.assert_not_awaited()
