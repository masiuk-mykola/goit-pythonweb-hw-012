"""Pydantic schemas for request validation and response serialization."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.database.models import UserRole


class ContactBase(BaseModel):
    """Fields shared by all contact schemas."""

    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: EmailStr
    phone_number: str = Field(max_length=10)
    dob: date
    additional_info: str | None = Field(default=None, max_length=255)


class ContactModel(ContactBase):
    """Request body for creating a contact."""


class ContactUpdate(ContactModel):
    """Request body for updating a contact."""


class ContactResponse(ContactBase):
    """Contact returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dob: datetime


class UserCreate(BaseModel):
    """Request body for user registration."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class User(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    avatar: str | None = None
    confirmed: bool
    role: UserRole


class Token(BaseModel):
    """Access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenModel(Token):
    """Access + refresh token pair returned on login and refresh."""

    refresh_token: str


class TokenRefreshRequest(BaseModel):
    """Request body for exchanging a refresh token for a new token pair."""

    refresh_token: str


class RequestEmail(BaseModel):
    """Request body containing only an email address."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for setting a new password with a reset token."""

    token: str
    new_password: str = Field(min_length=6, max_length=128)
