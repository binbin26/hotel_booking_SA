import enum
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Optional

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
    """Request body for POST /bookings (guest checkout)."""

    room_id: int = Field(..., gt=0)
    check_in: date
    check_out: date
    payment_method: PaymentMethod
    guest_name: str = Field(..., min_length=1, max_length=255)
    guest_email: str = Field(..., min_length=5, max_length=255)
    guest_phone: str = Field(..., min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_date_range(self) -> "BookingCreate":
        """Ensure check-out is after check-in."""
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self
    
    @field_validator("guest_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Basic email validation."""
        if "@" not in value or "." not in value:
            raise ValueError("Invalid email address")
        return value.strip().lower()
    
    @field_validator("guest_name", "guest_phone")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        """Strip leading/trailing whitespace."""
        return value.strip()


class BookingResponse(BaseModel):
    """Response payload for a created booking."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    booking_id: int = Field(validation_alias="id")
    user_id: Optional[int] = None
    room_id: int
    check_in: date
    check_out: date
    total_nights: int
    total_price: Decimal
    guest_name: str
    guest_email: str
    guest_phone: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    def normalize_booking_detail(cls, data: Any) -> Any:
        """Map guest fields and payment status when validating from ORM."""
        if isinstance(data, dict):
            return data

        booking = data
        payments = booking.payments or []
        payment_status = "UNPAID"
        if any(
            getattr(payment.status, "value", payment.status) == "PAID"
            for payment in payments
        ):
            payment_status = "PAID"

        if booking.user is not None:
            customer = booking.user
        else:
            customer = SimpleNamespace(
                id=0,
                full_name=booking.guest_name,
                email=booking.guest_email,
                phone=booking.guest_phone,
            )

        status = booking.status
        if hasattr(status, "value"):
            status = status.value

        return {
            "id": booking.id,
            "user": customer,
            "room": booking.room,
            "check_in": booking.check_in,
            "check_out": booking.check_out,
            "total_nights": booking.total_nights,
            "total_price": booking.total_price,
            "status": status,
            "payment_status": payment_status,
        }

    @field_serializer("total_price")
    def serialize_total_price(self, value: Decimal) -> int | float:
        """Render whole-number prices as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class CancelledBy(str, enum.Enum):
    """Who initiated the booking cancellation."""

    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class BookingCancelRequest(BaseModel):
    """Request body for PATCH /bookings/{booking_id}/cancel."""

    reason: str = Field(..., min_length=1, max_length=500)
    cancelled_by: CancelledBy = CancelledBy.CUSTOMER


class AdminBookingCancelRequest(BookingCancelRequest):
    """Admin cancel request — defaults actor to ADMIN."""

    cancelled_by: CancelledBy = CancelledBy.ADMIN

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

    status: str
    cancel_reason: str
    cancelled_by: str


class AdminBookingCustomerResponse(BaseModel):
    """Nested customer payload for admin booking list."""

    full_name: str
    phone: Optional[str] = None
    email: str


class AdminBookingRoomResponse(BaseModel):
    """Nested room payload for admin booking list."""

    room_number: str
    room_type: str
    capacity: int


class AdminBookingListItemResponse(BaseModel):
    """Single booking row for GET /admin/bookings with joined relations."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    check_in: date
    check_out: date
    total_price: Decimal
    status: str
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    payment_status: str = "UNPAID"
    customer: AdminBookingCustomerResponse
    room: AdminBookingRoomResponse

    @model_validator(mode="before")
    @classmethod
    def normalize_admin_booking(cls, data: Any) -> Any:
        """Map ORM booking with user/guest and room into admin list shape."""
        if isinstance(data, dict):
            return data

        booking = data
        payments = booking.payments or []
        payment_status = "UNPAID"
        if any(
            getattr(payment.status, "value", payment.status) == "PAID"
            for payment in payments
        ):
            payment_status = "PAID"

        if booking.user is not None:
            customer = AdminBookingCustomerResponse(
                full_name=booking.user.full_name,
                phone=booking.user.phone,
                email=booking.user.email,
            )
        else:
            customer = AdminBookingCustomerResponse(
                full_name=booking.guest_name,
                phone=booking.guest_phone,
                email=booking.guest_email,
            )

        room_type = booking.room.room_type
        if hasattr(room_type, "value"):
            room_type = room_type.value

        status = booking.status
        if hasattr(status, "value"):
            status = status.value

        cancelled_by = booking.cancelled_by
        if cancelled_by is not None and hasattr(cancelled_by, "value"):
            cancelled_by = cancelled_by.value

        return {
            "id": booking.id,
            "check_in": booking.check_in,
            "check_out": booking.check_out,
            "total_price": booking.total_price,
            "status": status,
            "cancel_reason": booking.cancel_reason,
            "cancelled_by": cancelled_by,
            "payment_status": payment_status,
            "customer": customer,
            "room": AdminBookingRoomResponse(
                room_number=booking.room.room_number,
                room_type=str(room_type),
                capacity=booking.room.capacity,
            ),
        }

    @field_serializer("total_price")
    def serialize_total_price(self, value: Decimal) -> int | float:
        """Render whole-number prices as JSON numbers."""
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class GuestChangeDatesRequest(BaseModel):
    """Request body for POST /bookings/public/{secure_token}/change-request."""

    check_in: date = Field(..., description="New check-in date")
    check_out: date = Field(..., description="New check-out date")

    @model_validator(mode="after")
    def validate_date_range(self) -> "GuestChangeDatesRequest":
        """Ensure check-out is after check-in."""
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class AdminChangeResponseRequest(BaseModel):
    """Request body for POST /admin/bookings/{booking_id}/change-response."""

    action: str = Field(..., description="Action to take: APPROVE or REJECT")

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        """Ensure action is APPROVE or REJECT."""
        action_upper = value.strip().upper()
        if action_upper not in ("APPROVE", "REJECT"):
            raise ValueError("action must be APPROVE or REJECT")
        return action_upper
