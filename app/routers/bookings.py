from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.auth import get_current_user
from app.dependencies.booking import get_booking_service
from app.dependencies.payment import get_payment_service
from app.exceptions.booking_exceptions import (
    BookingAlreadyCancelledException,
    BookingNotFoundException,
    RoomNotAvailableException,
    RoomNotFoundException,
)
from app.exceptions.payment_exceptions import (
    PaymentAlreadyPaidException,
    PaymentAmountMismatchException,
)
from app.models.user import User, UserRole
from app.schemas.booking_schema import (
    BookingCancelRequest,
    BookingCancelResponse,
    BookingCreate,
    BookingDetailResponse,
    BookingResponse,
)
from app.schemas.payment_schema import PaymentCreate, PaymentResponse
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/{booking_id}", response_model=None)
async def get_booking_detail(
    booking_id: int,
    booking_service: BookingService = Depends(get_booking_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | JSONResponse:
    """JWT endpoint: return a booking detail visible to the caller."""
    try:
        booking = await booking_service.get_booking_detail(
            booking_id=booking_id,
            current_user=current_user,
        )
    except BookingNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking not found",
                "error_code": "BOOKING_NOT_FOUND",
            },
        )

    return {
        "success": True,
        "message": "Booking details retrieved",
        "data": BookingDetailResponse.model_validate(booking).model_dump(mode="json"),
    }


@router.patch("/{booking_id}/cancel", response_model=None)
async def cancel_booking(
    booking_id: int,
    body: BookingCancelRequest,
    booking_service: BookingService = Depends(get_booking_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | JSONResponse:
    """JWT endpoint: cancel a visible booking."""
    try:
        booking = await booking_service.cancel_booking(
            booking_id=booking_id,
            reason=body.reason,
            current_user=current_user,
        )
    except BookingNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking not found",
                "error_code": "BOOKING_NOT_FOUND",
            },
        )
    except BookingAlreadyCancelledException:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "Booking is already cancelled",
                "error_code": "BOOKING_ALREADY_CANCELLED",
            },
        )

    return {
        "success": True,
        "message": "Booking cancelled successfully",
        "data": BookingCancelResponse(
            booking_id=booking.id,
            status=booking.status.value,
            cancel_reason=body.reason,
        ).model_dump(mode="json"),
    }


@router.post("", response_model=None)
async def create_booking(
    body: BookingCreate,
    booking_service: BookingService = Depends(get_booking_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | JSONResponse:
    """JWT endpoint: create a room booking for GUEST or ADMIN callers."""
    try:
        booking = await booking_service.create_booking(
            user_id=_resolve_booking_user_id(body, current_user),
            room_id=body.room_id,
            check_in=body.check_in,
            check_out=body.check_out,
            payment_method=body.payment_method.value,
        )
    except RoomNotAvailableException:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "Room is not available for the selected dates",
                "error_code": "ROOM_NOT_AVAILABLE",
            },
        )
    except RoomNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            },
        )

    return {
        "success": True,
        "message": "Booking created successfully",
        "data": BookingResponse.model_validate(booking).model_dump(mode="json"),
    }


@router.post("/{booking_id}/payment", response_model=None)
async def process_payment(
    booking_id: int,
    body: PaymentCreate,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | JSONResponse:
    """JWT endpoint: record a payment for a booking."""
    try:
        payment = await payment_service.process_payment(
            booking_id=booking_id,
            amount=body.amount,
            payment_method=body.payment_method,
            transaction_ref=body.transaction_ref,
        )
    except BookingNotFoundException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking not found",
                "error_code": "BOOKING_NOT_FOUND",
            },
        )
    except PaymentAlreadyPaidException:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "Booking is already paid",
                "error_code": "PAYMENT_ALREADY_PAID",
            },
        )
    except PaymentAmountMismatchException as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"Payment amount mismatch: expected {e.expected}, received {e.received}",
                "error_code": "PAYMENT_AMOUNT_MISMATCH",
            },
        )

    return {
        "success": True,
        "message": "Payment recorded successfully",
        "data": PaymentResponse.model_validate(payment).model_dump(mode="json"),
    }


def _resolve_booking_user_id(body: BookingCreate, current_user: User) -> int:
    if current_user.role == UserRole.ADMIN and body.user_id is not None:
        return body.user_id
    return current_user.id
