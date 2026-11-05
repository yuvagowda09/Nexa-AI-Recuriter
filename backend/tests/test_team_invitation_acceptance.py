
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from jwt.exceptions import InvalidTokenError

from fastapi.testclient import TestClient

from dependencies import get_db
from main import app


def test_invitation_acceptance_rejects_invalid_token():
    fake_db = MagicMock()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "routes.organization.validate_team_invitation_token",
            side_effect=InvalidTokenError("Invalid token"),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/organization/team-invitations/accept",
                    json={
                        "token": "not-a-valid-token",
                        "new_password": "StrongTestPassword123!",
                    },
                )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "The invitation link is invalid or expired."
        )
        fake_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_invitation_acceptance_rejects_expired_invitation():
    fake_db = MagicMock()

    invitation = MagicMock()
    invitation.id = 7
    invitation.token_jti_hash = "expected-hash"
    invitation.accepted_at = None
    invitation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    fake_db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = invitation

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "routes.organization.validate_team_invitation_token",
            return_value={
                "invitation_id": 7,
                "token_jti_hash": "expected-hash",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            },
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/organization/team-invitations/accept",
                    json={
                        "token": "test-token",
                        "new_password": "StrongTestPassword123!",
                    },
                )

        assert response.status_code == 400
        fake_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()



def test_invitation_acceptance_creates_user_successfully():
    fake_db = MagicMock()

    now = datetime.now(timezone.utc)

    invitation = MagicMock()
    invitation.id = 7
    invitation.organization_id = 3
    invitation.name = "Test Recruiter"
    invitation.email = "recruiter@example.com"
    invitation.role = "recruiter"
    invitation.token_jti_hash = "expected-hash"
    invitation.accepted_at = None
    invitation.expires_at = now + timedelta(hours=24)

    # Mock the database lookup for the invitation.
    invitation_query = MagicMock()
    invitation_query.filter.return_value.with_for_update.return_value.first.return_value = invitation

    # Mock the database lookup for an existing user.
    user_query = MagicMock()
    user_query.filter.return_value.first.return_value = None

    fake_db.query.side_effect = [invitation_query, user_query]

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch(
                "routes.organization.validate_team_invitation_token",
                return_value={
                    "invitation_id": 7,
                    "token_jti_hash": "expected-hash",
                    "expires_at": now + timedelta(hours=24),
                },
            ),
            patch(
                "routes.organization.password_hasher.hash",
                return_value="test-password-hash",
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/organization/team-invitations/accept",
                    json={
                        "token": "valid-test-token",
                        "new_password": "StrongTestPassword123!",
                    },
                )

        assert response.status_code == 200
        assert response.json()["message"] == (
            "Invitation accepted. You can now log in."
        )
        assert response.json()["organization_id"] == 3
        assert response.json()["email"] == "recruiter@example.com"
        assert response.json()["role"] == "recruiter"

        # Confirm the password is hashed before storing the user.
        created_user = next(
            item for item in fake_db.add.call_args_list[0].args
            if isinstance(item, object)
        )
        assert created_user.password_hash == "test-password-hash"

        # Confirm the invitation is marked accepted and committed.
        assert invitation.accepted_at is not None
        fake_db.commit.assert_called_once()
        fake_db.refresh.assert_called_once()

    finally:
        app.dependency_overrides.clear()




def test_accepted_invitation_cannot_be_reused():
    fake_db = MagicMock()

    now = datetime.now(timezone.utc)

    # Simulate an invitation that was already accepted.
    invitation = MagicMock()
    invitation.id = 7
    invitation.organization_id = 3
    invitation.name = "Test Recruiter"
    invitation.email = "recruiter@example.com"
    invitation.role = "recruiter"
    invitation.token_jti_hash = "expected-hash"
    invitation.accepted_at = now - timedelta(minutes=5)
    invitation.expires_at = now + timedelta(hours=24)

    fake_db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = invitation

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "routes.organization.validate_team_invitation_token",
            return_value={
                "invitation_id": 7,
                "token_jti_hash": "expected-hash",
                "expires_at": now + timedelta(hours=24),
            },
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/organization/team-invitations/accept",
                    json={
                        "token": "already-used-test-token",
                        "new_password": "StrongTestPassword123!",
                    },
                )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "The invitation link is invalid or expired."
        )

        # Reusing an accepted invitation must not create or commit a user.
        fake_db.add.assert_not_called()
        fake_db.commit.assert_not_called()

    finally:
        app.dependency_overrides.clear()



def test_invitation_acceptance_rejects_existing_user_email():
    fake_db = MagicMock()

    now = datetime.now(timezone.utc)

    # Simulate a valid, unused invitation.
    invitation = MagicMock()
    invitation.id = 7
    invitation.organization_id = 3
    invitation.name = "Test Recruiter"
    invitation.email = "recruiter@example.com"
    invitation.role = "recruiter"
    invitation.token_jti_hash = "expected-hash"
    invitation.accepted_at = None
    invitation.expires_at = now + timedelta(hours=24)

    # Simulate an account that already uses this email.
    existing_user = MagicMock()
    existing_user.email = "recruiter@example.com"

    invitation_query = MagicMock()
    invitation_query.filter.return_value.with_for_update.return_value.first.return_value = invitation

    existing_user_query = MagicMock()
    existing_user_query.filter.return_value.first.return_value = existing_user

    # First query finds the invitation; second finds the existing user.
    fake_db.query.side_effect = [
        invitation_query,
        existing_user_query,
    ]

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "routes.organization.validate_team_invitation_token",
            return_value={
                "invitation_id": 7,
                "token_jti_hash": "expected-hash",
                "expires_at": now + timedelta(hours=24),
            },
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/organization/team-invitations/accept",
                    json={
                        "token": "valid-test-token",
                        "new_password": "StrongTestPassword123!",
                    },
                )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "An account with this email already exists. "
            "Please contact your organization administrator."
        )

        # No duplicate account should be created or committed.
        fake_db.add.assert_not_called()
        fake_db.commit.assert_not_called()

    finally:
        app.dependency_overrides.clear()


# --- Invitation Management Tests (List, Cancel, Resend) ---

def make_admin(organization_id=3, user_id=1):
    user = MagicMock()
    user.id = user_id
    user.role = "admin"
    user.organization_id = organization_id
    user.is_active = True
    return user


def test_admin_can_list_team_invitations():
    from security import get_current_user

    fake_db = MagicMock()
    admin = make_admin(organization_id=3)

    now = datetime.now(timezone.utc)
    inv1 = MagicMock()
    inv1.id = 10
    inv1.name = "Pending Inv"
    inv1.email = "pending@example.com"
    inv1.role = "recruiter"
    inv1.token_jti_hash = "secret-hash-1"
    inv1.expires_at = now + timedelta(hours=24)
    inv1.accepted_at = None
    inv1.created_at = now

    inv2 = MagicMock()
    inv2.id = 11
    inv2.name = "Accepted Inv"
    inv2.email = "accepted@example.com"
    inv2.role = "team_lead"
    inv2.token_jti_hash = "secret-hash-2"
    inv2.expires_at = now + timedelta(hours=24)
    inv2.accepted_at = now
    inv2.created_at = now

    fake_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        inv1, inv2
    ]

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.get("/organization/team-invitations")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["status"] == "pending"
        assert data[1]["status"] == "accepted"

        # Security check: tokens and token hashes must NEVER be exposed
        for item in data:
            assert "token" not in item
            assert "token_jti_hash" not in item
    finally:
        app.dependency_overrides.clear()


def test_recruiter_cannot_list_team_invitations():
    from security import get_current_user

    recruiter = MagicMock()
    recruiter.role = "recruiter"
    recruiter.organization_id = 3
    recruiter.is_active = True

    app.dependency_overrides[get_current_user] = lambda: recruiter

    try:
        with TestClient(app) as client:
            response = client.get("/organization/team-invitations")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_can_cancel_pending_invitation():
    from security import get_current_user

    fake_db = MagicMock()
    admin = make_admin(organization_id=3)

    inv = MagicMock()
    inv.id = 10
    inv.organization_id = 3
    inv.accepted_at = None

    fake_db.query.return_value.filter.return_value.first.return_value = inv

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.delete("/organization/team-invitations/10")

        assert response.status_code == 200
        assert response.json()["message"] == "Invitation cancelled successfully."
        fake_db.delete.assert_called_once_with(inv)
        fake_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_cannot_cancel_already_accepted_invitation():
    from security import get_current_user

    fake_db = MagicMock()
    admin = make_admin(organization_id=3)

    inv = MagicMock()
    inv.id = 10
    inv.organization_id = 3
    inv.accepted_at = datetime.now(timezone.utc)

    fake_db.query.return_value.filter.return_value.first.return_value = inv

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.delete("/organization/team-invitations/10")

        assert response.status_code == 400
        assert response.json()["detail"] == "Accepted invitations cannot be cancelled."
        fake_db.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_cannot_cancel_invitation_from_another_org():
    from security import get_current_user

    fake_db = MagicMock()
    admin = make_admin(organization_id=3)
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.delete("/organization/team-invitations/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Invitation not found."
    finally:
        app.dependency_overrides.clear()


def test_admin_can_resend_team_invitation():
    from security import get_current_user

    fake_db = MagicMock()
    admin = make_admin(organization_id=3)

    inv = MagicMock()
    inv.id = 10
    inv.organization_id = 3
    inv.name = "Candidate Name"
    inv.email = "cand@example.com"
    inv.accepted_at = None

    org = MagicMock()
    org.name = "Test Org"

    # 1. query for invitation, 2. query for existing user, 3. query for org
    query_mock = MagicMock()
    query_mock.filter.return_value.first.side_effect = [inv, None, org]
    fake_db.query.return_value = query_mock

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    now = datetime.now(timezone.utc)
    new_exp = now + timedelta(hours=48)

    try:
        with patch(
            "routes.organization.create_team_invitation_token",
            return_value=("new-raw-token", "new-hash", new_exp),
        ), patch("routes.organization.send_team_invitation_email") as mock_send:
            with TestClient(app) as client:
                response = client.post("/organization/team-invitations/10/resend")

        assert response.status_code == 200
        assert response.json()["message"] == "Invitation resent successfully."
        mock_send.assert_called_once_with(
            recipient_email="cand@example.com",
            recipient_name="Candidate Name",
            company_name="Test Org",
            invitation_token="new-raw-token",
        )
        fake_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()

