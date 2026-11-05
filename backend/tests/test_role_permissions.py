
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from dependencies import get_db
from main import app
from models import User
from security import require_roles, get_current_user


def make_user(role: str) -> User:
    user = MagicMock(spec=User)
    user.role = role
    return user


def test_admin_is_allowed():
    checker = require_roles("admin")
    user = make_user("admin")

    assert checker(current_user=user) is user


def test_recruiter_is_denied_admin_permission():
    checker = require_roles("admin")
    user = make_user("recruiter")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == (
        "You do not have permission to perform this action."
    )


def test_recruiter_can_create_job():
    fake_db = MagicMock()

    def set_job_id(job):
        job.id = 1

    fake_db.refresh.side_effect = set_job_id

    fake_user = make_user("recruiter")
    fake_user.organization_id = 101

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        with TestClient(app) as client:
            response = client.post(
                "/jobs/",
                json={
                    "title": "Python Developer",
                    "description": "Build backend services",
                    "location": "Bengaluru",
                    "status": "active",
                },
            )

        assert response.status_code == 200
        assert fake_db.add.called

        created_job = fake_db.add.call_args.args[0]
        assert created_job.organization_id == 101
        assert created_job.id == 1
    finally:
        app.dependency_overrides.clear()


def test_unsupported_role_cannot_create_job():
    fake_db = MagicMock()
    fake_user = make_user("candidate")
    fake_user.organization_id = 101

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        with TestClient(app) as client:
            response = client.post(
                "/jobs/",
                json={
                    "title": "Python Developer",
                    "description": "Build backend services",
                    "location": "Bengaluru",
                    "status": "active",
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "You do not have permission to perform this action."
        )
        fake_db.add.assert_not_called()
    finally:
        app.dependency_overrides.clear()
