from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.repositories.base_repository import BaseRepository


class RoomRepository(BaseRepository[Room]):
    """Data access for rooms and related entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Room)

    async def get_room_by_id(self, room_id: int) -> Room | None:
        """Fetch one room by id with room_images eager-loaded."""
        stmt = (
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.images))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
