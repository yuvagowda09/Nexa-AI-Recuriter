
import os
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 64 * 1024

# Defaults to a private folder under the backend directory.
# Production can set RESUME_STORAGE_DIR to a protected volume.
STORAGE_DIR = Path(
    os.getenv("RESUME_STORAGE_DIR", str(Path(__file__).resolve().parent / "private_resumes"))
).resolve()


async def save_pdf_resume(upload: UploadFile) -> tuple[str, Path]:
    if upload.filename is None or Path(upload.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resumes are allowed.",
        )

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    stored_name = f"{secrets.token_hex(24)}.pdf"
    destination = STORAGE_DIR / stored_name
    total_size = 0
    header = b""

    try:
        with destination.open("xb") as output:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > MAX_RESUME_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Resume file must be 5 MB or smaller.",
                    )

                if len(header) < 5:
                    header += chunk[: 5 - len(header)]

                output.write(chunk)

        if header != b"%PDF-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid PDF.",
            )

        return stored_name, destination

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    finally:
        await upload.close()
