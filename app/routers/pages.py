from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.i18n import page_context, templates
from app.dependencies.booking import get_booking_service
from app.exceptions.booking_exceptions import InvalidBookingTokenException
from app.services.booking_service import BookingService
from app.utils.email_service import build_guest_links

router = APIRouter(tags=["pages"])


def _api_base(request: Request) -> str:
    """Return API base URL (no trailing slash)."""
    return str(request.base_url).rstrip("/") + "/api"


def _year() -> int:
    return datetime.now().year


def _site_base(request: Request) -> str:
    """Return site base URL (no trailing slash)."""
    return str(request.base_url).rstrip("/")


def _invalid_token_response(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "public_invalid_token.html",
        page_context(request, current_year=_year()),
        status_code=404,
    )


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request) -> HTMLResponse:
    """Trang chủ: form tìm phòng redirect sang /rooms?..."""
    return templates.TemplateResponse(
        request,
        "index.html",
        page_context(
            request,
            rooms_search_path="/rooms",
            current_year=_year(),
        ),
    )


@router.get("/rooms", response_class=HTMLResponse)
async def rooms_page(request: Request) -> HTMLResponse:
    """Danh sách phòng: JS tự đọc check_in/check_out/guests từ URLSearchParams."""
    return templates.TemplateResponse(
        request,
        "rooms.html",
        page_context(
            request,
            api_base_url=_api_base(request),
            room_detail_path="/rooms",
            current_year=_year(),
        ),
    )


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_detail_page(request: Request, room_id: int) -> HTMLResponse:
    """Chi tiết phòng. room_id PHẢI được truyền — template không có default."""
    return templates.TemplateResponse(
        request,
        "room_detail.html",
        page_context(
            request,
            api_base_url=_api_base(request),
            room_id=room_id,
            booking_confirm_path="/confirm",
            rooms_list_path="/rooms",
            mock_user_id=1,
            current_year=_year(),
        ),
    )


@router.get("/confirm", response_class=HTMLResponse)
async def booking_confirm_page(request: Request) -> HTMLResponse:
    """Xác nhận booking. booking_id được JS lấy từ URLSearchParams hoặc sessionStorage."""
    return templates.TemplateResponse(
        request,
        "booking_confirm.html",
        page_context(
            request,
            api_base_url=_api_base(request),
            current_year=_year(),
        ),
    )


@router.get("/track", response_class=HTMLResponse)
async def booking_tracking_page(request: Request) -> HTMLResponse:
    """Guest booking tracking page (no login required)."""
    return templates.TemplateResponse(
        request,
        "booking_tracking.html",
        page_context(
            request,
            api_base_url=_api_base(request),
            current_year=_year(),
        ),
    )


@router.get("/public/booking/{secure_token}", response_class=HTMLResponse)
async def public_booking_view_page(
    request: Request,
    secure_token: str,
    booking_service: BookingService = Depends(get_booking_service),
) -> HTMLResponse:
    """Token-secured view-only invoice and reservation summary."""
    try:
        booking = await booking_service.get_public_booking(secure_token)
    except InvalidBookingTokenException:
        return _invalid_token_response(request)

    base = _site_base(request)
    links = build_guest_links(base, booking.secure_token)
    payment = booking.payments[-1] if booking.payments else None

    return templates.TemplateResponse(
        request,
        "public_booking_view.html",
        page_context(
            request,
            booking=booking,
            room=booking.room,
            payment=payment,
            links=links,
            api_base_url=_api_base(request),
            secure_token=secure_token,
            current_year=_year(),
        ),
    )


@router.get("/public/booking/{secure_token}/edit", response_class=HTMLResponse)
async def public_booking_edit_page(
    request: Request,
    secure_token: str,
    booking_service: BookingService = Depends(get_booking_service),
) -> HTMLResponse:
    """Token-secured booking modification form."""
    try:
        booking = await booking_service.get_public_booking(secure_token)
    except InvalidBookingTokenException:
        return _invalid_token_response(request)

    if booking.status.value == "CANCELLED":
        return _invalid_token_response(request)

    base = _site_base(request)
    links = build_guest_links(base, booking.secure_token)

    return templates.TemplateResponse(
        request,
        "public_booking_edit.html",
        page_context(
            request,
            booking=booking,
            room=booking.room,
            links=links,
            api_base_url=_api_base(request),
            secure_token=secure_token,
            current_year=_year(),
        ),
    )


@router.get("/public/booking/{secure_token}/cancel", response_class=HTMLResponse)
async def public_booking_cancel_page(
    request: Request,
    secure_token: str,
    booking_service: BookingService = Depends(get_booking_service),
) -> HTMLResponse:
    """Token-secured cancellation confirmation form."""
    try:
        booking = await booking_service.get_public_booking(secure_token)
    except InvalidBookingTokenException:
        return _invalid_token_response(request)

    if booking.status.value == "CANCELLED":
        return _invalid_token_response(request)

    base = _site_base(request)
    links = build_guest_links(base, booking.secure_token)

    return templates.TemplateResponse(
        request,
        "public_booking_cancel.html",
        page_context(
            request,
            booking=booking,
            room=booking.room,
            links=links,
            api_base_url=_api_base(request),
            secure_token=secure_token,
            current_year=_year(),
        ),
    )

