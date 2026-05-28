from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class SupplierCreate(BaseModel):
    name:        str       = Field(..., min_length=2, max_length=255)
    phone:       str|None  = None
    email:       str|None  = None
    address:     str|None  = None
    description: str|None  = None
    telegram_username: str|None = None


class SupplierUpdate(BaseModel):
    name:        str|None  = Field(None, min_length=2, max_length=255)
    phone:       str|None  = None
    email:       str|None  = None
    address:     str|None  = None
    description: str|None  = None
    telegram_username: str|None = None
    is_active:   bool|None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                int
    company_id:        int
    name:              str
    phone:             str|None
    email:             str|None
    address:           str|None
    description:       str|None
    telegram_username: str|None
    is_active:         bool
    created_at:        datetime
    updated_at:        datetime