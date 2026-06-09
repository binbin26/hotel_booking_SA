"""Unit tests for invoice email delivery."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings, get_settings
from app.models.booking import Booking, BookingStatus, PaymentMethod
from app.models.payment import Payment, PaymentStatus
from app.models.room import Room, RoomStatus, RoomType
from app.utils import email_service


def _make_booking() -> Booking:
    room = Room(
        id=1,
        room_number="101",
        room_type=RoomType.STANDARD,
        capacity=2,
        price_per_night=Decimal("100.00"),
        status=RoomStatus.AVAILABLE,
    )
    payment = Payment(
        id=1,
        booking_id=42,
        amount=Decimal("200.00"),
        payment_method="MOMO",
        status=PaymentStatus.PAID,
    )
    booking = Booking(
        id=42,
        room_id=1,
        check_in=date(2026, 6, 10),
        check_out=date(2026, 6, 12),
        total_nights=2,
        total_price=Decimal("200.00"),
        status=BookingStatus.CONFIRMED,
        payment_method=PaymentMethod.MOMO,
        guest_name="Test Guest",
        guest_email="guest@example.com",
        secure_token="abc123securetoken",
    )
    booking.room = room
    booking.payments = [payment]
    return booking


@pytest.fixture
def smtp_settings() -> Settings:
    return Settings(
        DATABASE_URL="mysql+aiomysql://user:pass@localhost:3306/test",
        SECRET_KEY="test-secret",
        SMTP_ENABLED=True,
        SMTP_HOST="localhost",
        SMTP_PORT=1025,
        SMTP_USER="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="noreply@hotel.local",
        SMTP_USE_TLS=False,
        APP_BASE_URL="http://localhost:8000",
    )


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_send_invoice_for_booking_id_loads_renders_and_sends(
    mocker,
    smtp_settings: Settings,
) -> None:
    booking = _make_booking()
    mock_repo = MagicMock()
    mock_repo.get_booking_by_id = AsyncMock(return_value=booking)

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_smtp_server = MagicMock()
    mock_smtp_cls = mocker.patch("app.utils.email_service.smtplib.SMTP")
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=None)

    mocker.patch("app.utils.email_service.get_settings", return_value=smtp_settings)
    mocker.patch("app.database.AsyncSessionLocal", return_value=mock_session)
    mocker.patch(
        "app.repositories.booking_repository.BookingRepository",
        return_value=mock_repo,
    )

    render_spy = mocker.spy(email_service, "render_invoice_html")

    await email_service.send_invoice_for_booking_id(42)

    mock_repo.get_booking_by_id.assert_awaited_once_with(42)
    render_spy.assert_called_once_with(booking, smtp_settings.APP_BASE_URL)

    mock_smtp_cls.assert_called_once_with(
        smtp_settings.SMTP_HOST,
        smtp_settings.SMTP_PORT,
        timeout=30,
    )
    mock_smtp_server.sendmail.assert_called_once()
    sendmail_args = mock_smtp_server.sendmail.call_args[0]
    assert sendmail_args[0] == smtp_settings.SMTP_FROM_EMAIL
    assert sendmail_args[1] == [booking.guest_email]
    # MIME body is base64-encoded; render_spy above already asserts HTML was built.
    assert booking.guest_email in sendmail_args[2]


@pytest.mark.asyncio
async def test_send_invoice_for_booking_id_skips_when_booking_missing(
    mocker,
    smtp_settings: Settings,
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_booking_by_id = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_smtp_cls = mocker.patch("app.utils.email_service.smtplib.SMTP")
    mocker.patch("app.utils.email_service.get_settings", return_value=smtp_settings)
    mocker.patch("app.database.AsyncSessionLocal", return_value=mock_session)
    mocker.patch(
        "app.repositories.booking_repository.BookingRepository",
        return_value=mock_repo,
    )
    render_spy = mocker.spy(email_service, "render_invoice_html")

    await email_service.send_invoice_for_booking_id(99)

    mock_repo.get_booking_by_id.assert_awaited_once_with(99)
    render_spy.assert_not_called()
    mock_smtp_cls.assert_not_called()


@pytest.mark.asyncio
async def test_send_booking_invoice_email_logs_failure_on_render_error(
    mocker,
    smtp_settings: Settings,
) -> None:
    booking = _make_booking()
    mocker.patch("app.utils.email_service.get_settings", return_value=smtp_settings)
    mocker.patch(
        "app.utils.email_service.render_invoice_html",
        side_effect=RuntimeError("template error"),
    )
    mock_smtp_cls = mocker.patch("app.utils.email_service.smtplib.SMTP")
    mock_logger = mocker.patch("app.utils.email_service.logger")

    await email_service.send_booking_invoice_email(booking)

    mock_smtp_cls.assert_not_called()
    mock_logger.exception.assert_called_once()
    assert mock_logger.exception.call_args[0][0] == "invoice_email_failed"
