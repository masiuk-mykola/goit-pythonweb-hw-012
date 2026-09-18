from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repo(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, username="testuser")


@pytest.fixture
def contact_body():
    return ContactModel(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone_number="0501234567",
        dob=date(1990, 5, 17),
    )


def _result(scalar=None, scalars=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value.all.return_value = scalars or []
    return result


async def test_get_contacts(repo, mock_session, user):
    contacts = [Contact(id=1, first_name="John", user_id=1)]
    mock_session.execute = AsyncMock(return_value=_result(scalars=contacts))

    result = await repo.get_contacts(user, skip=0, limit=10)

    mock_session.execute.assert_awaited_once()
    assert result == contacts


async def test_get_contacts_with_all_filters(repo, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_result(scalars=[]))

    result = await repo.get_contacts(
        user,
        contact_first_name="John",
        contact_last_name="Doe",
        contact_email="JOHN@example.com",
        days_to_birthday=7,
    )

    query = mock_session.execute.await_args.args[0]
    sql = str(query.compile(compile_kwargs={"literal_binds": False}))
    assert "lower(contacts.first_name)" in sql
    assert "lower(contacts.last_name)" in sql
    assert "lower(contacts.email)" in sql
    assert result == []


async def test_get_contact_by_id(repo, mock_session, user):
    contact = Contact(id=1, first_name="John", user_id=1)
    mock_session.execute = AsyncMock(return_value=_result(scalar=contact))

    assert await repo.get_contact_by_id(1, user) is contact


async def test_get_contact_by_id_not_found(repo, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_result(scalar=None))

    assert await repo.get_contact_by_id(999, user) is None


async def test_create_contact(repo, mock_session, user, contact_body):
    result = await repo.create_contact(contact_body, user)

    assert isinstance(result, Contact)
    assert result.first_name == "John"
    assert result.user_id == user.id
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


async def test_update_contact(repo, mock_session, user, contact_body):
    existing = Contact(id=1, first_name="Old", last_name="Name", user_id=1)
    mock_session.execute = AsyncMock(return_value=_result(scalar=existing))

    result = await repo.update_contact(1, contact_body, user)

    assert result is existing
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing)


async def test_update_contact_not_found(repo, mock_session, user, contact_body):
    mock_session.execute = AsyncMock(return_value=_result(scalar=None))

    assert await repo.update_contact(1, contact_body, user) is None
    mock_session.commit.assert_not_awaited()


async def test_remove_contact(repo, mock_session, user):
    existing = Contact(id=1, first_name="John", user_id=1)
    mock_session.execute = AsyncMock(return_value=_result(scalar=existing))

    result = await repo.remove_contact(1, user)

    assert result is existing
    mock_session.delete.assert_awaited_once_with(existing)
    mock_session.commit.assert_awaited_once()


async def test_remove_contact_not_found(repo, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_result(scalar=None))

    assert await repo.remove_contact(1, user) is None
    mock_session.delete.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


async def test_get_contacts_by_ids(repo, mock_session, user):
    contacts = [Contact(id=1, user_id=1), Contact(id=2, user_id=1)]
    mock_session.execute = AsyncMock(return_value=_result(scalars=contacts))

    assert await repo.get_contacts_by_ids([1, 2], user) == contacts


async def test_get_contact_by_contact_info(repo, mock_session, user):
    contact = Contact(id=1, first_name="john", user_id=1)
    mock_session.execute = AsyncMock(return_value=_result(scalar=contact))

    assert await repo.get_contact_by_contact_info("John", user) is contact
