"""SMTP email delivery for booking invoices."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings
from app.models.booking import Booking

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_DIR = _PROJECT_ROOT / "templates" / "emails"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def build_guest_links(base_url: str, secure_token: str) -> dict[str, str]:
    """Build absolute public self-service URLs for a booking."""
    base = base_url.rstrip("/")
    root = f"{base}/public/booking/{secure_token}"
    return {
        "track_url": root,
        "edit_url": f"{root}/edit",
        "cancel_url": f"{root}/cancel",
    }


def render_invoice_html(booking: Booking, base_url: str) -> str:
    """Render the HTML invoice email body for a paid booking."""
    links = build_guest_links(base_url, booking.secure_token)
    payment = booking.payments[-1] if booking.payments else None
    template = _jinja_env.get_template("invoice.html")
    return template.render(
        booking=booking,
        room=booking.room,
        payment=payment,
        links=links,
        base_url=base_url.rstrip("/"),
    )


def _send_smtp_message(to_email: str, subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP (blocking)."""
    settings = get_settings()
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], message.as_string())


async def send_booking_invoice_email(booking: Booking) -> None:
    """Send the post-payment HTML invoice email to the guest."""
    settings = get_settings()
    if not settings.SMTP_ENABLED:
        logger.info(
            "invoice_email_skipped_smtp_disabled",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
        return

    if not booking.guest_email:
        logger.warning(
            "invoice_email_skipped_no_guest_email",
            extra={"booking_id": booking.id},
        )
        return

    subject = f"Your Reservation Invoice — Ref #{booking.id}"

    try:
        html_body = render_invoice_html(booking, settings.APP_BASE_URL)
        await asyncio.to_thread(
            _send_smtp_message,
            booking.guest_email,
            subject,
            html_body,
        )
        logger.info(
            "invoice_email_sent",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
    except Exception:
        logger.exception(
            "invoice_email_failed",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )


def render_cancellation_confirmation_html(booking: Booking) -> str:
    """Render HTML for guest cancellation confirmation email (guest initiated)."""
    template = _jinja_env.get_template("cancellation_confirmation.html")
    return template.render(
        booking=booking,
        room=booking.room,
    )


def render_cancellation_notification_html(booking: Booking) -> str:
    """Render HTML for cancellation notification email (admin initiated)."""
    template = _jinja_env.get_template("cancellation_notification.html")
    return template.render(
        booking=booking,
        room=booking.room,
    )


def render_invoice_interaction_notification_html(
    booking: Booking,
    interaction_type: str,
    interaction_time: str,
) -> str:
    """Render HTML for admin notification when guest interacts with email."""
    template = _jinja_env.get_template("invoice_interaction_notification.html")
    return template.render(
        booking=booking,
        interaction_type=interaction_type,
        interaction_time=interaction_time,
    )


async def send_cancellation_confirmation_email(booking: Booking) -> None:
    """Send cancellation confirmation email to guest (when they cancel)."""
    settings = get_settings()
    if not settings.SMTP_ENABLED:
        logger.info(
            "cancellation_email_skipped_smtp_disabled",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
        return

    if not booking.guest_email:
        logger.warning(
            "cancellation_email_skipped_no_guest_email",
            extra={"booking_id": booking.id},
        )
        return

    subject = f"Booking Cancelled — Ref #{booking.id}"

    try:
        html_body = render_cancellation_confirmation_html(booking)
        await asyncio.to_thread(
            _send_smtp_message,
            booking.guest_email,
            subject,
            html_body,
        )
        logger.info(
            "cancellation_confirmation_email_sent",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
    except Exception:
        logger.exception(
            "cancellation_confirmation_email_failed",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )


async def send_cancellation_notification_email(booking: Booking) -> None:
    """Send cancellation notification email to guest (when admin cancels)."""
    settings = get_settings()
    if not settings.SMTP_ENABLED:
        logger.info(
            "cancellation_notification_email_skipped_smtp_disabled",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
        return

    if not booking.guest_email:
        logger.warning(
            "cancellation_notification_email_skipped_no_guest_email",
            extra={"booking_id": booking.id},
        )
        return

    subject = f"Your Reservation Has Been Cancelled — Ref #{booking.id}"

    try:
        html_body = render_cancellation_notification_html(booking)
        await asyncio.to_thread(
            _send_smtp_message,
            booking.guest_email,
            subject,
            html_body,
        )
        logger.info(
            "cancellation_notification_email_sent",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
    except Exception:
        logger.exception(
            "cancellation_notification_email_failed",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )


async def send_invoice_for_booking_id(booking_id: int) -> None:
    """Background-task entry point: load booking in a fresh session and send invoice."""
    from app.database import AsyncSessionLocal
    from app.repositories.booking_repository import BookingRepository

    async with AsyncSessionLocal() as session:
        repo = BookingRepository(session)
        booking = await repo.get_booking_by_id(booking_id)
        if booking is None:
            logger.warning(
                "invoice_email_booking_not_found",
                extra={"booking_id": booking_id},
            )
            return
        await send_booking_invoice_email(booking)


async def send_cancellation_confirmation_for_booking_id(booking_id: int) -> None:
    """Background-task entry point: send cancellation confirmation email."""
    from app.database import AsyncSessionLocal
    from app.repositories.booking_repository import BookingRepository
    from app.repositories.notification_log_repository import NotificationLogRepository
    from app.models.notification_log import InteractionType

    logger.info(f"Background task started: send_cancellation_confirmation_for_booking_id({booking_id})")
    
    async with AsyncSessionLocal() as session:
        repo = BookingRepository(session)
        booking = await repo.get_booking_by_id(booking_id)
        if booking is None:
            logger.warning(
                "cancellation_email_booking_not_found",
                extra={"booking_id": booking_id},
            )
            return
        logger.info(f"Background task: sending cancellation confirmation email to {booking.guest_email}")
        await send_cancellation_confirmation_email(booking)
        
        # Log the notification
        try:
            notification_repo = NotificationLogRepository(session)
            await notification_repo.create_log(
                booking_id=booking_id,
                interaction_type=InteractionType.BOOKING_CANCELLED_BY_GUEST,
                guest_name=booking.guest_name or "Unknown",
                message=f"Guest cancelled booking #{booking_id}. Confirmation email sent to {booking.guest_email}",
                action="cancel",
            )
            await session.commit()
            logger.info(f"Background task: notification log saved for booking {booking_id}")
        except Exception as e:
            logger.exception(f"Background task: failed to save notification log - {e}")


async def send_cancellation_notification_for_booking_id(booking_id: int) -> None:
    """Background-task entry point: send cancellation notification email (admin action)."""
    from app.database import AsyncSessionLocal
    from app.repositories.booking_repository import BookingRepository
    from app.repositories.notification_log_repository import NotificationLogRepository
    from app.models.notification_log import InteractionType

    logger.info(f"Background task started: send_cancellation_notification_for_booking_id({booking_id})")
    
    async with AsyncSessionLocal() as session:
        repo = BookingRepository(session)
        booking = await repo.get_booking_by_id(booking_id)
        if booking is None:
            logger.warning(
                "cancellation_notification_email_booking_not_found",
                extra={"booking_id": booking_id},
            )
            return
        logger.info(f"Background task: sending cancellation notification email to {booking.guest_email}")
        await send_cancellation_notification_email(booking)
        
        # Log the notification
        try:
            notification_repo = NotificationLogRepository(session)
            await notification_repo.create_log(
                booking_id=booking_id,
                interaction_type=InteractionType.BOOKING_CANCELLED_BY_ADMIN,
                guest_name=booking.guest_name or "Unknown",
                message=f"Admin cancelled booking #{booking_id}. Notification email sent to {booking.guest_email}",
                action="cancel",
            )
            await session.commit()
            logger.info(f"Background task: notification log saved for booking {booking_id}")
        except Exception as e:
            logger.exception(f"Background task: failed to save notification log - {e}")


def render_booking_change_result_html(booking: Booking, action: str) -> str:
    """Render HTML for booking change result email (approval or rejection)."""
    template = _jinja_env.get_template("booking_change_result.html")
    return template.render(
        booking=booking,
        room=booking.room,
        action=action.upper(),
    )


async def send_booking_change_result_email_internal(booking: Booking, action: str) -> None:
    """Send booking change result email to guest (internal implementation)."""
    settings = get_settings()
    if not settings.SMTP_ENABLED:
        logger.info(
            "booking_change_result_email_skipped_smtp_disabled",
            extra={"booking_id": booking.id, "guest_email": booking.guest_email},
        )
        return

    if not booking.guest_email:
        logger.warning(
            "booking_change_result_email_skipped_no_guest_email",
            extra={"booking_id": booking.id},
        )
        return

    action_upper = action.upper()
    if action_upper == "APPROVE":
        subject = f"[Residences] Thông báo kết quả yêu cầu thay đổi ngày đặt phòng đơn #{booking.id} - Phê duyệt"
    else:
        subject = f"[Residences] Thông báo kết quả yêu cầu thay đổi ngày đặt phòng đơn #{booking.id} - Từ chối"

    try:
        html_body = render_booking_change_result_html(booking, action)
        await asyncio.to_thread(
            _send_smtp_message,
            booking.guest_email,
            subject,
            html_body,
        )
        logger.info(
            "booking_change_result_email_sent",
            extra={
                "booking_id": booking.id,
                "guest_email": booking.guest_email,
                "action": action_upper,
            },
        )
    except Exception:
        logger.exception(
            "booking_change_result_email_failed",
            extra={
                "booking_id": booking.id,
                "guest_email": booking.guest_email,
                "action": action_upper,
            },
        )


async def send_booking_change_result_email(booking_id: int, action: str) -> None:
    """Background-task entry point: send booking change result email to guest."""
    from app.database import AsyncSessionLocal
    from app.repositories.booking_repository import BookingRepository
    from app.repositories.notification_log_repository import NotificationLogRepository
    from app.models.notification_log import InteractionType

    logger.info(
        f"Background task started: send_booking_change_result_email({booking_id}, {action})"
    )

    async with AsyncSessionLocal() as session:
        repo = BookingRepository(session)
        booking = await repo.get_booking_by_id(booking_id)
        if booking is None:
            logger.warning(
                "booking_change_result_email_booking_not_found",
                extra={"booking_id": booking_id},
            )
            return

        logger.info(
            f"Background task: sending booking change result email to {booking.guest_email}"
        )
        await send_booking_change_result_email_internal(booking, action)

        # Log the notification
        try:
            notification_repo = NotificationLogRepository(session)
            action_text = "phê duyệt" if action.upper() == "APPROVE" else "từ chối"
            await notification_repo.create_log(
                booking_id=booking_id,
                interaction_type=(
                    InteractionType.LINK_CLICK_EDIT
                    if action.upper() == "APPROVE"
                    else InteractionType.LINK_CLICK_CANCEL
                ),
                guest_name=booking.guest_name or "Unknown",
                message=f"Admin đã {action_text} yêu cầu đổi ngày cho booking #{booking_id}. Email thông báo đã gửi tới {booking.guest_email}",
                action="review_change",
            )
            await session.commit()
            logger.info(
                f"Background task: notification log saved for booking {booking_id}"
            )
        except Exception as e:
            logger.exception(
                f"Background task: failed to save notification log - {e}"
            )
