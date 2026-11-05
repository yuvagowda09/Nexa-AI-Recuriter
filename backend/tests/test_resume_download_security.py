
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dependencies import get_db
from models import Candidate, Resume, User
from routes.candidates import router
from security import get_current_user


app = FastAPI()
app.include_router(router)

fake_db = MagicMock()
fake_user = User(
    id=1,
    organization_id=101,
    name="Test Recruiter",
    email="recruiter@example.com",
    role="recruiter",
    is_active=True,
)

app.dependency_overrides[get_db] = lambda: fake_db
app.dependency_overrides[get_current_user] = lambda: fake_user

client = TestClient(app)


def test_download_returns_404_for_another_company_resume(tmp_path):
    fake_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

    with patch("routes.candidates.STORAGE_DIR", tmp_path):
        response = client.get("/candidates/20/resumes/55/download")

    assert response.status_code == 404


def test_download_returns_pdf_for_authorized_company(tmp_path):
    pdf_file = tmp_path / "private-test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test content")

    fake_resume = MagicMock(spec=Resume)
    fake_resume.id = 55
    fake_resume.candidate_id = 20
    fake_resume.file_path = pdf_file.name

    fake_db.query.return_value.join.return_value.filter.return_value.first.return_value = fake_resume

    with patch("routes.candidates.STORAGE_DIR", tmp_path):
        response = client.get("/candidates/20/resumes/55/download")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 test content"
    assert "attachment" in response.headers["content-disposition"]


def test_download_rejects_path_outside_private_storage(tmp_path):
    outside_file = tmp_path.parent / "outside-test.pdf"
    outside_file.write_bytes(b"%PDF-1.4 should not be served")

    fake_resume = MagicMock(spec=Resume)
    fake_resume.id = 55
    fake_resume.candidate_id = 20
    fake_resume.file_path = str(outside_file)

    fake_db.query.return_value.join.return_value.filter.return_value.first.return_value = fake_resume

    try:
        with patch("routes.candidates.STORAGE_DIR", tmp_path):
            response = client.get("/candidates/20/resumes/55/download")

        assert response.status_code == 404
    finally:
        outside_file.unlink(missing_ok=True)
