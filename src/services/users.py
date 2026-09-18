"""Business logic for users."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate


class UserService:
    """Thin service layer over :class:`~src.repository.users.UserRepository`.

    Args:
        db: Async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate, hashed_password: str) -> User:
        """Create a user. See :meth:`UserRepository.create_user`."""
        return await self.repository.create_user(body, hashed_password)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get a user by ID."""
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str) -> User | None:
        """Get a user by username."""
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str) -> None:
        """Mark the user's email as confirmed."""
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Set a new avatar URL for the user."""
        return await self.repository.update_avatar_url(email, url)

    async def update_refresh_token(self, user: User, token: str | None) -> None:
        """Store or revoke the user's refresh token."""
        return await self.repository.update_refresh_token(user, token)

    async def update_password(self, email: str, hashed_password: str) -> User | None:
        """Replace the user's password hash."""
        return await self.repository.update_password(email, hashed_password)
