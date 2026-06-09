import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.room import Room
    from app.models.user import User


def _generate_secure_token() -> str:
    """Generate a unique, unguessable token for guest self-service links."""
    return uuid.uuid4().hex


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    MOMO = "MOMO"
    ZALOPAY = "ZALOPAY"
    BANKING = "BANKING"


class CancelledBy(str, enum.Enum):
    """Who initiated the booking cancellation."""

    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class Booking(Base):
    """ORM model for room bookings."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_room_dates", "room_id", "check_in", "check_out"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    total_nights: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"),
        nullable=False,
        default=BookingStatus.PENDING,
        server_default=BookingStatus.PENDING.value,
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
        nullable=True,
    )
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    guest_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    guest_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    secure_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=_generate_secure_token,
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[Optional[CancelledBy]] = mapped_column(
        Enum(CancelledBy, name="cancelled_by"),
        nullable=True,
    )
    # Requested date change fields for tracking guest change requests
    requested_check_in: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    requested_check_out: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="bookings")
    room: Mapped["Room"] = relationship("Room", back_populates="bookings")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="booking")
