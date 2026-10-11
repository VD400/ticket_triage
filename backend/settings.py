"""Settings shared by local development and hosted deployments."""

import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


def is_production():
    return os.getenv("APP_ENV", "development").lower() == "production"


def frontend_url():
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def cors_origins():
    return [
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ORIGINS", frontend_url()).split(",")
        if origin.strip()
    ]


def validate_hosted_settings():
    if not is_production():
        return
    for origin in [frontend_url(), *cors_origins()]:
        url = urlsplit(origin)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.hostname in ("localhost", "127.0.0.1", "::1")
            or url.path
            or url.query
            or url.fragment
            or url.username
        ):
            raise RuntimeError("Production FRONTEND_URL/CORS_ORIGINS must be HTTPS website origins")
    if not cors_origins() or frontend_url() not in cors_origins():
        raise RuntimeError("CORS_ORIGINS must include FRONTEND_URL")
    if os.getenv("EMAIL_BACKEND", "console") not in ("resend", "smtp"):
        raise RuntimeError("Set EMAIL_BACKEND=resend or smtp for production email verification")
    required = ["EMAIL_FROM"]
    if os.getenv("EMAIL_BACKEND") == "resend":
        required.append("RESEND_API_KEY")
    else:
        required.extend(["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD"])
    if any(not os.getenv(name) for name in required):
        raise RuntimeError("Missing production email settings: " + ", ".join(required))
