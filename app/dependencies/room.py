from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.room_repository import RoomRepository
from app.services.room_service import RoomService


def get_room_repository(
    db: AsyncSession = Depends(get_db),
) -> RoomRepository:
    """Provide RoomRepository bound to the request session."""
    return RoomRepository(db)


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repository),
) -> RoomService:
    """Provide RoomService with injected repository."""
    return RoomService(room_repo)
