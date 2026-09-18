"""Data access layer for contacts."""

from datetime import date, timedelta

from sqlalchemy import Integer, and_, cast, extract, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactModel


class ContactRepository:
    """CRUD operations on the ``contacts`` table, always scoped to one owner.

    Args:
        session: Async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_contacts(
        self,
        user: User,
        contact_first_name: str | None = None,
        contact_last_name: str | None = None,
        contact_email: str | None = None,
        days_to_birthday: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Contact]:
        """List the user's contacts with optional filters and pagination.

        Filters are combined with AND; string filters are case-insensitive.

        Args:
            user: Owner of the contacts.
            contact_first_name: Exact first name to match.
            contact_last_name: Exact last name to match.
            contact_email: Exact email to match.
            days_to_birthday: Only contacts whose birthday falls within the
                next N days, today included.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            list[Contact]: Matching contacts.
        """
        conditions = [Contact.user_id == user.id]
        if contact_first_name:
            conditions.append(
                func.lower(Contact.first_name) == contact_first_name.lower()
            )
        if contact_last_name:
            conditions.append(
                func.lower(Contact.last_name) == contact_last_name.lower()
            )
        if contact_email:
            conditions.append(func.lower(Contact.email) == contact_email.lower())
        if days_to_birthday is not None:
            today = date.today()
            birthday_window = {
                (day.month, day.day)
                for day in (
                    today + timedelta(days=offset)
                    for offset in range(days_to_birthday + 1)
                )
            }
            conditions.append(
                tuple_(
                    cast(extract("month", Contact.dob), Integer),
                    cast(extract("day", Contact.dob), Integer),
                ).in_(birthday_window)
            )

        query = select(Contact).where(and_(*conditions)).offset(skip).limit(limit)
        contacts = await self.db.execute(query)
        return list(contacts.scalars().all())

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Get one of the user's contacts by ID.

        Args:
            contact_id: Contact ID.
            user: Owner of the contact.

        Returns:
            Contact | None: The contact, or ``None`` if not found or owned by
            someone else.
        """
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """Create a contact for the user.

        Args:
            body: Contact data.
            user: Owner of the new contact.

        Returns:
            Contact: The created contact.
        """
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        """Update one of the user's contacts.

        Args:
            contact_id: Contact ID.
            body: New contact data.
            user: Owner of the contact.

        Returns:
            Contact | None: The updated contact, or ``None`` if not found.
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if not contact:
            return None

        update_data = body.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(contact, field, value)

        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Delete one of the user's contacts.

        Args:
            contact_id: Contact ID.
            user: Owner of the contact.

        Returns:
            Contact | None: The deleted contact, or ``None`` if not found.
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_contacts_by_ids(
        self, contact_id: list[int], user: User
    ) -> list[Contact]:
        """Get the user's contacts with the given IDs.

        Args:
            contact_id: List of contact IDs.
            user: Owner of the contacts.

        Returns:
            list[Contact]: Found contacts (missing IDs are skipped).
        """
        stmt = select(Contact).where(
            Contact.id.in_(contact_id), Contact.user_id == user.id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_contact_by_contact_info(
        self,
        first_name: str,
        user: User,
    ) -> Contact | None:
        """Get the user's contact by first name.

        Args:
            first_name: First name (lower-cased before matching).
            user: Owner of the contact.

        Returns:
            Contact | None: The contact, or ``None`` if not found.
        """
        stmt = select(Contact).filter_by(
            first_name=first_name.lower(), user_id=user.id
        )
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()
