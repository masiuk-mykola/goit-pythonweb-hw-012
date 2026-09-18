from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactBase(BaseModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: EmailStr
    phone_number: str = Field(max_length=10)
    dob: date
    additional_info: str | None = Field(default=None, max_length=255)


class ContactModel(ContactBase):
    pass


class ContactUpdate(ContactModel):
    pass


class ContactResponse(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dob: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    avatar: str | None = None
    confirmed: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RequestEmail(BaseModel):
    email: EmailStr
