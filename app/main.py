from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_babel import BabelMiddleware

from app.config import get_settings
from app.core.i18n import babel_configs, locale_selector, templates
from app.exceptions.handlers import register_exception_handlers
from app.routers import admin_router, auth, bookings, health, language, pages, rooms

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    BabelMiddleware,
    babel_configs=babel_configs,
    jinja2_templates=templates,
    locale_selector=locale_selector,
)

register_exception_handlers(app)

# ── API routers (prefix="/api" để tách biệt với page routes) ──────────────
app.include_router(health.router)                         # /health — giữ nguyên
app.include_router(language.router, prefix="/api")          # /api/language
app.include_router(auth.router, prefix="/api")            # /api/auth/me
app.include_router(rooms.router, prefix="/api")           # /api/rooms/search, /api/rooms/{id}
app.include_router(rooms.admin_router, prefix="/api")     # /api/admin/rooms/{id}
app.include_router(bookings.router, prefix="/api")        # /api/bookings/...
app.include_router(bookings.admin_router, prefix="/api")  # /api/admin/bookings

# ── Admin portal (Jinja2 pages + form login) ───────────────────────────────
app.include_router(admin_router.router)                   # /admin/login, /admin/dashboard

# ── Page routes — PHẢI đứng sau tất cả API routers ────────────────────────
app.include_router(pages.router)                          # /, /rooms, /rooms/{id}, /confirm
