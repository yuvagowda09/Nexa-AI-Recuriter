
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from dependencies import get_db


client = TestClient(app)


def test_login_with_unknown_email_returns_generic_401():
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("routes.auth.password_hasher.verify") as verify:
            response = client.post(
                "/auth/login",
                json={
                    "email": "unknown@example.com",
                    "password": "ExamplePassword123!",
                },
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."
        verify.assert_not_called()

    finally:
        app.dependency_overrides.clear()


def test_login_with_wrong_password_returns_generic_401():
    from unittest.mock import MagicMock, patch
    from dependencies import get_db
    from models import User

    fake_db = MagicMock()
    fake_user = MagicMock(spec=User)
    fake_user.email = "existing@example.com"
    fake_user.password_hash = "a-test-password-hash"
    fake_user.is_active = True

    fake_db.query.return_value.filter.return_value.first.return_value = fake_user

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("routes.auth.password_hasher.verify", return_value=False):
            response = client.post(
                "/auth/login",
                json={
                    "email": "existing@example.com",
                    "password": "WrongPassword123!",
                },
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."
    finally:
        app.dependency_overrides.clear()


def test_login_with_inactive_user_returns_403():
    from unittest.mock import MagicMock, patch
    from dependencies import get_db
    from models import User

    fake_db = MagicMock()
    fake_user = MagicMock(spec=User)
    fake_user.email = "inactive@example.com"
    fake_user.password_hash = "a-test-password-hash"
    fake_user.is_active = False

    fake_db.query.return_value.filter.return_value.first.return_value = fake_user

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("routes.auth.password_hasher.verify", return_value=True):
            response = client.post(
                "/auth/login",
                json={
                    "email": "inactive@example.com",
                    "password": "Password123!",
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "This account is inactive."
    finally:
        app.dependency_overrides.clear()

