"""Tests for ChunkingService (no LLM, no embedding model)."""
from __future__ import annotations

import pytest
from app.services.chunking_service import ChunkingService


SAMPLE_TEXT = (
    "Section 1: Introduction.\n\n"
    "This product is designed for industrial use. "
    "Always follow safety guidelines before operating the device.\n\n"
    "Section 2: Maintenance.\n\n"
    "Perform monthly oil checks. Replace the filter every six months. "
    "Contact technical support for any issues not covered in this manual."
)


def test_chunks_have_required_fields():
    svc = ChunkingService(chunk_size=200, chunk_overlap=30)
    chunks = svc._split(SAMPLE_TEXT, "doc_1", "manual.pdf", 5)
    for c in chunks:
        assert "chunk_id" in c
        assert c["document_id"] == "doc_1"
        assert c["filename"] == "manual.pdf"
        assert c["page_number"] == 5
        assert "text" in c
        assert len(c["text"]) > 0


def test_chunks_respect_chunk_size():
    svc = ChunkingService(chunk_size=100, chunk_overlap=20)
    chunks = svc._split(SAMPLE_TEXT, "d", "f.pdf", 1)
    for c in chunks:
        # Allow a small margin for boundary alignment
        assert len(c["text"]) <= 130, f"Chunk too long: {len(c['text'])}"


def test_overlap_produces_multiple_chunks():
    svc = ChunkingService(chunk_size=80, chunk_overlap=20)
    chunks = svc._split(SAMPLE_TEXT, "d", "f.pdf", 1)
    assert len(chunks) >= 2


def test_empty_text_returns_no_chunks():
    svc = ChunkingService()
    assert svc._split("", "d", "f.pdf", 1) == []


def test_short_text_single_chunk():
    svc = ChunkingService(chunk_size=500)
    short = "Short text."
    chunks = svc._split(short, "d", "f.pdf", 1)
    assert len(chunks) == 1
    assert chunks[0]["text"] == short


def test_chunk_document_skips_empty_pages():
    extraction = {
        "document_id": "doc_x",
        "filename": "test.pdf",
        "pages": [
            {"page_number": 1, "has_text": True, "text": "Real content here."},
            {"page_number": 2, "has_text": False, "text": ""},
        ],
    }
    svc = ChunkingService()
    chunks = svc.chunk_document(extraction)
    assert all(c["page_number"] == 1 for c in chunks)
    assert len(chunks) > 0


def test_chunk_ids_are_unique():
    svc = ChunkingService(chunk_size=80, chunk_overlap=20)
    chunks = svc._split(SAMPLE_TEXT * 5, "d", "f.pdf", 1)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
