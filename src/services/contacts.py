"""Business logic for contacts."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


class ContactService:
    """Thin service layer over :class:`~src.repository.contacts.ContactRepository`.

    Args:
        db: Async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession):
        self.repository = ContactRepository(db)

    async def create_contact(self, body: ContactModel, user: User):
        """Create a contact for the user."""
        return await self.repository.create_contact(body, user)

    async def get_contacts(
        self,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        days_to_birthday: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """List the user's contacts. See :meth:`ContactRepository.get_contacts`."""
        return await self.repository.get_contacts(
            user=user,
            contact_first_name=first_name,
            contact_last_name=last_name,
            contact_email=email,
            days_to_birthday=days_to_birthday,
            skip=skip,
            limit=limit,
        )

    async def get_contact(self, contact_id: int, user: User):
        """Get one of the user's contacts by ID."""
        return await self.repository.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: ContactModel, user: User):
        """Update one of the user's contacts."""
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        """Delete one of the user's contacts."""
        return await self.repository.remove_contact(contact_id, user)

    async def get_contact_by_contact_info(self, first_name: str, user: User):
        """Get the user's contact by first name."""
        return await self.repository.get_contact_by_contact_info(first_name, user)
