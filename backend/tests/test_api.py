"""
API integration tests using FastAPI TestClient.

All external services (Ollama, embedding model) are mocked so these tests
run fully offline with no model downloads required.
"""
from __future__ import annotations

import io
import numpy as np
import pytest
import pymupdf
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# Patch vector store BEFORE importing app so the singleton uses tmp storage
import tempfile, os
_TMP_VSTORE = tempfile.mkdtemp()

DIM = 384


def _make_pdf_bytes(text: str = "Product warranty is 2 years.") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _mock_emb():
    m = MagicMock()
    m.embed_documents.return_value = np.random.randn(1, DIM).astype(np.float32)
    m.embed_query.return_value = np.random.randn(1, DIM).astype(np.float32)
    m.get_dimension.return_value = DIM
    m._model = MagicMock()   # pretend loaded
    return m


@pytest.fixture(scope="module")
def client():
    """Return a TestClient with all external services mocked."""
    mock_emb = _mock_emb()
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "The warranty is 2 years."
    mock_llm.check.return_value = {
        "available": True,
        "has_model": True,
        "models": ["llama3.2:latest"],
    }

    with (
        patch("app.services.embedding_service.embedding_service", mock_emb),
        patch("app.services.retrieval_service.embedding_service", mock_emb),
        patch("app.services.rag_service.llm_service", mock_llm),
        patch("app.services.llm_service.llm_service", mock_llm),
        patch("app.api.routes_health.llm_service", mock_llm),
    ):
        from app.main import create_app
        app = create_app()
        with TestClient(app) as c:
            yield c


# ── Health ────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "embedding_model" in data
    assert "faiss" in data
    assert "ollama" in data


# ── Documents ─────────────────────────────────────────────────

def test_list_documents_empty(client):
    r = client.get("/api/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_upload_valid_pdf(client):
    pdf_bytes = _make_pdf_bytes()
    r = client.post(
        "/api/documents/upload",
        files={"file": ("test_warranty.pdf", pdf_bytes, "application/pdf")},
    )
    # 202 Accepted (background processing started)
    assert r.status_code in (200, 202)
    data = r.json()
    assert "document_id" in data
    assert data["filename"] == "test_warranty.pdf"


def test_upload_non_pdf_rejected(client):
    r = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"some bytes", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_upload_empty_file_rejected(client):
    r = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert r.status_code == 400


def test_delete_nonexistent_document(client):
    r = client.delete("/api/documents/doc_does_not_exist")
    assert r.status_code == 404


# ── Chat ──────────────────────────────────────────────────────

def test_chat_empty_question_rejected(client):
    r = client.post("/api/chat", json={"question": ""})
    # Pydantic min_length=1 raises 422; explicit route check raises 400 — both are correct rejections
    assert r.status_code in (400, 422)


def test_chat_empty_question_whitespace_rejected(client):
    r = client.post("/api/chat", json={"question": "   "})
    assert r.status_code == 400


# ── Summary ───────────────────────────────────────────────────

def test_summary_invalid_type(client):
    r = client.post("/api/summary/doc_fake?summary_type=invalid")
    assert r.status_code == 400


def test_summary_nonexistent_document(client):
    r = client.post("/api/summary/doc_does_not_exist?summary_type=short")
    assert r.status_code == 404
