from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import BookingService


def get_booking_repository(
    db: AsyncSession = Depends(get_db),
) -> BookingRepository:
    """Provide BookingRepository bound to the request session."""
    return BookingRepository(db)


def get_booking_service(
    db: AsyncSession = Depends(get_db, use_cache=False),
) -> BookingService:
    """Provide BookingService with its own transactional session."""
    return BookingService(BookingRepository(db), db)
