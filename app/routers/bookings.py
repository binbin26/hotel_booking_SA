from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.database import get_db
from app.dependencies.admin import get_current_admin, get_current_admin_or_none
from app.dependencies.auth import get_current_user
from app.dependencies.booking import get_booking_service
from app.dependencies.payment import get_payment_service
from app.exceptions.booking_exceptions import (
    BookingAlreadyCancelledException,
    BookingNotFoundException,
    InvalidBookingTokenException,
    RoomNotAvailableException,
    RoomNotFoundException,
)
from app.utils.email_service import (
    send_invoice_for_booking_id,
    send_cancellation_confirmation_for_booking_id,
    send_cancellation_notification_for_booking_id,
    send_booking_change_result_email,
)
from app.utils.realtime_notifications import (
    notification_stream,
    broadcast_notification,
    NotificationEvent,
)
from app.exceptions.payment_exceptions import (
    PaymentAlreadyPaidException,
    PaymentAmountMismatchException,
)
from app.models.admin_model import AdminUser
from app.models.user import User, UserRole
from app.models.booking import Booking, CancelledBy as CancelledByEnum
from app.schemas.booking_schema import (
    AdminBookingCancelRequest,
    AdminBookingListItemResponse,
    AdminChangeResponseRequest,
    BookingCancelRequest,
    BookingCancelResponse,
    BookingCreate,
    BookingDetailResponse,
    BookingResponse,
    GuestChangeDatesRequest,
)
from app.schemas.payment_schema import PaymentCreate, PaymentResponse
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/bookings", tags=["bookings"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _build_cancel_response(booking: Booking) -> BookingCancelResponse:
    """Map a cancelled booking ORM row to the public cancel response shape."""
    cancelled_by = booking.cancelled_by
    if cancelled_by is not None and hasattr(cancelled_by, "value"):
        cancelled_by = cancelled_by.value
        
    # SỬA TẠI ĐÂY: Kiểm tra xem status có thuộc tính .value hay không
    status_val = booking.status.value if hasattr(booking.status, "value") else booking.status
    
    return BookingCancelResponse(
        status=str(status_val or ""),
        cancel_reason=booking.cancel_reason or "",
        cancelled_by=str(cancelled_by or ""),
    )


@admin_router.get("/bookings", response_model=None)
async def admin_get_all_bookings(
    current_admin: AdminUser | None = Depends(get_current_admin_or_none),
    booking_service: BookingService = Depends(get_booking_service),
) -> dict[str, Any]:
    """Admin session endpoint: return all bookings for authenticated admin."""
    if current_admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
    bookings = await booking_service.get_all_bookings()
    bookings_data = []
    for booking in bookings:
        booking_dict = AdminBookingListItemResponse.model_validate(booking).model_dump(mode="json")
        # Bơm thêm dữ liệu ngày mong muốn vào response
        booking_dict["requested_check_in"] = booking.requested_check_in.isoformat() if getattr(booking, "requested_check_in", None) else None
        booking_dict["requested_check_out"] = booking.requested_check_out.isoformat() if getattr(booking, "requested_check_out", None) else None
        bookings_data.append(booking_dict)

    return {
        "success": True,
        "data": bookings_data,
    }


@admin_router.get("/notifications/stream", response_class=StreamingResponse)
async def stream_admin_notifications(
    current_admin: AdminUser = Depends(get_current_admin),
) -> StreamingResponse:
    """Admin endpoint: Server-Sent Events stream for real-time notifications."""
    
    async def event_generator():
        async for event in notification_stream(current_admin.id):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@admin_router.get("/notifications", response_model=None)
async def get_admin_notifications(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
) -> dict[str, Any]:
    """Admin endpoint: get recent notification logs."""
    from app.repositories.notification_log_repository import NotificationLogRepository
    
    repo = NotificationLogRepository(db)
    logs = await repo.get_recent_logs(limit=limit)
    
    logs_data = [
        {
            "id": log.id,
            "booking_id": log.booking_id,
            # SỬA TẠI ĐÂY: Kiểm tra thuộc tính .value một cách an toàn
            "interaction_type": log.interaction_type.value if hasattr(log.interaction_type, "value") else log.interaction_type,
            "guest_name": log.guest_name,
            "message": log.message,
            "action": log.action,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    
    return {
        "success": True,
        "data": logs_data,
        "count": len(logs_data),
    }


@admin_router.patch("/bookings/{booking_id}/cancel", response_model=None)
async def admin_cancel_booking(
    booking_id: int,
    body: AdminBookingCancelRequest,
    background_tasks: BackgroundTasks,
    current_admin: AdminUser = Depends(get_current_admin),
    booking_service: BookingService = Depends(get_booking_service),
) -> dict[str, Any] | JSONResponse:
    """Admin session endpoint: cancel any booking."""
    _ = current_admin
    try:
        # SỬA TẠI ĐÂY: Lấy giá trị an toàn dù body truyền vào là chuỗi hay enum
        c_by_val = body.cancelled_by.value if hasattr(body.cancelled_by, "value") else body.cancelled_by
        
        booking = await booking_service.cancel_booking_by_admin(
            booking_id=booking_id,
            reason=body.reason,
            cancelled_by=CancelledByEnum(c_by_val),
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
            status_code=400,
            content={
                "success": False,
                "message": "Booking is already cancelled",
                "error_code": "BOOKING_ALREADY_CANCELLED",
            },
        )

    # Send cancellation notification email to guest
    import asyncio
    import logging
    logger = logging.getLogger(__name__)
    
    if background_tasks:
        logger.info(f"Admin cancel booking {booking_id}: adding background task to send email")
        background_tasks.add_task(send_cancellation_notification_for_booking_id, booking_id)
    else:
        logger.warning(f"Admin cancel booking {booking_id}: background_tasks is None, email may not be sent")
    
    # Broadcast real-time notification to all admins
    notification = NotificationEvent(
        event_type="booking_cancelled_by_admin",
        booking_id=booking_id,
        guest_name=booking.guest_name,
        message=f"Booking #{booking_id} has been cancelled by admin. Guest notification sent.",
        action="view",
    )
    # Fire and forget - don't wait for broadcast
    try:
        asyncio.create_task(broadcast_notification(notification))
        logger.info(f"Admin cancel booking {booking_id}: notification broadcast queued")
    except Exception as e:
        logger.error(f"Admin cancel booking {booking_id}: failed to broadcast notification - {e}")

    return {
        "success": True,
        "message": "Reservation cancelled successfully",
        "data": _build_cancel_response(booking).model_dump(mode="json"),
    }


@router.get("", response_model=None)
async def get_bookings(
    booking_service: BookingService = Depends(get_booking_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """JWT endpoint: return user's own bookings (for GUEST users)."""
    bookings = await booking_service.get_user_bookings(current_user.id)

    bookings_data = [
        BookingResponse.model_validate(booking).model_dump(mode="json")
        for booking in bookings
    ]

    return {
        "success": True,
        "message": "Bookings retrieved successfully",
        "data": bookings_data,
    }


@router.get("/track", response_model=None)
async def track_guest_booking(
    booking_id: int,
    guest_email: str,
    booking_service: BookingService = Depends(get_booking_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: track a guest booking by reference number and email."""
    try:
        booking = await booking_service.track_guest_booking(
            booking_id=booking_id,
            guest_email=guest_email,
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


@router.post("/public/{secure_token}/cancel", response_model=None)
async def cancel_booking_by_token(
    secure_token: str,
    body: BookingCancelRequest,
    background_tasks: BackgroundTasks,
    booking_service: BookingService = Depends(get_booking_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: cancel a booking using its secure guest token."""
    try:
        booking = await booking_service.cancel_booking_by_token(
            token=secure_token,
            reason=body.reason,
        )
    except InvalidBookingTokenException:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking link is expired or invalid",
                "error_code": "INVALID_BOOKING_TOKEN",
            },
        )
    except BookingAlreadyCancelledException:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Booking is already cancelled",
                "error_code": "BOOKING_ALREADY_CANCELLED",
            },
        )

    # Send cancellation confirmation email to guest
    import asyncio
    import logging
    logger = logging.getLogger(__name__)
    
    if background_tasks:
        logger.info(f"Guest cancel booking {booking.id}: adding background task to send email")
        background_tasks.add_task(send_cancellation_confirmation_for_booking_id, booking.id)
    else:
        logger.warning(f"Guest cancel booking {booking.id}: background_tasks is None, email may not be sent")
    
    # Broadcast notification to admins
    notification = NotificationEvent(
        event_type="booking_cancelled_by_guest",
        booking_id=booking.id,
        guest_name=booking.guest_name,
        message=f"Guest {booking.guest_name} cancelled booking #{booking.id}. Confirmation email sent.",
        action="view",
    )
    try:
        asyncio.create_task(broadcast_notification(notification))
        logger.info(f"Guest cancel booking {booking.id}: notification broadcast queued")
    except Exception as e:
        logger.error(f"Guest cancel booking {booking.id}: failed to broadcast notification - {e}")

    return {
        "success": True,
        "message": "Reservation cancelled successfully",
        "data": _build_cancel_response(booking).model_dump(mode="json"),
    }


@router.post("/public/{secure_token}/change-request", response_model=None)
async def request_booking_change_by_token(
    secure_token: str,
    body: GuestChangeDatesRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: Guest requests to change check-in/out dates."""
    try:
        # 1. Tìm đơn đặt phòng bằng secure_token
        result = await db.execute(
            select(Booking).where(Booking.secure_token == secure_token)
        )
        booking = result.scalars().first()
        
        if not booking:
            return JSONResponse(
                status_code=404, 
                content={"success": False, "message": "Yêu cầu không hợp lệ hoặc liên kết hết hạn."}
            )

        # 2. Lưu ngày mong muốn của khách vào bảng bookings
        booking.requested_check_in = body.check_in
        booking.requested_check_out = body.check_out
        
        # 3. CHÍNH LÀ ĐOẠN NÀY: Lưu thông tin tương tác vào bảng lịch sử thông báo (notification_logs)
        from app.repositories.notification_log_repository import NotificationLogRepository
        from app.models.notification_log import InteractionType
        
        repo = NotificationLogRepository(db)
        await repo.create_log(
            booking_id=booking.id,
            interaction_type=InteractionType.LINK_CLICK_EDIT,  # Sử dụng enum tương tác sửa đổi sẵn có
            guest_name=booking.guest_name or "Unknown",
            message=f"Khách hàng yêu cầu đổi ngày đặt phòng thành: {body.check_in} -> {body.check_out}",
            action="review_change"  # Đánh dấu hành động để frontend nhận diện và cho phép click xử lý
        )
        
        # Commit toàn bộ thay đổi vào MariaDB
        await db.commit()

        # 4. Phát thông báo thời gian thực (SSE) tới Admin Dashboard
        import asyncio
        from app.utils.realtime_notifications import NotificationEvent, broadcast_notification
        
        notification = NotificationEvent(
            event_type="booking_change_requested",
            booking_id=booking.id,
            guest_name=booking.guest_name,
            message=f"Khách hàng {booking.guest_name} yêu cầu đổi ngày: {body.check_in} -> {body.check_out}",
            action="review_change",
        )
        asyncio.create_task(broadcast_notification(notification))

        return {
            "success": True,
            "message": "Yêu cầu thay đổi ngày đã được lưu và gửi tới quản trị viên."
        }
        
    except Exception as e:
        await db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Lỗi lưu thông báo đổi ngày: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Lỗi hệ thống: {str(e)}"}
        )


@admin_router.post("/bookings/{booking_id}/change-response", response_model=None)
async def handle_booking_change_response(
    booking_id: int,
    body: AdminChangeResponseRequest,
    background_tasks: BackgroundTasks,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """
    Admin endpoint: Approve or reject guest's date change request.
    
    Updates booking dates in database when action is "APPROVE"
    and sends email notification to guest (both APPROVE and REJECT).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Lấy booking từ database
        result = await db.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalars().first()
        
        if booking is None:
            raise BookingNotFoundException(booking_id)
        
        action = body.action.upper()
        
        # Validate action
        if action not in ("APPROVE", "REJECT"):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Hành động không hợp lệ. Chỉ chấp nhận APPROVE hoặc REJECT.",
                    "error_code": "INVALID_ACTION",
                },
            )
        
        if action == "APPROVE":
            # Cập nhật ngày check-in và check-out bằng ngày yêu cầu
            if booking.requested_check_in and booking.requested_check_out:
                booking.check_in = booking.requested_check_in
                booking.check_out = booking.requested_check_out
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Không tìm thấy thông tin ngày mới cần phê duyệt.",
                        "error_code": "MISSING_REQUESTED_DATES",
                    },
                )
        
        # Xóa dữ liệu yêu cầu đổi ngày (dù APPROVE hay REJECT)
        booking.requested_check_in = None
        booking.requested_check_out = None
        
        # Commit thay đổi vào database
        await db.commit()
        
        # Thêm background task gửi email kết quả cho khách hàng
        background_tasks.add_task(
            send_booking_change_result_email,
            booking_id,
            action
        )
        
        logger.info(f"Admin {current_admin.id} processed change request for booking {booking_id}: {action}")
        
        return {
            "success": True,
            "message": f"Yêu cầu đổi ngày đã được {('phê duyệt' if action == 'APPROVE' else 'từ chối')}",
            "data": {
                "booking_id": booking_id,
                "action": action,
            },
        }
        
    except BookingNotFoundException:
        logger.warning(f"Booking {booking_id} not found")
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking not found",
                "error_code": "BOOKING_NOT_FOUND",
            },
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error processing change response for booking {booking_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Lỗi hệ thống: {str(e)}",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )


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
    current_admin: AdminUser | None = Depends(get_current_admin_or_none),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """Cancel a booking via admin session cookie or JWT bearer token."""
    try:
        if current_admin is not None:
            c_by_val = body.cancelled_by.value if hasattr(body.cancelled_by, "value") else body.cancelled_by
            cancelled_by = CancelledByEnum(c_by_val)
            if cancelled_by != CancelledByEnum.ADMIN:
                cancelled_by = CancelledByEnum.ADMIN
            booking = await booking_service.cancel_booking_by_admin(
                booking_id=booking_id,
                reason=body.reason,
                cancelled_by=cancelled_by,
            )
        else:
            if credentials is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            try:
                payload = verify_token(credentials.credentials)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc

            current_user = await db.get(User, payload.sub)
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            booking = await booking_service.cancel_booking(
                booking_id=booking_id,
                reason=body.reason,
                current_user=current_user,
                cancelled_by=CancelledByEnum(body.cancelled_by.value),
            )
    except HTTPException:
        raise
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
            status_code=400,
            content={
                "success": False,
                "message": "Booking is already cancelled",
                "error_code": "BOOKING_ALREADY_CANCELLED",
            },
        )

    return {
        "success": True,
        "message": "Reservation cancelled successfully",
        "data": _build_cancel_response(booking).model_dump(mode="json"),
    }


@router.post("", response_model=None)
async def create_booking(
    body: BookingCreate,
    booking_service: BookingService = Depends(get_booking_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: create a room booking for guest checkout (no login required)."""
    try:
        booking = await booking_service.create_booking(
            room_id=body.room_id,
            check_in=body.check_in,
            check_out=body.check_out,
            payment_method=body.payment_method.value,
            user_id=None,
            guest_name=body.guest_name,
            guest_email=body.guest_email,
            guest_phone=body.guest_phone,
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
    background_tasks: BackgroundTasks,
    payment_service: PaymentService = Depends(get_payment_service),
) -> dict[str, Any] | JSONResponse:
    """Public endpoint: record a payment for a booking (no login required)."""
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

    background_tasks.add_task(send_invoice_for_booking_id, booking_id)

    return {
        "success": True,
        "message": "Payment recorded successfully",
        "data": PaymentResponse.model_validate(payment).model_dump(mode="json"),
    }


@router.get("/{booking_id}/invoice-interaction", response_model=None)
@router.post("/{booking_id}/invoice-interaction", response_model=None)
async def record_invoice_interaction(
    booking_id: int,
    background_tasks: BackgroundTasks,
    action: str = "track",
    booking_service: BookingService = Depends(get_booking_service),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """
    Webhook endpoint: record guest interaction with invoice email.
    
    Supports both GET (for tracking pixels) and POST (for direct calls).
    Called when guest clicks action links in their email (track, edit, cancel, open).
    Broadcasts real-time notification to admin dashboard and logs interaction.
    """
    try:
        booking = await booking_service.get_booking_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundException(booking_id)
    except BookingNotFoundException:
        # Return 1x1 pixel for tracking endpoints
        if action == "open":
            import base64
            pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
            from fastapi.responses import Response
            return Response(content=pixel, media_type="image/png")
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Booking not found",
                "error_code": "BOOKING_NOT_FOUND",
            },
        )

    # Broadcast notification to admins
    action_labels = {
        "track": "viewed booking details",
        "edit": "started editing booking",
        "cancel": "started cancellation process",
        "open": "opened invoice email",
    }
    action_label = action_labels.get(action, action)

    notification = NotificationEvent(
        event_type="invoice_interaction",
        booking_id=booking_id,
        guest_name=booking.guest_name,
        message=f"Guest {booking.guest_name} {action_label} for booking #{booking_id}",
        action=action,
    )
    
    # Fire and forget - don't wait for broadcast
    import asyncio
    import logging
    logger_routers = logging.getLogger(__name__)
    
    try:
        asyncio.create_task(broadcast_notification(notification))
        logger_routers.info(f"Guest interaction recorded: booking {booking_id}, action {action}")
    except Exception as e:
        logger_routers.error(f"Failed to broadcast notification for guest interaction: {e}")
    
    # Save interaction to database
    if background_tasks:
        background_tasks.add_task(save_interaction_log, booking_id, action, booking.guest_name)

    # Return 1x1 pixel for tracking endpoints
    if action == "open":
        import base64
        pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        from fastapi.responses import Response
        return Response(content=pixel, media_type="image/png")

    return {
        "success": True,
        "message": "Interaction recorded",
        "data": {"booking_id": booking_id, "action": action},
    }


async def save_interaction_log(booking_id: int, action: str, guest_name: str) -> None:
    """Background task to save guest interaction log to database."""
    from app.database import AsyncSessionLocal
    from app.repositories.notification_log_repository import NotificationLogRepository
    from app.models.notification_log import InteractionType
    
    import logging
    logger_task = logging.getLogger(__name__)
    
    # Map action to interaction type
    action_to_type_map = {
        "track": InteractionType.LINK_CLICK_VIEW,
        "edit": InteractionType.LINK_CLICK_EDIT,
        "cancel": InteractionType.LINK_CLICK_CANCEL,
        "open": InteractionType.EMAIL_OPEN,
    }
    interaction_type = action_to_type_map.get(action, InteractionType.INVOICE_INTERACTION)
    
    try:
        async with AsyncSessionLocal() as session:
            repo = NotificationLogRepository(session)
            await repo.create_log(
                booking_id=booking_id,
                interaction_type=interaction_type,
                guest_name=guest_name or "Unknown",
                message=f"Guest {guest_name} {action_to_type_map.get(action, 'interacted')} with booking #{booking_id}",
                action=action,
            )
            await session.commit()
            logger_task.info(f"Saved interaction log for booking {booking_id}: action={action}")
    except Exception as e:
        logger_task.error(f"Failed to save interaction log for booking {booking_id}: {e}")
