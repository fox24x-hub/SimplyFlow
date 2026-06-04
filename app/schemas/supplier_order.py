from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal


class SupplierOrderCreate(BaseModel):
    supplier_id:    int
    notes:          str | None = None


class SupplierOrderInvoice(BaseModel):
    """Снабженец вносит счёт от поставщика."""
    invoice_number: str            = Field(..., min_length=1)
    invoice_amount: Decimal
    notes:          str | None     = None


class SupplierOrderReview(BaseModel):
    """Мастер или РП согласует счёт."""
    approved:       bool
    notes:          str | None     = None


class SupplierOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    request_id:       int
    supplier_id:      int
    status:           str
    invoice_number:   str | None
    invoice_amount:   Decimal | None
    invoice_approved: bool
    notes:            str | None
    created_at:       datetime
    updated_at:       datetime