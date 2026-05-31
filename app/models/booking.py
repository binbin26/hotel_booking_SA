import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.user import User


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    MOMO = "MOMO"
    ZALOPAY = "ZALOPAY"
    BANKING = "BANKING"


class Booking(Base):
    """ORM model for room bookings."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_room_dates", "room_id", "check_in", "check_out"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="bookings")
    room: Mapped["Room"] = relationship("Room", back_populates="bookings")
