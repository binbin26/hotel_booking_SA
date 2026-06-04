import structlog
from decimal import Decimal
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.booking_exceptions import BookingNotFoundException
from app.exceptions.payment_exceptions import (
    PaymentAlreadyPaidException,
    PaymentAmountMismatchException,
)
from app.models.booking import Booking, BookingStatus
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.models.payment import Payment

logger = structlog.get_logger(__name__)


class PaymentService:
    """Business logic for payment workflows."""

    def __init__(
        self,
        payment_repo: PaymentRepository,
        booking_repo: BookingRepository,
        session: AsyncSession,
    ) -> None:
        self._payment_repo = payment_repo
        self._booking_repo = booking_repo
        self._session = session

    async def process_payment(
        self,
        booking_id: int,
        amount: Decimal,
        payment_method: str,
        transaction_ref: str | None = None,
    ) -> Payment:
        """
        Process payment for a booking with atomic locking.
        
        Uses SELECT...FOR UPDATE to prevent race conditions:
        1. Lock booking row
        2. Check if already CONFIRMED
        3. Validate amount
        4. Create payment + update status atomically
        """
        logger.msg("payment.start", booking_id=booking_id, amount=float(amount))

        # Lock booking row to prevent concurrent payments (SELECT...FOR UPDATE)
        stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
        result = await self._session.execute(stmt)
        booking = result.scalar_one_or_none()
        
        if booking is None:
            raise BookingNotFoundException(booking_id)
        
        # Check if already paid (prevents race condition with WITH_FOR_UPDATE lock)
        if booking.status == BookingStatus.CONFIRMED:
            raise PaymentAlreadyPaidException(booking_id)
        
        # Validate amount matches total price
        if amount != booking.total_price:
            raise PaymentAmountMismatchException(
                booking_id,
                float(booking.total_price),
                float(amount),
            )

        # Create payment and update booking status
        # (transaction is managed by dependency injection)
        payment = await self._payment_repo.create_payment(
            booking_id=booking_id,
            amount=amount,
            payment_method=payment_method,
            transaction_ref=transaction_ref,
        )

        logger.msg("payment.success", payment_id=payment.id, booking_id=booking_id)
        return payment
