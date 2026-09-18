from datetime import date, timedelta

from sqlalchemy import Integer, and_, cast, extract, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactModel


class ContactRepository:
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
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
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
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_contacts_by_ids(
        self, contact_id: list[int], user: User
    ) -> list[Contact]:
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
        stmt = select(Contact).filter_by(
            first_name=first_name.lower(), user_id=user.id
        )
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()
