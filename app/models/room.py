import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking


class RoomType(str, enum.Enum):
    STANDARD = "STANDARD"
    DELUXE = "DELUXE"
    SUITE = "SUITE"
    VIP = "VIP"


class RoomStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"


class Room(Base):
    """ORM model for hotel rooms."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType, name="room_type"), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="room_status"),
        nullable=False,
        default=RoomStatus.AVAILABLE,
        server_default=RoomStatus.AVAILABLE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="room",
    )
