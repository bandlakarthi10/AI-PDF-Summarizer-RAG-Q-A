"""
FAISS vector store tests.

Uses a temporary directory and a mock embedding service so no model is downloaded.
Tests save→load persistence and document deletion with index rebuild.
"""
from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.vector_store_service import VectorStoreService

DIM = 384


def _rand_vecs(n: int) -> np.ndarray:
    v = np.random.randn(n, DIM).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _make_chunks(doc_id: str, filename: str, n: int):
    return [
        {
            "chunk_id": f"c{i}",
            "document_id": doc_id,
            "filename": filename,
            "page_number": i + 1,
            "start_char": 0,
            "end_char": 10,
            "text": f"Chunk {i} content for {doc_id}",
        }
        for i in range(n)
    ]


@pytest.fixture
def store(tmp_path: Path):
    """Fresh VectorStoreService backed by a temp directory."""
    with patch("app.services.vector_store_service.settings") as mock_settings:
        mock_settings.vectorstore_dir = tmp_path
        mock_settings.EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
        svc = VectorStoreService(store_dir=tmp_path)
        yield svc


def test_initially_empty(store):
    assert store.total_vectors == 0


def test_add_and_search(store):
    chunks = _make_chunks("docA", "a.pdf", 3)
    vecs = _rand_vecs(3)
    store.add_chunks(chunks, vecs)

    assert store.total_vectors == 3

    query = vecs[0:1]   # search for the first chunk's own vector
    results = store.search(query, top_k=1)
    assert len(results) == 1
    meta, score = results[0]
    assert meta["document_id"] == "docA"
    assert score > 0.9   # exact match → near-1 cosine similarity


def test_persistence(tmp_path: Path):
    """Save index then reload in a new instance — vectors must survive."""
    with patch("app.services.vector_store_service.settings") as ms:
        ms.vectorstore_dir = tmp_path
        ms.EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
        store1 = VectorStoreService(store_dir=tmp_path)
        chunks = _make_chunks("docB", "b.pdf", 2)
        vecs = _rand_vecs(2)
        store1.add_chunks(chunks, vecs)

    with patch("app.services.vector_store_service.settings") as ms:
        ms.vectorstore_dir = tmp_path
        ms.EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
        store2 = VectorStoreService(store_dir=tmp_path)
        assert store2.total_vectors == 2


def test_delete_document(store):
    a_chunks = _make_chunks("docA", "a.pdf", 3)
    b_chunks = _make_chunks("docB", "b.pdf", 2)
    a_vecs = _rand_vecs(3)
    b_vecs = _rand_vecs(2)

    store.add_chunks(a_chunks, a_vecs)
    store.add_chunks(b_chunks, b_vecs)
    assert store.total_vectors == 5

    # Inject a mock embedding service so delete_document can re-embed
    # the remaining chunks without loading the real SentenceTransformer model.
    mock_emb = MagicMock()
    mock_emb.embed_documents.return_value = b_vecs   # 2 remaining docB chunks

    import app.services.vector_store_service as vss_mod
    original = vss_mod._emb_module
    try:
        vss_mod._emb_module = MagicMock()
        vss_mod._emb_module.embedding_service = mock_emb
        deleted = store.delete_document("docA")
    finally:
        vss_mod._emb_module = original

    assert deleted is True
    assert store.total_vectors == 2
    # Remaining chunks must be from docB
    for meta in store._meta:
        assert meta["document_id"] == "docB"


def test_delete_nonexistent_returns_false(store):
    assert store.delete_document("does_not_exist") is False


def test_filter_by_document_id(store):
    a_chunks = _make_chunks("docA", "a.pdf", 2)
    b_chunks = _make_chunks("docB", "b.pdf", 2)
    a_vecs = _rand_vecs(2)
    b_vecs = _rand_vecs(2)
    store.add_chunks(a_chunks, a_vecs)
    store.add_chunks(b_chunks, b_vecs)

    query = _rand_vecs(1)
    results = store.search(query, top_k=10, document_ids=["docA"])
    assert all(m["document_id"] == "docA" for m, _ in results)
