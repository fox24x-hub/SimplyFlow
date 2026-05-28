from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from app.core.enums import UserRole


class UserRegister(BaseModel):
    email:     EmailStr
    password:  str      = Field(..., min_length=8)
    full_name: str      = Field(..., min_length=2)
    phone:     str | None = None
    role:      UserRole = UserRole.master


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                int
    company_id:        int
    email:             str
    full_name:         str
    phone:             str | None
    role:              UserRole
    is_active:         bool
    telegram_username: str | None
    created_at:        datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"