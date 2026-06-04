from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Data access for payments."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Payment)

    async def create_payment(
        self,
        booking_id: int,
        amount: Decimal,
        payment_method: str,
        transaction_ref: str | None = None,
    ) -> Payment:
        """Create a new payment record and update booking status to CONFIRMED."""
        payment = Payment(
            booking_id=booking_id,
            amount=amount,
            payment_method=payment_method,
            transaction_ref=transaction_ref,
            status=PaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
        self._session.add(payment)

        # Update booking status to CONFIRMED (atomic UPDATE)
        stmt = update(Booking).where(
            Booking.id == booking_id
        ).values(status=BookingStatus.CONFIRMED)
        await self._session.execute(stmt)

        await self._session.flush()
        await self._session.commit()
        return payment

    async def get_payment_by_booking(self, booking_id: int) -> Payment | None:
        """Retrieve the most recent payment for a booking."""
        stmt = (
            select(Payment)
            .where(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
