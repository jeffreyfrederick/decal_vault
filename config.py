import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Off by default. The Werkzeug debugger this turns on lets anyone who
    # can reach the app run arbitrary code from the browser.
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'decal_vault.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Env override so a Railway volume can mount somewhere other than the
    # source tree.
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "app", "static", "uploads"))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB, generous for a decal photo/scan

    # SESSION_COOKIE_SECURE stays off for local http:// dev - browsers drop
    # secure cookies there.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # Single shared password gates upload/delete - fine for a small trusted
    # staff, not real multi-user auth. Set a real value before deploying.
    STAFF_PASSWORD = os.environ.get("DECAL_VAULT_STAFF_PASSWORD", "hunter-decals")
