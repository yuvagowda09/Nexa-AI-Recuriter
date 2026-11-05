
import logging

from datetime import datetime, timezone
import secrets
from jwt.exceptions import InvalidTokenError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from dependencies import get_db
from models import User, Organization, TeamInvitation
from schemas import (
    TeamMemberCreate,
    TeamMemberRoleUpdate,
    TeamInvitationCreate,
    TeamInvitationAccept,
)
from security import require_roles
from team_invitations import (
    create_team_invitation_token,
    send_team_invitation_email,
    validate_team_invitation_token,
)


router = APIRouter(
    prefix="/organization",
    tags=["Organization"],
)

password_hasher = PasswordHash.recommended()


@router.post(
    "/team-members",
    status_code=status.HTTP_201_CREATED,
)
def create_team_member(
    request: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    email = str(request.email).strip().lower()

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        organization_id=current_user.organization_id,
        name=request.name.strip(),
        email=email,
        password_hash=password_hasher.hash(request.password),
        role=request.role,
        is_active=True,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "organization_id": new_user.organization_id,
        "is_active": new_user.is_active,
    }


@router.post(
    "/team-invitations",
    status_code=status.HTTP_201_CREATED,
)
def create_team_invitation(
    request: TeamInvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    email = str(request.email).strip().lower()

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    existing_invitation = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.organization_id == current_user.organization_id,
            TeamInvitation.email == email,
            TeamInvitation.accepted_at.is_(None),
            TeamInvitation.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active invitation already exists for this email.",
        )

    organization = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization could not be found.",
        )

    invitation = None

    try:
        invitation = TeamInvitation(
            organization_id=current_user.organization_id,
            invited_by_user_id=current_user.id,
            name=request.name.strip(),
            email=email,
            role=request.role,
            token_jti_hash="pending-" + secrets.token_hex(24),
            expires_at=datetime.now(timezone.utc),
        )

        db.add(invitation)
        db.flush()

        token, token_hash, expires_at = create_team_invitation_token(
            invitation.id
        )

        invitation.token_jti_hash = token_hash
        invitation.expires_at = expires_at

        db.commit()
        db.refresh(invitation)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An invitation could not be created for this email.",
        ) from None
    except Exception:
        db.rollback()
        raise

    try:
        send_team_invitation_email(
            recipient_email=invitation.email,
            recipient_name=invitation.name,
            company_name=organization.name,
            invitation_token=token,
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "Team invitation email delivery failed."
        )

        try:
            invitation.expires_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
            logging.getLogger(__name__).exception(
                "Failed to invalidate an undelivered invitation."
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The invitation email could not be sent. "
                "Please try again."
            ),
        ) from None

    return {
        "message": "Invitation created and email sent.",
        "invitation_id": invitation.id,
        "email": invitation.email,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
    }


@router.post("/team-invitations/accept")
def accept_team_invitation(
    request: TeamInvitationAccept,
    db: Session = Depends(get_db),
):
    # First validate the signed token and its intended purpose.
    try:
        token_data = validate_team_invitation_token(request.token)
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The invitation link is invalid or expired.",
        ) from None

    try:
        # Lock the invitation row so concurrent requests cannot
        # accept the same invitation simultaneously.
        invitation = (
            db.query(TeamInvitation)
            .filter(
                TeamInvitation.id == token_data["invitation_id"],
                TeamInvitation.token_jti_hash
                == token_data["token_jti_hash"],
            )
            .with_for_update()
            .first()
        )

        now = datetime.now(timezone.utc)

        if (
            not invitation
            or invitation.accepted_at is not None
            or invitation.expires_at <= now
            or token_data["expires_at"] <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The invitation link is invalid or expired.",
            )

        # Prevent creating an account if this email already belongs
        # to an existing user.
        existing_user = (
            db.query(User)
            .filter(User.email == invitation.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An account with this email already exists. "
                    "Please contact your organization administrator."
                ),
            )

        new_user = User(
            organization_id=invitation.organization_id,
            name=invitation.name,
            email=invitation.email,
            password_hash=password_hasher.hash(request.new_password),
            role=invitation.role,
            is_active=True,
        )

        db.add(new_user)

        # Mark accepted in the same transaction as account creation.
        invitation.accepted_at = now

        db.commit()
        db.refresh(new_user)

        return {
            "message": "Invitation accepted. You can now log in.",
            "user_id": new_user.id,
            "organization_id": new_user.organization_id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
        }

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The invitation could not be accepted.",
        ) from None
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to accept the invitation right now.",
        ) from None


@router.get("/team-invitations")
def list_team_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    invitations = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.organization_id == current_user.organization_id
        )
        .order_by(TeamInvitation.created_at.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    results = []
    for inv in invitations:
        if inv.accepted_at is not None:
            inv_status = "accepted"
        elif inv.expires_at <= now:
            inv_status = "expired"
        else:
            inv_status = "pending"

        # Security: Raw tokens and token hashes are strictly omitted.
        results.append({
            "id": inv.id,
            "name": inv.name,
            "email": inv.email,
            "role": inv.role,
            "status": inv_status,
            "expires_at": inv.expires_at,
            "accepted_at": inv.accepted_at,
            "created_at": inv.created_at,
        })

    return results


@router.delete("/team-invitations/{invitation_id}")
def cancel_team_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    invitation = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.id == invitation_id,
            TeamInvitation.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accepted invitations cannot be cancelled.",
        )

    try:
        db.delete(invitation)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to cancel the invitation.",
        ) from None

    return {
        "message": "Invitation cancelled successfully.",
        "id": invitation_id,
    }


@router.post("/team-invitations/{invitation_id}/resend")
def resend_team_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    invitation = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.id == invitation_id,
            TeamInvitation.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been accepted.",
        )

    existing_user = (
        db.query(User).filter(User.email == invitation.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    organization = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization could not be found.",
        )

    token, token_hash, expires_at = create_team_invitation_token(
        invitation.id
    )

    try:
        invitation.token_jti_hash = token_hash
        invitation.expires_at = expires_at
        db.commit()
        db.refresh(invitation)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update invitation token.",
        ) from None

    try:
        send_team_invitation_email(
            recipient_email=invitation.email,
            recipient_name=invitation.name,
            company_name=organization.name,
            invitation_token=token,
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "Team invitation email delivery failed on resend."
        )
        try:
            invitation.expires_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The invitation email could not be resent. Please try again.",
        ) from None

    return {
        "message": "Invitation resent successfully.",
        "invitation_id": invitation.id,
        "email": invitation.email,
        "expires_at": invitation.expires_at,
    }


@router.get("/team-members")
def list_team_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    members = (
        db.query(User)
        .filter(
            User.organization_id == current_user.organization_id
        )
        .order_by(User.id.asc())
        .all()
    )

    return [
        {
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "role": member.role,
            "is_active": member.is_active,
            "created_at": member.created_at,
        }
        for member in members
    ]


@router.patch("/team-members/{member_id}/status")
def update_team_member_status(
    member_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    # Find the member inside the current organization only.
    member = (
        db.query(User)
        .filter(
            User.id == member_id,
            User.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found.",
        )

    # Prevent changing your own account status.
    if member.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own account status.",
        )

    # Protect administrator accounts.
    if member.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot be changed here.",
        )

    try:
        member.is_active = is_active
        db.commit()
        db.refresh(member)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update team member status.",
        ) from None

    return {
        "message": "Team member status updated successfully.",
        "id": member.id,
        "name": member.name,
        "role": member.role,
        "is_active": member.is_active,
    }


@router.patch("/team-members/{member_id}/role")
def update_team_member_role(
    member_id: int,
    role_data: TeamMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    member = (
        db.query(User)
        .filter(
            User.id == member_id,
            User.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found.",
        )

    if member.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )

    if member.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator roles cannot be changed here.",
        )

    try:
        member.role = role_data.role
        db.commit()
        db.refresh(member)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update team member role.",
        ) from None

    return {
        "message": "Team member role updated successfully.",
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "role": member.role,
        "is_active": member.is_active,
    }
