
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from dependencies import get_db
from main import app
from models import User
from security import get_current_user


def make_user(role: str, organization_id: int = 101, user_id: int = 1):
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.organization_id = organization_id
    user.is_active = True
    user.name = "Test User"
    user.email = "test@example.com"
    user.created_at = "2026-11-01T00:00:00"
    return user


def test_admin_can_create_team_member():
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None
    admin = make_user("admin")

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.post(
                "/organization/team-members",
                json={
                    "name": "Test Recruiter",
                    "email": "recruiter@example.com",
                    "password": "TestPassword123!",
                    "role": "recruiter",
                },
            )

        assert response.status_code == 201

        created_user = fake_db.add.call_args.args[0]
        assert created_user.organization_id == 101
        assert created_user.role == "recruiter"
        assert created_user.password_hash != "TestPassword123!"
        fake_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_recruiter_cannot_create_team_member():
    fake_db = MagicMock()
    recruiter = make_user("recruiter")

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: recruiter

    try:
        with TestClient(app) as client:
            response = client.post(
                "/organization/team-members",
                json={
                    "name": "Another Recruiter",
                    "email": "another@example.com",
                    "password": "TestPassword123!",
                    "role": "recruiter",
                },
            )

        assert response.status_code == 403
        fake_db.add.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_create_team_member_in_another_organization():
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None
    admin = make_user("admin", organization_id=101)

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.post(
                "/organization/team-members",
                json={
                    "name": "Test Recruiter",
                    "email": "recruiter2@example.com",
                    "password": "TestPassword123!",
                    "role": "recruiter",
                    "organization_id": 202,
                },
            )

        assert response.status_code == 201

        created_user = fake_db.add.call_args.args[0]

        # The authenticated admin's organization must be used.
        assert created_user.organization_id == 101
        assert created_user.organization_id != 202

    finally:
        app.dependency_overrides.clear()


# --- Team Member Listing Tests ---

def test_admin_can_list_team_members():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    member2 = make_user("recruiter", organization_id=101, user_id=2)
    fake_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        admin, member2
    ]

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.get("/organization/team-members")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2
        assert data[0]["role"] == "admin"
        assert data[1]["role"] == "recruiter"
    finally:
        app.dependency_overrides.clear()


def test_recruiter_cannot_list_team_members():
    recruiter = make_user("recruiter", organization_id=101, user_id=2)
    app.dependency_overrides[get_current_user] = lambda: recruiter

    try:
        with TestClient(app) as client:
            response = client.get("/organization/team-members")

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You do not have permission to perform this action."
        )
    finally:
        app.dependency_overrides.clear()


# --- Role Management Tests (Task 4) ---

def test_admin_can_promote_recruiter_to_team_lead():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    target_member = make_user("recruiter", organization_id=101, user_id=4)
    fake_db.query.return_value.filter.return_value.first.return_value = target_member

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/role",
                json={"role": "team_lead"},
            )

        assert response.status_code == 200
        assert target_member.role == "team_lead"
        fake_db.commit.assert_called_once()
        assert response.json()["role"] == "team_lead"
    finally:
        app.dependency_overrides.clear()


def test_admin_can_downgrade_team_lead_to_recruiter():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    target_member = make_user("team_lead", organization_id=101, user_id=4)
    fake_db.query.return_value.filter.return_value.first.return_value = target_member

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/role",
                json={"role": "recruiter"},
            )

        assert response.status_code == 200
        assert target_member.role == "recruiter"
        fake_db.commit.assert_called_once()
        assert response.json()["role"] == "recruiter"
    finally:
        app.dependency_overrides.clear()


def test_recruiter_cannot_update_roles():
    recruiter = make_user("recruiter", organization_id=101, user_id=2)
    app.dependency_overrides[get_current_user] = lambda: recruiter

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/role",
                json={"role": "team_lead"},
            )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You do not have permission to perform this action."
        )
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_change_own_role():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    fake_db.query.return_value.filter.return_value.first.return_value = admin

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/1/role",
                json={"role": "team_lead"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "You cannot change your own role."
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_modify_another_organization_member_role():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/999/role",
                json={"role": "team_lead"},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Team member not found."
    finally:
        app.dependency_overrides.clear()


def test_unknown_member_role_update_returns_404():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/888/role",
                json={"role": "recruiter"},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Team member not found."
    finally:
        app.dependency_overrides.clear()


def test_invalid_role_update_returns_422():
    admin = make_user("admin", organization_id=101, user_id=1)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/role",
                json={"role": "superadmin"},
            )
        assert response.status_code == 422

        with TestClient(app) as client:
            response_admin = client.patch(
                "/organization/team-members/4/role",
                json={"role": "admin"},
            )
        assert response_admin.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_administrator_role_cannot_be_modified():
    fake_db = MagicMock()
    admin_caller = make_user("admin", organization_id=101, user_id=1)
    admin_target = make_user("admin", organization_id=101, user_id=2)
    fake_db.query.return_value.filter.return_value.first.return_value = admin_target

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_caller

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/2/role",
                json={"role": "team_lead"},
            )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Administrator roles cannot be changed here."
        )
    finally:
        app.dependency_overrides.clear()


# --- Status Management Tests (Task 5) ---

def test_admin_can_deactivate_member():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    target_member = make_user("recruiter", organization_id=101, user_id=4)
    target_member.is_active = True
    fake_db.query.return_value.filter.return_value.first.return_value = target_member

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/status",
                params={"is_active": False},
            )

        assert response.status_code == 200
        assert target_member.is_active is False
        fake_db.commit.assert_called_once()
        assert response.json()["is_active"] is False
    finally:
        app.dependency_overrides.clear()


def test_admin_can_reactivate_member():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    target_member = make_user("recruiter", organization_id=101, user_id=4)
    target_member.is_active = False
    fake_db.query.return_value.filter.return_value.first.return_value = target_member

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/4/status",
                params={"is_active": True},
            )

        assert response.status_code == 200
        assert target_member.is_active is True
        fake_db.commit.assert_called_once()
        assert response.json()["is_active"] is True
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_deactivate_own_account():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    fake_db.query.return_value.filter.return_value.first.return_value = admin

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/1/status",
                params={"is_active": False},
            )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "You cannot change your own account status."
        )
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_deactivate_another_admin():
    fake_db = MagicMock()
    admin_caller = make_user("admin", organization_id=101, user_id=1)
    admin_target = make_user("admin", organization_id=101, user_id=2)
    fake_db.query.return_value.filter.return_value.first.return_value = admin_target

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_caller

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/2/status",
                params={"is_active": False},
            )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Administrator accounts cannot be changed here."
        )
    finally:
        app.dependency_overrides.clear()


def test_cross_organization_status_update_is_rejected():
    fake_db = MagicMock()
    admin = make_user("admin", organization_id=101, user_id=1)
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/organization/team-members/999/status",
                params={"is_active": False},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Team member not found."
    finally:
        app.dependency_overrides.clear()

