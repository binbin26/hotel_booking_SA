"""
Babel CLI entry point (keep separate from main.py so uvicorn still works).

Usage:
    python babel.py extract --dir .
    python babel.py init -l vi
    python babel.py update -l vi
    python babel.py compile
"""

from fastapi_babel import Babel

from app.core.i18n import babel_configs

if __name__ == "__main__":
    Babel(configs=babel_configs).run_cli()
