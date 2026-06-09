from dataclasses import dataclass
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus, CancelledBy, PaymentMethod
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
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: PaymentMethod,
        user_id: int | None = None,
        guest_name: str = "",
        guest_email: str = "",
        guest_phone: str | None = None,
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
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
        )
        self._session.add(booking)
        await self._session.flush()
        await self._session.refresh(booking)
        return BookingCreateResult(
            room_exists=True,
            room_available=True,
            booking=booking,
        )

    async def get_booking_by_token(self, token: str) -> Booking | None:
        """Fetch one booking by secure token with room and payments eager-loaded."""
        stmt = (
            select(Booking)
            .where(Booking.secure_token == token)
            .options(
                selectinload(Booking.room),
                selectinload(Booking.payments),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_guest_booking(
        self,
        booking_id: int,
        guest_email: str,
    ) -> Booking | None:
        """Fetch a guest booking matching both id and email with room and payments."""
        stmt = (
            select(Booking)
            .where(
                Booking.id == booking_id,
                Booking.guest_email == guest_email,
            )
            .options(
                selectinload(Booking.room),
                selectinload(Booking.payments),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_booking_by_id(self, booking_id: int) -> Booking | None:
        """Fetch one booking by id with customer, room, and payments eager-loaded."""
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.room),
                selectinload(Booking.payments),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_bookings(self) -> list[Booking]:
        """Fetch all bookings sorted by created_at DESC with relations eager-loaded."""
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.room),
                selectinload(Booking.payments),
            )
            .order_by(desc(Booking.created_at))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_user_bookings(self, user_id: int) -> list[Booking]:
        """Fetch all bookings for a specific user sorted by created_at DESC."""
        stmt = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.room),
            )
            .order_by(desc(Booking.created_at))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def cancel_booking(
        self,
        booking_id: int,
        reason: str,
        cancelled_by: CancelledBy,
    ) -> BookingCancelResult:
        """Lock booking, persist cancellation metadata, and release the room."""
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
        booking.cancel_reason = reason
        booking.cancelled_by = cancelled_by

        room = await self._lock_room(booking.room_id)
        if room is not None and room.status == RoomStatus.BOOKED:
            room.status = RoomStatus.AVAILABLE

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
