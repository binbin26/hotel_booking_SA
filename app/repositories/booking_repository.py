from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus, PaymentMethod
from app.models.room import Room, RoomStatus
from app.repositories.base_repository import BaseRepository


@dataclass(frozen=True)
class BookingCreateResult:
    """Database result for an attempted booking insert."""

    room_exists: bool
    room_available: bool
    booking: Booking | None = None


@dataclass(frozen=True)
class BookingCancelResult:
    """Database result for an attempted booking cancellation."""

    booking_exists: bool
    already_cancelled: bool
    booking: Booking | None = None


class BookingRepository(BaseRepository[Booking]):
    """Data access for bookings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Booking)

    async def create_booking(
        self,
        user_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: PaymentMethod,
    ) -> BookingCreateResult:
        """Lock room, reject overlapping dates, then insert a booking."""
        room = await self._lock_room(room_id)
        if room is None:
            return BookingCreateResult(room_exists=False, room_available=False)

        has_overlap = await self._has_active_overlap(room_id, check_in, check_out)
        if room.status != RoomStatus.AVAILABLE or has_overlap:
            return BookingCreateResult(room_exists=True, room_available=False)

        booking = Booking(
            user_id=user_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            total_nights=total_nights,
            total_price=room.price_per_night * total_nights,
            payment_method=payment_method,
        )
        self._session.add(booking)
        await self._session.flush()
        await self._session.refresh(booking)
        return BookingCreateResult(
            room_exists=True,
            room_available=True,
            booking=booking,
        )

    async def get_booking_by_id(self, booking_id: int) -> Booking | None:
        """Fetch one booking by id with customer and room eager-loaded."""
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.room),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancel_booking(
        self,
        booking_id: int,
        reason: str,
    ) -> BookingCancelResult:
        """Lock a booking row and set its status to CANCELLED."""
        _ = reason
        booking = await self._lock_booking(booking_id)
        if booking is None:
            return BookingCancelResult(
                booking_exists=False,
                already_cancelled=False,
            )
        if booking.status == BookingStatus.CANCELLED:
            return BookingCancelResult(
                booking_exists=True,
                already_cancelled=True,
                booking=booking,
            )

        booking.status = BookingStatus.CANCELLED
        await self._session.flush()
        await self._session.refresh(booking)
        return BookingCancelResult(
            booking_exists=True,
            already_cancelled=False,
            booking=booking,
        )

    async def _lock_room(self, room_id: int) -> Room | None:
        stmt = select(Room).where(Room.id == room_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _lock_booking(self, booking_id: int) -> Booking | None:
        stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _has_active_overlap(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
    ) -> bool:
        stmt = (
            select(Booking.id)
            .where(
                Booking.room_id == room_id,
                Booking.status != BookingStatus.CANCELLED,
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .limit(1)
        )
        return await self._session.scalar(stmt) is not None
