
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from dependencies import get_db
from main import app
from security import get_current_user


def test_company_cannot_upload_resume_for_another_company_candidate():
    company_a_user = SimpleNamespace(
        id=1,
        organization_id=101,
        is_active=True,
        role="admin",
    )

    fake_db = MagicMock()

    # Candidate ID 55 is not accessible to Company A.
    fake_db.query.return_value.filter.return_value.first.return_value = None

    def override_get_db():
        yield fake_db

    def override_get_current_user():
        return company_a_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with patch(
            "routes.candidates.save_pdf_resume",
            new_callable=AsyncMock,
        ) as save_resume:
            with TestClient(app) as client:
                response = client.post(
                    "/candidates/55/resumes",
                    files={
                        "file": (
                            "resume.pdf",
                            b"%PDF-1.4 test content",
                            "application/pdf",
                        )
                    },
                )

        assert response.status_code == 404
        assert response.json()["detail"] == "Candidate not found."

        # The file must not be saved for an inaccessible candidate.
        save_resume.assert_not_awaited()

        # No resume record should be created.
        fake_db.add.assert_not_called()
        fake_db.commit.assert_not_called()

    finally:
        app.dependency_overrides.clear()
