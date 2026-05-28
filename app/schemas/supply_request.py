from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from decimal import Decimal
from app.core.enums import RequestStatus


class SupplyRequestCreate(BaseModel):
    object_id:        int
    task_description: str       = Field(..., min_length=5)
    notes:            str|None  = None
    priority:         str       = "medium"  # low / medium / high
    required_by:      date|None = None


class SupplyRequestUpdate(BaseModel):
    task_description: str|None  = None
    notes:            str|None  = None
    priority:         str|None  = None
    required_by:      date|None = None
    manager_id:       int|None  = None
    supervisor_id:    int|None  = None


class SupplyRequestStatusChange(BaseModel):
    new_status: RequestStatus
    reason:     str|None = None


class SupplyRequestItemCreate(BaseModel):
    name:       str             = Field(..., min_length=2)
    unit:       str|None        = None
    quantity:   Decimal|None    = None
    unit_price: Decimal|None    = None
    notes:      str|None        = None


class SupplyRequestItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    request_id:  int
    name:        str
    unit:        str|None
    quantity:    Decimal|None
    unit_price:  Decimal|None
    total_price: Decimal|None
    notes:       str|None
    created_at:  datetime


class SupplyRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    company_id:       int
    request_number:   str|None
    object_id:        int
    status:           RequestStatus
    created_by_id:    int
    manager_id:       int|None
    supervisor_id:    int|None
    task_description: str|None
    notes:            str|None
    priority:         str
    required_by:      date|None
    delivery_date:    date|None
    delivery_time:    str|None
    driver_name:      str|None
    vehicle_number:   str|None
    vehicle_model:    str|None
    total_amount:     Decimal|None
    created_at:       datetime
    updated_at:       datetime
    items:            list[SupplyRequestItemResponse] = []


class SupplyRequestListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    request_number:   str|None
    object_id:        int
    status:           RequestStatus
    priority:         str
    task_description: str|None
    required_by:      date|None
    total_amount:     Decimal|None
    created_at:       datetime
    updated_at:       datetime