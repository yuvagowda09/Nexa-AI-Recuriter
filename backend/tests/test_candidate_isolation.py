
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from dependencies import get_db
from main import app
from security import get_current_user


client = TestClient(app)


def test_candidates_list_only_returns_current_organizations_candidates():
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
        response = client.get("/candidates/")

        assert response.status_code == 200

        query_filter = fake_db.query.return_value.filter
        query_filter.assert_called_once()

        filter_condition = query_filter.call_args.args[0]
        assert "organization_id" in str(filter_condition)

        parameters = filter_condition.compile().params
        assert 101 in parameters.values()

    finally:
        app.dependency_overrides.clear()


def test_candidate_creation_uses_authenticated_organizations_id():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()
    fake_db.refresh.side_effect = lambda candidate: setattr(candidate, "id", 1)

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.post(
            "/candidates/",
            json={
                "name": "Test Candidate",
                "email": "candidate@example.com",
                "phone": "9999999999",
                "location": "Bengaluru",
                "organization_id": 202,
            },
        )

        assert response.status_code == 200

        created_candidate = fake_db.add.call_args.args[0]

        assert created_candidate.organization_id == 101
        assert created_candidate.organization_id != 202

        fake_db.commit.assert_called_once()
        fake_db.refresh.assert_called_once_with(created_candidate)

    finally:
        app.dependency_overrides.clear()



def test_candidate_by_id_requires_matching_organization():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.get("/candidates/55")

        assert response.status_code == 404
        assert response.json()["detail"] == "Candidate not found."

        query_filter = fake_db.query.return_value.filter
        query_filter.assert_called_once()

        filter_condition = query_filter.call_args.args
        assert len(filter_condition) == 2
        assert "organization_id" in str(filter_condition[1])

        parameters = filter_condition[1].compile().params
        assert 101 in parameters.values()

    finally:
        app.dependency_overrides.clear()


def test_candidate_by_id_returns_candidate_in_same_organization():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    candidate = SimpleNamespace(
        id=55,
        organization_id=101,
        name="Test Candidate",
        email="candidate@example.com",
        phone="9999999999",
        location="Bengaluru",
    )

    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = candidate

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = client.get("/candidates/55")

        assert response.status_code == 200
        assert response.json()["id"] == 55
        assert response.json()["organization_id"] == 101
        assert response.json()["name"] == "Test Candidate"

    finally:
        app.dependency_overrides.clear()
