
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from dependencies import get_db
from security import get_current_user


client = TestClient(app)


def test_jobs_list_only_returns_current_organizations_jobs():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.all.return_value = []

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.get("/jobs/")

        assert response.status_code == 200

        query_filter = fake_db.query.return_value.filter
        query_filter.assert_called_once()

        filter_condition = query_filter.call_args.args[0]
        assert "organization_id" in str(filter_condition)

        parameters = filter_condition.compile().params
        assert 101 in parameters.values()

    finally:
        app.dependency_overrides.clear()


def test_job_creation_uses_authenticated_users_organization():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()
    fake_db.refresh.side_effect = lambda job: setattr(job, "id", 1)

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.post(
            "/jobs/",
            json={
                "title": "Python Developer",
                "description": "Test job description",
                "location": "Bengaluru",
                "status": "active",
            },
        )

        assert response.status_code == 200

        created_job = fake_db.add.call_args.args[0]
        assert created_job.organization_id == 101

        fake_db.commit.assert_called_once()
        fake_db.refresh.assert_called_once_with(created_job)

    finally:
        app.dependency_overrides.clear()



def test_job_creation_ignores_spoofed_organization_id():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()
    fake_db.refresh.side_effect = lambda job: setattr(job, "id", 1)

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.post(
            "/jobs/",
            json={
                "title": "Python Developer",
                "description": "Test job description",
                "location": "Bengaluru",
                "status": "active",
                "organization_id": 202,
            },
        )

        assert response.status_code == 200

        created_job = fake_db.add.call_args.args[0]

        # The authenticated user's company must take precedence.
        assert created_job.organization_id == 101
        assert created_job.organization_id != 202

    finally:
        app.dependency_overrides.clear()

