"""Application configuration, read from environment variables (and an optional .env file)."""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development").lower()
    DEBUG = _bool("FLASK_DEBUG", APP_ENV == "development")
    TESTING = False

    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Database
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "student_portal")
    DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "8"))
    AUTO_MIGRATE = _bool("AUTO_MIGRATE", True)
    DB_SSL = _bool("DB_SSL", False)

    # Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_HOURS", "8")))

    CSRF_ENABLED = True

    # Uploads
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    IS_VERCEL = bool(os.environ.get("VERCEL"))
    UPLOAD_ROOT = "/tmp" if IS_VERCEL else BASE_DIR

    # Application documents (COG/COE) are private and served only through an access-checked route.
    PRIVATE_UPLOAD_FOLDER = os.environ.get(
        "PRIVATE_UPLOAD_FOLDER", os.path.join(UPLOAD_ROOT, "instance", "uploads", "applications")
    )
    # Files uploaded before the reengineering live here; still readable for existing records.
    LEGACY_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ANNOUNCEMENT_UPLOAD_FOLDER = os.environ.get(
        "ANNOUNCEMENT_UPLOAD_FOLDER", os.path.join(UPLOAD_ROOT, "static", "uploads", "announcements")
    )

    # Ranking export: "auto" tries the DL.docx template through MS Word first, then falls back to ReportLab.
    PDF_EXPORT_ENGINE = os.environ.get("PDF_EXPORT_ENGINE", "auto")
    DL_TEMPLATE_PATH = os.path.join(BASE_DIR, "DL.docx")

    FIRST_ACADEMIC_YEAR = int(os.environ.get("FIRST_ACADEMIC_YEAR", "2024"))

    # Login throttling
    LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300"))


def resolve_secret_key(config):
    """Return a usable secret key, refusing to run production without one."""
    if config.get("SECRET_KEY"):
        return config["SECRET_KEY"]
    if config.get("APP_ENV") == "production":
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production.")
    # Development fallback: sessions reset whenever the server restarts.
    return secrets.token_hex(32)
