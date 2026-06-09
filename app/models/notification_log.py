"""Model for storing guest interaction notifications."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking


class InteractionType(str, enum.Enum):
    """Type of guest interaction with email."""

    EMAIL_OPEN = "EMAIL_OPEN"
    LINK_CLICK_VIEW = "LINK_CLICK_VIEW"
    LINK_CLICK_EDIT = "LINK_CLICK_EDIT"
    LINK_CLICK_CANCEL = "LINK_CLICK_CANCEL"
    INVOICE_INTERACTION = "INVOICE_INTERACTION"
    BOOKING_CANCELLED_BY_GUEST = "BOOKING_CANCELLED_BY_GUEST"
    BOOKING_CANCELLED_BY_ADMIN = "BOOKING_CANCELLED_BY_ADMIN"


class NotificationLog(Base):
    """ORM model for logging guest interactions and notifications."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType),
        nullable=False,
    )
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    # Relationship to booking
    booking: Mapped["Booking"] = relationship(
        "Booking",
        foreign_keys=[booking_id],
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog(id={self.id}, booking_id={self.booking_id}, "
            f"type={self.interaction_type}, created_at={self.created_at})>"
        )
