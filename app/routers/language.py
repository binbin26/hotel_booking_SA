from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.language_schema import LanguageUpdateRequest, LanguageUpdateResponse

router = APIRouter(prefix="/language", tags=["language"])


@router.post("", response_model=LanguageUpdateResponse)
async def set_language(
    request: Request,
    body: LanguageUpdateRequest,
) -> JSONResponse:
    """
    Switch UI language and persist choice in a cookie.

    Frontend should reload the page (or re-fetch data) after a successful call.
    """
    settings = get_settings()
    language = body.language.strip().lower()

    if language not in settings.SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_LANGUAGE",
                "message": f"Language '{language}' is not supported.",
                "supported": settings.SUPPORTED_LOCALES,
            },
        )

    response = JSONResponse(
        content=LanguageUpdateResponse(language=language).model_dump(),
    )
    response.set_cookie(
        key=settings.LANGUAGE_COOKIE_NAME,
        value=language,
        max_age=settings.LANGUAGE_COOKIE_MAX_AGE,
        httponly=False,
        samesite="lax",
    )
    return response
