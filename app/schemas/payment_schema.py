from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class PaymentCreate(BaseModel):
    """Request body for POST /bookings/{booking_id}/payment."""

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(..., min_length=1, max_length=50)
    transaction_ref: Optional[str] = Field(default=None, max_length=255)

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: str) -> str:
        """Ensure payment method is not blank."""
        method = value.strip().upper()
        if not method:
            raise ValueError("payment_method cannot be empty")
        return method


class PaymentResponse(BaseModel):
    """Response payload for a payment transaction."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_id: int = Field(validation_alias="id")
    booking_id: int
    amount: Decimal
    payment_method: str
    status: str
    transaction_ref: Optional[str] = None
    paid_at: Optional[datetime] = None

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> int | float:
        """Render whole-number amounts as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)
