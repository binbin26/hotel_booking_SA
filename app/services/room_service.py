from app.exceptions.room_exceptions import RoomNotFoundException
from app.models.room import Room
from app.repositories.room_repository import RoomRepository


class RoomService:
    """Business logic for room search and detail."""

    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def get_room_detail(self, room_id: int) -> Room:
        """Return room with images or raise RoomNotFoundException."""
        room = await self._room_repo.get_room_by_id(room_id)
        if room is None:
            raise RoomNotFoundException(room_id)
        return room
