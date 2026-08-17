"""
RAG service tests — Ollama and embedding model are both mocked.
All tests run fully offline.

Rule 27 (No-Hallucination) tests:
  1. Known fact → answer contains that fact AND sources are returned.
  2. Unknown fact → LLM replies "not found"; sources may or may not be empty.
  3. Empty vector store → immediate refusal, no LLM call at all.
"""
from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.schemas import ChatRequest
from app.services.rag_service import RAGService

DIM = 384
_REFUSAL = "The information requested was not found in the uploaded document."


def _norm(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _warranty_chunk(doc_id: str):
    return {
        "chunk_id": f"chk_{doc_id}",
        "document_id": doc_id,
        "filename": "warranty_guide.pdf",
        "page_number": 3,
        "start_char": 0,
        "end_char": 47,
        "text": "Product warranty is 2 years from purchase date.",
    }


# ── Helper: build an isolated store + mock emb ───────────────

def _isolated_store(tmp_path, doc_id, emb_vec, chunk):
    from app.services.vector_store_service import VectorStoreService
    vstore = VectorStoreService(store_dir=tmp_path)
    vstore.add_chunks([chunk], emb_vec)
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = emb_vec   # same vec → high similarity
    return vstore, mock_emb


# ── Rule-27 Test 1: known fact ────────────────────────────────

async def test_known_fact_returns_grounded_answer(tmp_path):
    doc_id = "doc_rule27a"
    vec = _norm(np.random.randn(1, DIM).astype(np.float32))
    chunk = _warranty_chunk(doc_id)

    vstore, mock_emb = _isolated_store(tmp_path, doc_id, vec, chunk)

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        "The product warranty is 2 years from purchase date "
        "[warranty_guide.pdf, page 3]."
    )

    with (
        patch("app.services.retrieval_service.embedding_service", mock_emb),
        patch("app.services.retrieval_service.vector_store_service", vstore),
        patch("app.services.rag_service.llm_service", mock_llm),
    ):
        svc = RAGService()
        resp = await svc.answer(
            ChatRequest(question="What is the warranty period?", document_ids=[doc_id])
        )

    assert "2 years" in resp.answer.lower()
    assert len(resp.sources) > 0
    assert resp.sources[0].filename == "warranty_guide.pdf"
    assert resp.sources[0].page_number == 3
    mock_llm.generate.assert_called_once()  # LLM was called exactly once


# ── Rule-27 Test 2: unknown fact → LLM must refuse ───────────

async def test_unknown_fact_llm_refuses(tmp_path):
    """
    CEO name not in document.  LLM is mocked to return the refusal string
    (as a well-instructed LLM should).  Test verifies the refusal reaches
    the caller and is not silently transformed into a fabricated answer.
    """
    doc_id = "doc_rule27b"
    vec = _norm(np.random.randn(1, DIM).astype(np.float32))
    chunk = _warranty_chunk(doc_id)

    vstore, mock_emb = _isolated_store(tmp_path, doc_id, vec, chunk)

    mock_llm = AsyncMock()
    # A correctly-prompted LLM returns the refusal for out-of-context questions
    mock_llm.generate.return_value = _REFUSAL

    with (
        patch("app.services.retrieval_service.embedding_service", mock_emb),
        patch("app.services.retrieval_service.vector_store_service", vstore),
        patch("app.services.rag_service.llm_service", mock_llm),
    ):
        svc = RAGService()
        resp = await svc.answer(
            ChatRequest(question="Who is the CEO?", document_ids=[doc_id])
        )

    ans_lower = resp.answer.lower()
    assert (
        "not found" in ans_lower or "information requested" in ans_lower
    ), f"Expected refusal, got: {resp.answer!r}"


# ── Rule-27 Test 3: empty store → refusal without LLM ────────

async def test_empty_vectorstore_returns_refusal_without_llm():
    """When FAISS is empty, the service must refuse immediately — no LLM call."""
    empty_store = MagicMock()
    empty_store.total_vectors = 0
    empty_store.search.return_value = []

    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = _norm(np.random.randn(1, DIM).astype(np.float32))

    mock_llm = AsyncMock()  # should NOT be called

    with (
        patch("app.services.retrieval_service.embedding_service", mock_emb),
        patch("app.services.retrieval_service.vector_store_service", empty_store),
        patch("app.services.rag_service.llm_service", mock_llm),
    ):
        svc = RAGService()
        resp = await svc.answer(ChatRequest(question="Anything?"))

    assert resp.sources == []
    assert "not found" in resp.answer.lower()
    mock_llm.generate.assert_not_called()   # LLM must NOT have been called


# ── Conversation memory test ──────────────────────────────────

async def test_conversation_id_is_returned():
    empty_store = MagicMock()
    empty_store.search.return_value = []
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = _norm(np.random.randn(1, DIM).astype(np.float32))

    with (
        patch("app.services.retrieval_service.embedding_service", mock_emb),
        patch("app.services.retrieval_service.vector_store_service", empty_store),
    ):
        svc = RAGService()
        resp = await svc.answer(ChatRequest(question="Test?"))

    assert resp.conversation_id
    assert resp.conversation_id.startswith("conv_")
