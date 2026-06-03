from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.room import Room


class RoomImage(Base):
    """ORM model for room gallery images."""

    __tablename__ = "room_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    room: Mapped["Room"] = relationship("Room", back_populates="images")
