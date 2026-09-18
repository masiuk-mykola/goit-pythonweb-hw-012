"""SQLAlchemy ORM models."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import DateTime


class Base(DeclarativeBase):
    """Declarative base class for all models."""


class UserRole(str, enum.Enum):
    """Access role of a user."""

    USER = "user"
    ADMIN = "admin"


class Contact(Base):
    """A phonebook entry owned by a single :class:`User`."""

    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(10), nullable=False)
    dob: Mapped[datetime] = mapped_column(
        "dob",
        DateTime,
    )
    additional_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="contacts")


class User(Base):
    """An application user (account owner)."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )
    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contacts: Mapped[list[Contact]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
