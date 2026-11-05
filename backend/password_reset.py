
import hashlib
import os
import secrets
import smtplib

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode

import jwt
from jwt.exceptions import InvalidTokenError


JWT_ALGORITHM = "HS256"
RESET_TOKEN_MINUTES = 15


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    return secret


def hash_token_identifier(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_password_reset_token(
    user_id: int,
) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=RESET_TOKEN_MINUTES)
    jti = secrets.token_urlsafe(32)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "jti": jti,
        "purpose": "password_reset",
    }

    token = jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )

    return token, hash_token_identifier(jti), expires_at


def validate_password_reset_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": ["sub", "iat", "exp", "jti", "purpose"],
        },
    )

    if payload.get("purpose") != "password_reset":
        raise InvalidTokenError("Invalid token purpose.")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise InvalidTokenError("Invalid token subject.") from None

    jti = payload.get("jti")

    if not isinstance(jti, str) or not jti:
        raise InvalidTokenError("Invalid token identifier.")

    return {
        "user_id": user_id,
        "token_jti_hash": hash_token_identifier(jti),
        "expires_at": datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        ),
    }


def send_password_reset_email(
    recipient_email: str,
    reset_token: str,
) -> None:
    host = os.getenv("BREVO_SMTP_HOST")
    port = int(os.getenv("BREVO_SMTP_PORT", "587"))
    login = os.getenv("BREVO_SMTP_LOGIN")
    smtp_key = os.getenv("BREVO_SMTP_KEY")
    sender = os.getenv("EMAIL_FROM")

    if not all([host, login, smtp_key, sender]):
        raise RuntimeError("Email settings are incomplete.")

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173",
    ).rstrip("/")

    reset_url = (
        f"{frontend_url}/?"
        f"{urlencode({'reset_token': reset_token})}"
    )

    message = EmailMessage()
    message["Subject"] = "Reset your Nexa Recruit password"
    message["From"] = sender
    message["To"] = recipient_email

    message.set_content(
        "We received a request to reset your Nexa Recruit password.\n\n"
        f"Use this link within {RESET_TOKEN_MINUTES} minutes:\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(login, smtp_key)
        server.send_message(message)
