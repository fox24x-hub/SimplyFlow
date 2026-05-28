from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ObjectCreate(BaseModel):
    name:        str       = Field(..., min_length=2, max_length=500)
    address:     str       = Field(..., min_length=5, max_length=500)
    description: str|None = None
    master_id:     int|None = None
    supervisor_id: int|None = None


class ObjectUpdate(BaseModel):
    name:          str|None = Field(None, min_length=2, max_length=500)
    address:       str|None = None
    description:   str|None = None
    master_id:     int|None = None
    supervisor_id: int|None = None
    is_active:     bool|None = None


class ObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    company_id:   int
    name:         str
    address:      str
    description:  str|None
    master_id:    int|None
    supervisor_id:int|None
    is_active:    bool
    created_at:   datetime
    updated_at:   datetime