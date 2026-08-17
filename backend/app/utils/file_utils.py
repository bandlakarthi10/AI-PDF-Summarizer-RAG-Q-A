"""
File-level utilities: validation, safe naming, deduplication hashing.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf"}


# ── public helpers ────────────────────────────────────────────

def sanitize_filename(filename: str) -> str:
    """Strip directory components and replace unsafe characters."""
    name = Path(filename).name
    name = re.sub(r"[^\w\.\-]", "_", name)
    return name or "document.pdf"


def generate_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf_upload(file: UploadFile, content: bytes, max_size_mb: int) -> None:
    """Raise HTTPException for any invalid upload condition."""
    if not content:
        raise HTTPException(400, "Uploaded file is empty (0 bytes).")

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        mb = len(content) / (1024 * 1024)
        raise HTTPException(
            400,
            f"File too large ({mb:.1f} MB). Maximum allowed is {max_size_mb} MB.",
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Invalid file type '{ext}'. Only PDF files (.pdf) are accepted.",
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            400,
            "File does not have a valid PDF header. Upload a valid PDF document.",
        )
