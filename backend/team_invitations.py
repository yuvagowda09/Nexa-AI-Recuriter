
import hashlib
import os
import secrets

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

import smtplib

from email.message import EmailMessage
from urllib.parse import urlencode

JWT_ALGORITHM = "HS256"
INVITATION_TOKEN_HOURS = 48


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    return secret


def hash_token_identifier(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_team_invitation_token(
    invitation_id: int,
) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=INVITATION_TOKEN_HOURS)
    jti = secrets.token_urlsafe(32)

    payload = {
        "sub": str(invitation_id),
        "iat": now,
        "exp": expires_at,
        "jti": jti,
        "purpose": "team_invitation",
    }

    token = jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )

    return token, hash_token_identifier(jti), expires_at


def validate_team_invitation_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": ["sub", "iat", "exp", "jti", "purpose"],
        },
    )

    if payload.get("purpose") != "team_invitation":
        raise InvalidTokenError("Invalid token purpose.")

    try:
        invitation_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise InvalidTokenError("Invalid invitation identifier.") from None

    if invitation_id <= 0:
        raise InvalidTokenError("Invalid invitation identifier.")

    jti = payload.get("jti")

    if not isinstance(jti, str) or not jti:
        raise InvalidTokenError("Invalid token identifier.")

    return {
        "invitation_id": invitation_id,
        "token_jti_hash": hash_token_identifier(jti),
        "expires_at": datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        ),
    }


def send_team_invitation_email(
    recipient_email: str,
    recipient_name: str,
    company_name: str,
    invitation_token: str,
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

    invitation_url = (
        f"{frontend_url}/?"
        f"{urlencode({'invitation_token': invitation_token})}"
    )

    message = EmailMessage()
    message["Subject"] = f"Invitation to join {company_name} on Nexa Recruit"
    message["From"] = sender
    message["To"] = recipient_email

    message.set_content(
        f"Hello {recipient_name},\n\n"
        f"You have been invited to join {company_name} on Nexa Recruit.\n\n"
        "Use the link below within 48 hours to accept your invitation "
        "and set your password:\n\n"
        f"{invitation_url}\n\n"
        "If you were not expecting this invitation, you can ignore "
        "this email."
    )

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(login, smtp_key)
        server.send_message(message)
