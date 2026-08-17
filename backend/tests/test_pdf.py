"""Tests for PDF extraction (no LLM, no Ollama required)."""
from __future__ import annotations

import io
import pytest
import pymupdf

from app.services.pdf_service import extract_pages
from app.utils.file_utils import validate_pdf_upload
from fastapi import HTTPException


def _make_pdf(pages: list[str]) -> bytes:
    """Create a minimal in-memory PDF with given per-page text strings."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── validate_pdf_upload ───────────────────────────────────────

class FakeUpload:
    def __init__(self, filename: str):
        self.filename = filename


def test_validate_rejects_empty():
    with pytest.raises(HTTPException) as ei:
        validate_pdf_upload(FakeUpload("a.pdf"), b"", max_size_mb=10)
    assert ei.value.status_code == 400


def test_validate_rejects_non_pdf_extension():
    with pytest.raises(HTTPException) as ei:
        validate_pdf_upload(FakeUpload("a.exe"), b"%PDF-1.4 fake", max_size_mb=10)
    assert ei.value.status_code == 400


def test_validate_rejects_wrong_magic():
    with pytest.raises(HTTPException) as ei:
        validate_pdf_upload(FakeUpload("a.pdf"), b"NOT A PDF", max_size_mb=10)
    assert ei.value.status_code == 400


def test_validate_rejects_oversized(tmp_path):
    content = _make_pdf(["hi"])
    # Set limit to 0 MB so even a tiny PDF is "too large"
    with pytest.raises(HTTPException) as ei:
        validate_pdf_upload(FakeUpload("a.pdf"), content, max_size_mb=0)
    assert ei.value.status_code == 400


def test_validate_accepts_valid_pdf():
    content = _make_pdf(["Valid content."])
    # Should not raise
    validate_pdf_upload(FakeUpload("a.pdf"), content, max_size_mb=10)


# ── extract_pages ─────────────────────────────────────────────

def test_extract_pages_basic():
    content = _make_pdf(["Warranty is 2 years.", "Maintenance monthly."])
    result = extract_pages("manual.pdf", content, "doc_test001")
    assert result["total_pages"] == 2
    assert result["pages_with_text"] == 2
    assert result["pages_without_text"] == 0
    assert "warranty" in result["pages"][0]["text"].lower()


def test_extract_pages_empty_page():
    content = _make_pdf(["First page text.", ""])   # second page has no text
    result = extract_pages("empty.pdf", content, "doc_test002")
    assert result["total_pages"] == 2
    assert result["pages_without_text"] == 1


def test_extract_metadata_fields():
    content = _make_pdf(["Test."])
    result = extract_pages("doc.pdf", content, "doc_test003")
    assert "document_id" in result
    assert "pages" in result
    assert result["pages"][0]["page_number"] == 1
    assert isinstance(result["pages"][0]["has_text"], bool)
