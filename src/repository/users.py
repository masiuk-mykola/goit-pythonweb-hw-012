"""Data access layer for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schemas import UserCreate


class UserRepository:
    """CRUD operations on the ``users`` table.

    Args:
        session: Async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get a user by primary key.

        Args:
            user_id: User ID.

        Returns:
            User | None: The user, or ``None`` if not found.
        """
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Get a user by username.

        Args:
            username: Exact username.

        Returns:
            User | None: The user, or ``None`` if not found.
        """
        stmt = select(User).filter_by(username=username)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email (case-insensitive).

        Args:
            email: Email address.

        Returns:
            User | None: The user, or ``None`` if not found.
        """
        stmt = select(User).filter_by(email=email.lower())
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(self, body: UserCreate, hashed_password: str) -> User:
        """Create a new user with the default ``user`` role.

        Args:
            body: Registration data.
            hashed_password: Password hash to store instead of the plain password.

        Returns:
            User: The created user.
        """
        user = User(
            username=body.username,
            email=body.email.lower(),
            hashed_password=hashed_password,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """Mark the user's email as confirmed.

        Args:
            email: Email address of the user.
        """
        user = await self.get_user_by_email(email)
        if user:
            user.confirmed = True
            await self.db.commit()

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Set a new avatar URL.

        Args:
            email: Email address of the user.
            url: Public URL of the uploaded avatar.

        Returns:
            User | None: The updated user, or ``None`` if not found.
        """
        user = await self.get_user_by_email(email)
        if user is None:
            return None
        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_refresh_token(self, user: User, token: str | None) -> None:
        """Store (or clear) the user's current refresh token.

        Args:
            user: User attached to the current session.
            token: New refresh token, or ``None`` to revoke it.
        """
        user.refresh_token = token
        await self.db.commit()

    async def update_password(self, email: str, hashed_password: str) -> User | None:
        """Replace the user's password hash and revoke their refresh token.

        Args:
            email: Email address of the user.
            hashed_password: New password hash.

        Returns:
            User | None: The updated user, or ``None`` if not found.
        """
        user = await self.get_user_by_email(email)
        if user is None:
            return None
        user.hashed_password = hashed_password
        user.refresh_token = None
        await self.db.commit()
        await self.db.refresh(user)
        return user
