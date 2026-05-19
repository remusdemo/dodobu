import os


def _read_version():
    path = os.path.join(os.path.dirname(__file__), "VERSION")
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


class Config:
    VERSION = _read_version()
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_HOST = os.getenv("DB_HOST", "db")
    DB_NAME = os.getenv("DB_NAME", "dodobu")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    PORT = int(os.getenv("PORT", 5000))
    TESTING_ENABLED = os.getenv("TESTING_ENABLED", "0") == "1"
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
