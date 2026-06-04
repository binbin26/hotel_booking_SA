from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService


def get_payment_repository(
    db: AsyncSession = Depends(get_db),
) -> PaymentRepository:
    """Provide PaymentRepository bound to the request session."""
    return PaymentRepository(db)


def get_payment_service(
    db: AsyncSession = Depends(get_db, use_cache=False),
) -> PaymentService:
    """Provide PaymentService with its own transactional session."""
    return PaymentService(
        PaymentRepository(db),
        BookingRepository(db),
        db,
    )
