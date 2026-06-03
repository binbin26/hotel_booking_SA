import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.booking_exceptions import (
    BookingAlreadyCancelledException,
    BookingNotFoundException,
    RoomNotAvailableException,
    RoomNotFoundException,
)
from app.models.booking import Booking, PaymentMethod
from app.models.user import User, UserRole
from app.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class BookingService:
    """Business logic for booking workflows."""

    def __init__(
        self,
        booking_repo: BookingRepository,
        session: AsyncSession,
    ) -> None:
        self._booking_repo = booking_repo
        self._session = session

    async def create_booking(
        self,
        user_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        payment_method: str,
    ) -> Booking:
        """Create a booking inside one transaction or raise a domain exception."""
        total_nights = self._calculate_total_nights(check_in, check_out)
        if self._session.in_transaction():
            return await self._create_with_existing_transaction(
                user_id,
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
            )

        async with self._session.begin():
            return await self._create_locked_booking(
                user_id,
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
            )

    async def _create_with_existing_transaction(
        self,
        user_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: str,
    ) -> Booking:
        try:
            booking = await self._create_locked_booking(
                user_id,
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
            )
            await self._session.commit()
            return booking
        except Exception:
            await self._session.rollback()
            raise

    async def _create_locked_booking(
        self,
        user_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: str,
    ) -> Booking:
        result = await self._booking_repo.create_booking(
            user_id=user_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            total_nights=total_nights,
            payment_method=PaymentMethod(payment_method),
        )
        if not result.room_exists:
            logger.warning("booking_room_not_found", extra={"room_id": room_id})
            raise RoomNotFoundException(room_id)
        if not result.room_available or result.booking is None:
            logger.info("booking_room_unavailable", extra={"room_id": room_id})
            raise RoomNotAvailableException(room_id)

        logger.info(
            "booking_created",
            extra={"booking_id": result.booking.id, "room_id": room_id},
        )
        return result.booking

    async def get_booking_detail(
        self,
        booking_id: int,
        current_user: User,
    ) -> Booking:
        """Return a visible booking detail or raise BookingNotFoundException."""
        booking = await self._booking_repo.get_booking_by_id(booking_id)
        if booking is None:
            logger.warning("booking_not_found", extra={"booking_id": booking_id})
            raise BookingNotFoundException(booking_id)

        if not self._can_view_booking(booking, current_user):
            logger.warning(
                "booking_access_denied",
                extra={"booking_id": booking_id, "user_id": current_user.id},
            )
            raise BookingNotFoundException(booking_id)

        return booking

    async def cancel_booking(
        self,
        booking_id: int,
        reason: str,
        current_user: User,
    ) -> Booking:
        """Cancel a visible booking or raise a domain exception."""
        if self._session.in_transaction():
            return await self._cancel_with_existing_transaction(
                booking_id,
                reason,
                current_user,
            )

        async with self._session.begin():
            return await self._cancel_visible_booking(
                booking_id,
                reason,
                current_user,
            )

    async def _cancel_with_existing_transaction(
        self,
        booking_id: int,
        reason: str,
        current_user: User,
    ) -> Booking:
        try:
            booking = await self._cancel_visible_booking(
                booking_id,
                reason,
                current_user,
            )
            await self._session.commit()
            return booking
        except Exception:
            await self._session.rollback()
            raise

    async def _cancel_visible_booking(
        self,
        booking_id: int,
        reason: str,
        current_user: User,
    ) -> Booking:
        booking = await self._booking_repo.get_booking_by_id(booking_id)
        if booking is None or not self._can_view_booking(booking, current_user):
            logger.warning(
                "booking_not_found",
                extra={"booking_id": booking_id, "user_id": current_user.id},
            )
            raise BookingNotFoundException(booking_id)

        result = await self._booking_repo.cancel_booking(booking_id, reason)
        if not result.booking_exists or result.booking is None:
            logger.warning("booking_not_found", extra={"booking_id": booking_id})
            raise BookingNotFoundException(booking_id)
        if result.already_cancelled:
            logger.info("booking_already_cancelled", extra={"booking_id": booking_id})
            raise BookingAlreadyCancelledException(booking_id)

        logger.info(
            "booking_cancelled",
            extra={"booking_id": result.booking.id, "user_id": current_user.id},
        )
        return result.booking

    def _calculate_total_nights(self, check_in: date, check_out: date) -> int:
        total_nights = (check_out - check_in).days
        if total_nights <= 0:
            raise ValueError("check_out must be after check_in")
        return total_nights

    def _can_view_booking(self, booking: Booking, current_user: User) -> bool:
        return current_user.role == UserRole.ADMIN or booking.user_id == current_user.id
