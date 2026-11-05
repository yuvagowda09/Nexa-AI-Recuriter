
import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile
from unittest.mock import patch

from resume_storage import save_pdf_resume, MAX_RESUME_SIZE


def test_valid_pdf_is_saved_with_generated_filename(tmp_path):
    upload = UploadFile(
        filename="my_resume.pdf",
        file=io.BytesIO(b"%PDF-1.4 test content"),
    )

    with patch("resume_storage.STORAGE_DIR", tmp_path):
        stored_name, destination = asyncio.run(save_pdf_resume(upload))

    assert stored_name.endswith(".pdf")
    assert stored_name != "my_resume.pdf"
    assert destination.parent == tmp_path
    assert destination.read_bytes() == b"%PDF-1.4 test content"


def test_non_pdf_extension_is_rejected(tmp_path):
    upload = UploadFile(
        filename="resume.txt",
        file=io.BytesIO(b"%PDF-1.4 test content"),
    )

    with patch("resume_storage.STORAGE_DIR", tmp_path):
        with pytest.raises(HTTPException) as error:
            asyncio.run(save_pdf_resume(upload))

    assert error.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_invalid_pdf_signature_is_rejected(tmp_path):
    upload = UploadFile(
        filename="resume.pdf",
        file=io.BytesIO(b"This is not a PDF"),
    )

    with patch("resume_storage.STORAGE_DIR", tmp_path):
        with pytest.raises(HTTPException) as error:
            asyncio.run(save_pdf_resume(upload))

    assert error.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_oversized_pdf_is_rejected_and_removed(tmp_path):
    oversized_content = b"%PDF-" + (
        b"A" * (MAX_RESUME_SIZE + 1)
    )

    upload = UploadFile(
        filename="large.pdf",
        file=io.BytesIO(oversized_content),
    )

    with patch("resume_storage.STORAGE_DIR", tmp_path):
        with pytest.raises(HTTPException) as error:
            asyncio.run(save_pdf_resume(upload))

    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []
