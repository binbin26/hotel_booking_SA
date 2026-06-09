from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings
from app.core.i18n import page_context, templates
from app.dependencies.admin import get_admin_auth_service, get_current_admin_or_none
from app.exceptions.auth_exceptions import InvalidCredentialsException
from app.models.admin_model import AdminUser
from app.services.admin_auth_service import AdminAuthService

router = APIRouter(prefix="/admin", tags=["admin"])


def _year() -> int:
    return datetime.now().year


@router.get("/login", response_class=HTMLResponse, response_model=None)
async def admin_login_page(
    request: Request,
    current_admin: AdminUser | None = Depends(get_current_admin_or_none),
) -> HTMLResponse | RedirectResponse:
    """Render the admin portal login form."""
    if current_admin is not None:
        return RedirectResponse(
            url="/admin/dashboard",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request,
        "admin/login.html",
        page_context(request, current_year=_year()),
    )


@router.post("/login", response_class=HTMLResponse, response_model=None)
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> HTMLResponse | RedirectResponse:
    """Authenticate admin credentials and set an HttpOnly session cookie."""
    settings = get_settings()

    try:
        result = await admin_auth_service.authenticate(username, password)
    except InvalidCredentialsException:
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            page_context(
                request,
                current_year=_year(),
                error_message="Invalid username or password",
                username=username,
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(
        url="/admin/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key=settings.ADMIN_TOKEN_COOKIE_NAME,
        value=result.access_token,
        max_age=settings.ADMIN_TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.ADMIN_COOKIE_SECURE,
        path="/",
    )
    return response


@router.get("/dashboard", response_class=HTMLResponse, response_model=None)
async def admin_dashboard_page(
    request: Request,
    current_admin: AdminUser | None = Depends(get_current_admin_or_none),
) -> HTMLResponse | RedirectResponse:
    """Render the protected admin management dashboard."""
    if current_admin is None:
        return RedirectResponse(
            url="/admin/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        page_context(
            request,
            api_base_url=str(request.base_url).rstrip("/") + "/api",
            admin_bookings_path="/admin/bookings",
            admin_name=current_admin.username,
            current_year=_year(),
        ),
    )


@router.get("", include_in_schema=False, response_model=None)
async def admin_root() -> RedirectResponse:
    """Redirect bare /admin to the login page."""
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
