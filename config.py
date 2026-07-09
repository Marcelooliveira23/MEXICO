"""Centralized application configuration.

Loads environment variables from a .env file if present. Provides
defaults that can be overridden in production. Keeps security related
and tuning parameters in one place for easier hardening.
"""
from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):
        return False

_ENV_PATH = Path(os.getcwd()) / '.env'
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    # attempt load from current working directory silently
    load_dotenv()


class Config:
    # Core / security
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY') or os.getenv(
        'SECRET_KEY', 'change-this-secret')

    # Database (primary troubleshooting DB)
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'mrceduardo')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Costera23')
    MYSQL_DB = os.getenv('MYSQL_DB', 'troubleshooting_db')
    MYSQL_CURSORCLASS = 'DictCursor'

    # MySQL Connection Pool & Timeout Settings (prevent Error 2006)
    MYSQL_CONNECT_TIMEOUT = int(os.getenv('MYSQL_CONNECT_TIMEOUT', '10'))
    MYSQL_POOL_RECYCLE = int(os.getenv('MYSQL_POOL_RECYCLE', '3600'))  # 1 hour
    MYSQL_POOL_PRE_PING = True  # Verify connection before using

    # Optional schema names (keeps compatibility across environments)
    FLEET_DB_NAME = os.getenv('FLEET_DB_NAME', 'fleet_db')
    MEL_DB_NAME = os.getenv('MEL_DB_NAME', 'mel_db')
    ETD_DB_NAME = os.getenv('ETD_DB_NAME', 'etds_db')

    # Upload handling
    UPLOAD_FOLDER = os.getenv(
        'UPLOAD_FOLDER', str(Path(os.getcwd()) / 'uploads'))
    # Max size in MB. Keep this above the exceedance endpoint guardrail
    # so API routes can return structured JSON instead of Flask HTML 413.
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_MB', '24')) * 1024 * 1024
    # Allowed attachment extensions (comma separated list). Keep lowercase.
    ALLOWED_ATTACH_EXTENSIONS = set(
        (os.getenv('ALLOWED_ATTACH_EXTENSIONS', 'pdf,txt,doc,docx,xlsx,png,jpg,jpeg'))
        .replace(' ', '').lower().split(',')
    )

    # Logging level (string name)
    APP_LOG_LEVEL = os.getenv('APP_LOG_LEVEL', 'INFO').upper()

    # Feature toggles
    ENABLE_XHTML2PDF = os.getenv('ENABLE_XHTML2PDF', '0') == '1'

    # PDF generation
    WKHTMLTOPDF_PATH = os.getenv(
        'WKHTMLTOPDF_PATH',
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )


__all__ = ["Config"]
