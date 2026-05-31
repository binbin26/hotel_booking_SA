from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle FastAPI HTTPException with a JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def value_error_handler(
    request: Request,
    exc: ValueError,
) -> JSONResponse:
    """Handle ValueError as a 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
