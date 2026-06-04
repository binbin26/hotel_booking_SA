from decimal import Decimal
from datetime import date

import structlog

from app.exceptions.room_exceptions import RoomNotFoundException
from app.models.room import Room
from app.repositories.room_repository import RoomRepository

logger = structlog.get_logger(__name__)


class RoomService:
    """Business logic for room search and detail."""

    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def search_available_rooms(
        self,
        check_in: date,
        check_out: date,
        capacity: int,
    ) -> list[tuple[Room, int, Decimal]]:
        """Search for available rooms. Returns (room, total_nights, estimated_price)."""
        total_nights = (check_out - check_in).days
        if total_nights <= 0:
            raise ValueError("check_out must be after check_in")
        
        rooms = await self._room_repo.search_available_rooms(
            check_in, check_out, capacity
        )
        
        result = [
            (room, total_nights, room.price_per_night * total_nights)
            for room in rooms
        ]
        
        await logger.ainfo(
            "room.search.success",
            results_count=len(result),
        )
        return result

    async def get_room_detail(self, room_id: int) -> Room:
        """Return room with images or raise RoomNotFoundException."""
        room = await self._room_repo.get_room_by_id(room_id)
        if room is None:
            raise RoomNotFoundException(room_id)
        return room

    async def update_room(
        self,
        room_id: int,
        room_type: str,
        capacity: int,
        price_per_night: Decimal,
        description: str | None,
        status: str,
    ) -> Room:
        """Update room details. Raises RoomNotFoundException if room does not exist."""
        await logger.ainfo(
            "room.update.start",
            room_id=room_id,
            room_type=room_type,
            capacity=capacity,
            price_per_night=str(price_per_night),
            status=status,
        )
        
        room = await self._room_repo.update_room(
            room_id=room_id,
            room_type=room_type,
            capacity=capacity,
            price_per_night=price_per_night,
            description=description,
            status=status,
        )
        
        if room is None:
            await logger.ainfo(
                "room.update.not_found",
                room_id=room_id,
            )
            raise RoomNotFoundException(room_id)
        
        await logger.ainfo(
            "room.update.success",
            room_id=room_id,
            room_number=room.room_number,
        )
        return room
