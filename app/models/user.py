import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking


class UserRole(str, enum.Enum):
    GUEST = "GUEST"
    ADMIN = "ADMIN"


class User(Base):
    """ORM model for hotel users (guests and admins)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.GUEST,
        server_default=UserRole.GUEST.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="user",
    )
