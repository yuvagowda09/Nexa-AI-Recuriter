
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_jobs_list_requires_authentication():
    response = client.get("/jobs/")

    assert response.status_code == 401


def test_jobs_create_requires_authentication():
    response = client.post(
        "/jobs/",
        json={
            "title": "Test Python Developer",
            "description": "Test-only job description",
            "location": "Bengaluru",
            "status": "active",
        },
    )

    assert response.status_code == 401



def test_ai_job_description_requires_authentication():
    response = client.post(
        "/ai/generate-job-description",
        json={
            "title": "Python Developer",
            "skills": ["Python", "FastAPI"],
            "experience": "2 years",
        },
    )

    assert response.status_code == 401

