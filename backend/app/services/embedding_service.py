"""
Embedding service — lazy-loads the SentenceTransformer model once.

The model is NOT loaded at import time; it is loaded on first use.
This keeps startup fast and allows tests to inject a mock.
"""
from __future__ import annotations

import time
from typing import List

import numpy as np

from app.core.config import settings
from app.core.logging_config import logger


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None      # loaded lazily
        self._dim: int | None = None

    # ── lazy loader ───────────────────────────────────────────

    def _load_model(self):
        """Load model once; subsequent calls are no-ops."""
        if self._model is not None:
            return

        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading embedding model '{self.model_name}' on {device} …")
        t0 = time.perf_counter()
        self._model = SentenceTransformer(self.model_name, device=device)
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info(
            f"Embedding model loaded (dim={self._dim}) in {time.perf_counter()-t0:.1f}s"
        )

    # ── public API ────────────────────────────────────────────

    def get_dimension(self) -> int:
        self._load_model()
        return self._dim  # type: ignore[return-value]

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Return an (N, D) float32 array of L2-normalised embeddings."""
        if not texts:
            return np.empty((0, self.get_dimension()), dtype=np.float32)

        self._load_model()
        t0 = time.perf_counter()
        vecs = self._model.encode(  # type: ignore[union-attr]
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        elapsed = time.perf_counter() - t0
        logger.info(
            f"Embedded {len(texts)} chunks in {elapsed:.2f}s "
            f"({elapsed/len(texts)*1000:.1f} ms/chunk)"
        )
        return vecs.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Return a (1, D) float32 array."""
        if not query.strip():
            raise ValueError("Query text cannot be empty.")
        self._load_model()
        vec = self._model.encode(  # type: ignore[union-attr]
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vec.astype(np.float32)


# ── singleton ─────────────────────────────────────────────────
embedding_service = EmbeddingService()
