
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
import os
import secrets

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Organization, User, PasswordResetToken
from schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

from password_reset import (
    create_password_reset_token,
    send_password_reset_email,
    validate_password_reset_token,
)
from jwt.exceptions import InvalidTokenError

router = APIRouter(prefix="/auth", tags=["Authentication"])

password_hasher = PasswordHash.recommended()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


def create_access_token(user_id: int) -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = str(request.email).strip().lower()

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    organization = Organization(
        name=request.company_name.strip(),
        organization_type=request.organization_type,
    )

    try:
        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            name=request.name.strip(),
            email=email,
            password_hash=password_hasher.hash(request.password),
            role="admin",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "message": "Company registered successfully.",
            "organization_id": organization.id,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    except Exception:
        db.rollback()
        raise


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    email = str(request.email).strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user or not password_hasher.verify(
        request.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/token", response_model=TokenResponse)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user or not password_hasher.verify(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    response = {
        "message": (
            "If an account exists for that email, "
            "a password reset link will be sent."
        )
    }

    email = str(request.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        return response

    reset_token, token_hash, expires_at = (
        create_password_reset_token(user.id)
    )

    try:
        # Store the token identifier hash, never the raw token.
        reset_record = PasswordResetToken(
            user_id=user.id,
            token_jti_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_record)
        db.commit()

        send_password_reset_email(user.email, reset_token)

    except Exception:
        db.rollback()
        # Do not expose account existence or SMTP/database details.
        import logging
        logging.getLogger(__name__).exception(
            "Password reset request could not be completed."
        )

    return response


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        token_data = validate_password_reset_token(request.token)
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The reset link is invalid or expired.",
        ) from None

    try:
        # Lock the token row so concurrent requests cannot both use it.
        reset_record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == token_data["user_id"],
                PasswordResetToken.token_jti_hash
                == token_data["token_jti_hash"],
            )
            .with_for_update()
            .first()
        )

        now = datetime.now(timezone.utc)

        if (
            not reset_record
            or reset_record.used_at is not None
            or reset_record.expires_at <= now
            or token_data["expires_at"] <= now
        ):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The reset link is invalid or expired.",
            )

        user = (
            db.query(User)
            .filter(User.id == token_data["user_id"])
            .with_for_update()
            .first()
        )

        if not user or not user.is_active:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The reset link is invalid or expired.",
            )

        user.password_hash = password_hasher.hash(
            request.new_password
        )
        reset_record.used_at = now

        db.commit()

        return {
            "message": (
                "Password reset successfully. "
                "You can now log in with your new password."
            )
        }

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset the password right now.",
        ) from None
