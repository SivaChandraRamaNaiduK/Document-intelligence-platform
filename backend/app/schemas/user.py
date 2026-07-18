"""
Pydantic schemas for user-related requests and responses.

Separating schemas from the SQLAlchemy model matters: it lets us control
exactly what's accepted on input (e.g. plain password) and returned on
output (never the hashed password), independent of the DB shape.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # allows .model_validate(user_orm_instance)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str