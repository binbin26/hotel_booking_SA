import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.booking_exceptions import (
    BookingAlreadyCancelledException,
    BookingNotFoundException,
    InvalidBookingTokenException,
    RoomNotAvailableException,
    RoomNotFoundException,
)
from app.models.booking import Booking, CancelledBy, PaymentMethod
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
        room_id: int,
        check_in: date,
        check_out: date,
        payment_method: str,
        user_id: int | None = None,
        guest_name: str = "",
        guest_email: str = "",
        guest_phone: str | None = None,
    ) -> Booking:
        """Create a booking inside one transaction or raise a domain exception."""
        total_nights = self._calculate_total_nights(check_in, check_out)
        if self._session.in_transaction():
            return await self._create_with_existing_transaction(
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
                user_id,
                guest_name,
                guest_email,
                guest_phone,
            )

        async with self._session.begin():
            return await self._create_locked_booking(
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
                user_id,
                guest_name,
                guest_email,
                guest_phone,
            )

    async def _create_with_existing_transaction(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: str,
        user_id: int | None = None,
        guest_name: str = "",
        guest_email: str = "",
        guest_phone: str | None = None,
    ) -> Booking:
        try:
            booking = await self._create_locked_booking(
                room_id,
                check_in,
                check_out,
                total_nights,
                payment_method,
                user_id,
                guest_name,
                guest_email,
                guest_phone,
            )
            await self._session.commit()
            return booking
        except Exception:
            await self._session.rollback()
            raise

    async def _create_locked_booking(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        total_nights: int,
        payment_method: str,
        user_id: int | None = None,
        guest_name: str = "",
        guest_email: str = "",
        guest_phone: str | None = None,
    ) -> Booking:
        result = await self._booking_repo.create_booking(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            total_nights=total_nights,
            payment_method=PaymentMethod(payment_method),
            user_id=user_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
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

    async def verify_guest_token(self, token: str) -> Booking:
        """Return a booking for a valid secure token or raise InvalidBookingTokenException."""
        normalized = token.strip()
        if not normalized or len(normalized) < 16:
            logger.warning("invalid_booking_token_format", extra={"token_prefix": normalized[:8]})
            raise InvalidBookingTokenException(token)

        booking = await self._booking_repo.get_booking_by_token(normalized)
        if booking is None:
            logger.warning("booking_token_not_found", extra={"token_prefix": normalized[:8]})
            raise InvalidBookingTokenException(token)

        logger.info("guest_token_verified", extra={"booking_id": booking.id})
        return booking

    async def get_public_booking(self, token: str) -> Booking:
        """Return a booking visible via guest self-service token."""
        return await self.verify_guest_token(token)

    async def cancel_booking_by_token(self, token: str, reason: str) -> Booking:
        """Cancel a booking using its secure guest token."""
        booking = await self.verify_guest_token(token)
        if self._session.in_transaction():
            return await self._cancel_by_token_with_existing_transaction(booking.id, reason)

        async with self._session.begin():
            return await self._cancel_booking_by_id(
                booking.id,
                reason,
                CancelledBy.CUSTOMER,
            )

    async def _cancel_by_token_with_existing_transaction(
        self,
        booking_id: int,
        reason: str,
    ) -> Booking:
        try:
            booking = await self._cancel_booking_by_id(
                booking_id,
                reason,
                CancelledBy.CUSTOMER,
            )
            await self._session.commit()
            return booking
        except Exception:
            await self._session.rollback()
            raise

    async def _cancel_booking_by_id(
        self,
        booking_id: int,
        reason: str,
        cancelled_by: CancelledBy,
    ) -> Booking:
        result = await self._booking_repo.cancel_booking(
            booking_id,
            reason,
            cancelled_by,
        )
        if not result.booking_exists or result.booking is None:
            logger.warning("booking_not_found", extra={"booking_id": booking_id})
            raise BookingNotFoundException(booking_id)
        if result.already_cancelled:
            logger.info("booking_already_cancelled", extra={"booking_id": booking_id})
            raise BookingAlreadyCancelledException(booking_id)

        logger.info("booking_cancelled_by_token", extra={"booking_id": booking_id})
        return result.booking

    async def track_guest_booking(
        self,
        booking_id: int,
        guest_email: str,
    ) -> Booking:
        """Return a guest booking matched by id and email or raise BookingNotFoundException."""
        normalized_email = guest_email.strip().lower()
        booking = await self._booking_repo.get_guest_booking(
            booking_id,
            normalized_email,
        )
        if booking is None:
            logger.warning(
                "guest_booking_not_found",
                extra={"booking_id": booking_id, "guest_email": normalized_email},
            )
            raise BookingNotFoundException(booking_id)

        logger.info(
            "guest_booking_tracked",
            extra={"booking_id": booking_id, "guest_email": normalized_email},
        )
        return booking

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

    async def get_all_bookings(self) -> list[Booking]:
        """Return all bookings for ADMIN users."""
        bookings = await self._booking_repo.get_all_bookings()
        logger.info("all_bookings_retrieved", extra={"count": len(bookings)})
        return bookings

    async def get_user_bookings(self, user_id: int) -> list[Booking]:
        """Return all bookings for a specific user."""
        bookings = await self._booking_repo.get_user_bookings(user_id)
        logger.info(
            "user_bookings_retrieved",
            extra={"user_id": user_id, "count": len(bookings)},
        )
        return bookings

    async def cancel_booking_by_admin(
        self,
        booking_id: int,
        reason: str,
        cancelled_by: CancelledBy = CancelledBy.ADMIN,
    ) -> Booking:
        """Cancel any booking as an authenticated admin."""
        if self._session.in_transaction():
            return await self._cancel_by_admin_with_existing_transaction(
                booking_id,
                reason,
                cancelled_by,
            )

        async with self._session.begin():
            return await self._cancel_booking_by_id(booking_id, reason, cancelled_by)

    async def _cancel_by_admin_with_existing_transaction(
        self,
        booking_id: int,
        reason: str,
        cancelled_by: CancelledBy,
    ) -> Booking:
        try:
            booking = await self._cancel_booking_by_id(
                booking_id,
                reason,
                cancelled_by,
            )
            await self._session.commit()
            return booking
        except Exception:
            await self._session.rollback()
            raise

    async def cancel_booking(
        self,
        booking_id: int,
        reason: str,
        current_user: User,
        cancelled_by: CancelledBy | None = None,
    ) -> Booking:
        """Cancel a visible booking or raise a domain exception."""
        actor = cancelled_by or (
            CancelledBy.ADMIN
            if current_user.role == UserRole.ADMIN
            else CancelledBy.CUSTOMER
        )
        if self._session.in_transaction():
            return await self._cancel_with_existing_transaction(
                booking_id,
                reason,
                current_user,
                actor,
            )

        async with self._session.begin():
            return await self._cancel_visible_booking(
                booking_id,
                reason,
                current_user,
                actor,
            )

    async def _cancel_with_existing_transaction(
        self,
        booking_id: int,
        reason: str,
        current_user: User,
        cancelled_by: CancelledBy,
    ) -> Booking:
        try:
            booking = await self._cancel_visible_booking(
                booking_id,
                reason,
                current_user,
                cancelled_by,
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
        cancelled_by: CancelledBy,
    ) -> Booking:
        booking = await self._booking_repo.get_booking_by_id(booking_id)
        if booking is None or not self._can_view_booking(booking, current_user):
            logger.warning(
                "booking_not_found",
                extra={"booking_id": booking_id, "user_id": current_user.id},
            )
            raise BookingNotFoundException(booking_id)

        result = await self._booking_repo.cancel_booking(
            booking_id,
            reason,
            cancelled_by,
        )
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
