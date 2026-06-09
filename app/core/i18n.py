"""Babel / gettext setup: locale resolution, Jinja2 templates, JS translation dict."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi_babel import BabelConfigs, _

from app.core.config import get_settings

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_settings = get_settings()

babel_configs = BabelConfigs(
    ROOT_DIR=str(_PROJECT_ROOT / "babel.py"),
    BABEL_DEFAULT_LOCALE=_settings.BABEL_DEFAULT_LOCALE,
    BABEL_TRANSLATION_DIRECTORY=_settings.BABEL_TRANSLATION_DIRECTORY,
)

templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))
templates.env.globals.update(_=_)


def resolve_locale_from_accept_language(
    accept_language: str | None,
    supported: frozenset[str],
    default: str,
) -> str:
    """Pick the best supported locale from an Accept-Language header value."""
    if not accept_language:
        return default

    candidates: list[tuple[str, float]] = []
    for part in accept_language.split(","):
        part = part.strip()
        if not part:
            continue
        if ";q=" in part:
            lang, _, q = part.partition(";q=")
            try:
                quality = float(q.strip())
            except ValueError:
                quality = 1.0
        else:
            lang = part
            quality = 1.0

        lang = lang.strip().lower()
        base = lang.split("-")[0]
        for code in (lang, base):
            if code in supported:
                candidates.append((code, quality))
                break

    if not candidates:
        return default

    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def locale_selector(request: Request) -> str:
    """
    Resolve request locale: cookie first, then Accept-Language, then default.
    """
    settings = get_settings()
    supported = frozenset(settings.SUPPORTED_LOCALES)

    cookie_locale = request.cookies.get(settings.LANGUAGE_COOKIE_NAME)
    if cookie_locale and cookie_locale in supported:
        return cookie_locale

    return resolve_locale_from_accept_language(
        request.headers.get("Accept-Language"),
        supported,
        settings.BABEL_DEFAULT_LOCALE,
    )


def get_request_locale(request: Request) -> str:
    """Return the active locale for the current request."""
    babel = getattr(request.state, "babel", None)
    if babel is not None and getattr(babel, "locale", None):
        return babel.locale
    return locale_selector(request)


# Keys used by Vanilla JS in HTML templates (injected via window.I18N).
JS_TRANSLATION_KEYS: tuple[str, ...] = (
    # rooms.html
    "Residence",
    "1 guest",
    "%(count)s guests",
    "night",
    "nights",
    "Up to %(capacity)s guests",
    "Available",
    "Pending",
    "Occupied",
    "Maintenance",
    "/ night",
    "Estimated total %(amount)s",
    "Select",
    "View larger image of %(title)s",
    "Search criteria incomplete.",
    "Request failed (%(status)s). Please try again.",
    "Unable to load rooms.",
    "An unexpected error occurred.",
    # index.html — booking form & calendar
    "Select date",
    "Please select a check-in date.",
    "Please select a check-out date.",
    "Check-in cannot be in the past.",
    "Check-out must be after check-in.",
    "Stays longer than 30 nights require a direct inquiry.",
    "Select your check-in date.",
    "Select your check-out date.",
    "Please select the number of guests.",
    # index.html — destinations
    "Culture & History",
    "Gastronomy",
    "%(distance)s km away",
)


def _extract_js_catalog() -> None:
    """Babel extract markers for client-side strings (not called at runtime)."""
    _("Residence")
    _("1 guest")
    _("%(count)s guests")
    _("night")
    _("nights")
    _("Up to %(capacity)s guests")
    _("Available")
    _("Pending")
    _("Occupied")
    _("Maintenance")
    _("/ night")
    _("Estimated total %(amount)s")
    _("Select")
    _("View larger image of %(title)s")
    _("Search criteria incomplete.")
    _("Request failed (%(status)s). Please try again.")
    _("Unable to load rooms.")
    _("An unexpected error occurred.")
    _("Select date")
    _("Please select a check-in date.")
    _("Please select a check-out date.")
    _("Check-in cannot be in the past.")
    _("Check-out must be after check-in.")
    _("Stays longer than 30 nights require a direct inquiry.")
    _("Select your check-in date.")
    _("Select your check-out date.")
    _("Please select the number of guests.")
    _("Culture & History")
    _("Gastronomy")
    _("%(distance)s km away")


def get_js_translations() -> dict[str, str]:
    """Build a gettext-backed dictionary for client-side strings."""
    return {key: _(key) for key in JS_TRANSLATION_KEYS}


def page_context(request: Request, **extra: object) -> dict[str, object]:
    """Common template context for server-rendered pages."""
    locale = get_request_locale(request)
    return {
        "current_locale": locale,
        "supported_locales": get_settings().SUPPORTED_LOCALES,
        "js_translations": get_js_translations(),
        **extra,
    }
