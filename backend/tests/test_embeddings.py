"""
Embedding service tests.

Fast tests use a mock model so the BAAI/bge model is NOT downloaded.
One optional integration test actually loads the model (skipped by default).
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.services.embedding_service import EmbeddingService

DIM = 384


def _mock_service() -> EmbeddingService:
    """Return an EmbeddingService with a fake model injected."""
    svc = EmbeddingService(model_name="mock")

    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = DIM

    def _encode(texts, **kwargs):
        n = len(texts) if isinstance(texts, list) else 1
        vecs = np.random.randn(n, DIM).astype(np.float32)
        # Normalise (as the real model would)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms

    mock_model.encode = _encode
    svc._model = mock_model
    svc._dim = DIM
    return svc


def test_embed_documents_shape():
    svc = _mock_service()
    texts = ["Hello.", "World."]
    vecs = svc.embed_documents(texts)
    assert vecs.shape == (2, DIM)
    assert vecs.dtype == np.float32


def test_embed_documents_empty():
    svc = _mock_service()
    vecs = svc.embed_documents([])
    assert vecs.shape == (0, DIM)


def test_embed_query_shape():
    svc = _mock_service()
    q = svc.embed_query("What is the warranty?")
    assert q.shape == (1, DIM)


def test_embed_query_empty_raises():
    svc = _mock_service()
    with pytest.raises(ValueError):
        svc.embed_query("   ")


def test_embeddings_are_normalised():
    svc = _mock_service()
    vecs = svc.embed_documents(["test sentence"])
    norm = np.linalg.norm(vecs[0])
    assert abs(norm - 1.0) < 0.01


def test_get_dimension():
    svc = _mock_service()
    assert svc.get_dimension() == DIM


# ── Optional real-model integration test ─────────────────────

@pytest.mark.skip(reason="Downloads ~130 MB model — run manually with: pytest -k real_model")
def test_real_model_embed():
    svc = EmbeddingService()
    vecs = svc.embed_documents(["Product warranty is 2 years."])
    assert vecs.shape[0] == 1
    assert vecs.shape[1] > 0
