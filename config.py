import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _stable_secret():
    """Generate a key once and persist it to a file so sessions survive restarts."""
    key_path = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            return f.read().strip()
    key = os.urandom(32).hex()
    with open(key_path, "w") as f:
        f.write(key)
    return key


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or _stable_secret()
    DATABASE = os.path.join(BASE_DIR, "site.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "uploads")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB max upload

    # Cloudflare Turnstile
    TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "0x4AAAAAACcmRED-ctEXXMpk")
    TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "0x4AAAAAACcmRBOWo71-slF2mJbq6BtLBLQ")

    # Session / cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

