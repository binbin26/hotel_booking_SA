import enum
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class PaymentMethod(str, enum.Enum):
    """Accepted payment methods for booking creation."""

    CASH = "CASH"
    MOMO = "MOMO"
    ZALOPAY = "ZALOPAY"
    BANKING = "BANKING"


class BookingCreate(BaseModel):
    """Request body for POST /bookings."""

    user_id: Optional[int] = Field(default=None, gt=0)
    room_id: int = Field(..., gt=0)
    check_in: date
    check_out: date
    payment_method: PaymentMethod

    @model_validator(mode="after")
    def validate_date_range(self) -> "BookingCreate":
        """Ensure check-out is after check-in."""
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class BookingResponse(BaseModel):
    """Response payload for a created booking."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    booking_id: int = Field(validation_alias="id")
    user_id: int
    room_id: int
    check_in: date
    check_out: date
    total_nights: int
    total_price: Decimal
    status: str

    @field_serializer("total_price")
    def serialize_total_price(self, value: Decimal) -> int | float:
        """Render whole-number prices as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class BookingCustomerResponse(BaseModel):
    """Customer payload nested in booking detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: Optional[str] = None


class BookingRoomResponse(BaseModel):
    """Room payload nested in booking detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: str


class BookingDetailResponse(BaseModel):
    """Response payload for GET /bookings/{booking_id}."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    booking_id: int = Field(validation_alias="id")
    customer: BookingCustomerResponse = Field(validation_alias="user")
    room: BookingRoomResponse
    check_in: date
    check_out: date
    total_nights: int
    total_price: Decimal
    status: str
    payment_status: str = "UNPAID"

    @field_serializer("total_price")
    def serialize_total_price(self, value: Decimal) -> int | float:
        """Render whole-number prices as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class BookingCancelRequest(BaseModel):
    """Request body for PATCH /bookings/{booking_id}/cancel."""

    reason: str = Field(..., min_length=1, max_length=255)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        """Trim the cancellation reason and reject blank content."""
        reason = value.strip()
        if not reason:
            raise ValueError("reason is required")
        return reason


class BookingCancelResponse(BaseModel):
    """Response payload for a cancelled booking."""

    booking_id: int
    status: str
    cancel_reason: str
