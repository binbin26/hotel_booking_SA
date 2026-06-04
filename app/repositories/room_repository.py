from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room, RoomStatus
from app.models.booking import Booking, BookingStatus
from app.repositories.base_repository import BaseRepository
from datetime import date


class RoomRepository(BaseRepository[Room]):
    """Data access for rooms and related entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Room)

    async def search_available_rooms(
        self,
        check_in: date,
        check_out: date,
        capacity: int,
    ) -> list[Room]:
        """
        Find rooms with sufficient capacity and no overlapping bookings.
        
        Returns list of available rooms for the given date range.
        """
        subquery = (
            select(Booking.room_id)
            .where(
                Booking.status != BookingStatus.CANCELLED,
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .distinct()
        )
        
        stmt = (
            select(Room)
            .where(
                Room.status == RoomStatus.AVAILABLE,
                Room.capacity >= capacity,
                ~Room.id.in_(subquery),
            )
            .options(selectinload(Room.images))
        )
        
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_room_by_id(self, room_id: int) -> Room | None:
        """Fetch one room by id with room_images eager-loaded."""
        stmt = (
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.images))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_room(
        self,
        room_id: int,
        room_type: str,
        capacity: int,
        price_per_night: str | float,
        description: str | None,
        status: str,
    ) -> Room | None:
        """Update room attributes by id."""
        room = await self._session.get(Room, room_id)
        if room is None:
            return None
        room.room_type = room_type
        room.capacity = capacity
        room.price_per_night = price_per_night
        room.description = description
        room.status = status
        await self._session.flush()
        await self._session.refresh(room)
        return room
