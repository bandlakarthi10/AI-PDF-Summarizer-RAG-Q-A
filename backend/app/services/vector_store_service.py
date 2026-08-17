"""
FAISS vector store with persistent index, metadata side-car, and manifest.

Design decisions
────────────────
- IndexFlatIP works correctly for cosine similarity when vectors are L2-normalised.
- Metadata (chunk dicts) is stored in a parallel JSON list; the list index maps
  1-to-1 to FAISS integer IDs.
- Manifest tracks generation, vector_count, chunk_count, and timestamp to provide
  instant out-of-sync detection.
- Rebuilding can be executed on-demand directly from the SQLite chunks table
  without needing to re-parse or re-OCR PDFs.
- Index, metadata, and manifest are always written together.
"""
from __future__ import annotations

import json
import time
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from app.core.config import settings
from app.core.logging_config import logger
from app.services import embedding_service as _emb_module


class VectorStoreService:
    def __init__(self, store_dir: Path | None = None):
        self._dir = store_dir or settings.vectorstore_dir
        self._index_file = self._dir / "faiss.index"
        self._meta_file = self._dir / "metadata.json"
        self._manifest_file = self._dir / "manifest.json"

        self._index: Optional[faiss.Index] = None
        self._meta: List[Dict[str, Any]] = []
        self._manifest: Dict[str, Any] = {}

        self._load()

    # ── persistence ───────────────────────────────────────────

    def _load(self):
        dim = self._get_dim_from_config()
        if self._index_file.exists() and self._meta_file.exists():
            try:
                self._index = faiss.read_index(str(self._index_file))
                self._meta = json.loads(self._meta_file.read_text("utf-8"))
                
                if self._manifest_file.exists():
                    try:
                        self._manifest = json.loads(self._manifest_file.read_text("utf-8"))
                    except Exception:
                        self._manifest = {}

                if self._index.ntotal != len(self._meta):
                    logger.warning(
                        f"FAISS/metadata size mismatch ({self._index.ntotal} vs {len(self._meta)}). "
                        "Recreating clean index."
                    )
                    self._create_fresh(dim)
                else:
                    logger.info(
                        f"Loaded FAISS index: {self._index.ntotal} vectors, dim={self._index.d}"
                    )
                    return
            except Exception as exc:
                logger.error(f"Could not load FAISS index ({exc}). Recreating clean index.")

        self._create_fresh(dim)

    def _create_fresh(self, dim: int):
        self._index = faiss.IndexFlatIP(dim)
        self._meta = []
        self._manifest = {
            "generation": 1,
            "vector_count": 0,
            "chunk_count": 0,
            "embedding_model": settings.EMBEDDING_MODEL,
            "dimension": dim,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self._persist()
        logger.info(f"Created new FAISS IndexFlatIP (dim={dim}).")

    def _persist(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            faiss.write_index(self._index, str(self._index_file))
        self._meta_file.write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=1), "utf-8"
        )
        self._manifest["vector_count"] = self.total_vectors
        self._manifest["chunk_count"] = len(self._meta)
        self._manifest["dimension"] = self._index.d if self._index else self._get_dim_from_config()
        self._manifest["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._manifest_file.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2), "utf-8"
        )

    def _get_dim_from_config(self) -> int:
        _MODEL_DIMS = {
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
        }
        return _MODEL_DIMS.get(settings.EMBEDDING_MODEL, 384)

    # ── public API ────────────────────────────────────────────

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        if not chunks:
            return
        assert len(chunks) == len(embeddings), "Chunk/embedding count mismatch"

        vecs = np.ascontiguousarray(embeddings, dtype=np.float32)
        self._index.add(vecs)
        self._meta.extend(chunks)
        self._manifest["generation"] = self._manifest.get("generation", 0) + 1
        self._persist()
        logger.info(f"Added {len(chunks)} vectors. Total in FAISS: {self._index.ntotal}")

    def rebuild_from_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Reconstruct FAISS index completely from a list of chunk dicts.
        Computes new embeddings and writes new index, metadata, and manifest atomically.
        """
        dim = self._get_dim_from_config()
        t0 = time.perf_counter()
        logger.info(f"Starting FAISS rebuild with {len(chunks)} chunks...")

        self._create_fresh(dim)
        if not chunks:
            logger.info("Rebuild complete: 0 chunks.")
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = _emb_module.embedding_service.embed_documents(texts)
        self.add_chunks(chunks, embeddings)
        
        elapsed = time.perf_counter() - t0
        logger.info(f"FAISS index rebuilt successfully with {self.total_vectors} vectors in {elapsed:.2f}s")
        return self.total_vectors

    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Return [(chunk_meta, score)] sorted by descending score."""
        if self._index is None or self._index.ntotal == 0:
            return []

        # Over-fetch to allow document_id filtering
        k = min(top_k * 5 if document_ids else top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, k)

        results: List[Tuple[Dict[str, Any], float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._meta):
                continue
            meta = self._meta[idx]
            if document_ids and meta.get("document_id") not in document_ids:
                continue
            results.append((meta, float(score)))
            if len(results) >= top_k:
                break

        return results

    def delete_document(self, document_id: str) -> bool:
        """Remove all chunks for document_id and rebuild the index."""
        remaining = [m for m in self._meta if m.get("document_id") != document_id]
        if len(remaining) == len(self._meta):
            return False

        logger.info(
            f"Rebuilding FAISS after deleting doc '{document_id}'. "
            f"{len(self._meta) - len(remaining)} vectors removed."
        )

        dim = self._index.d if self._index else self._get_dim_from_config()
        self._create_fresh(dim)

        if not remaining:
            return True

        texts = [c["text"] for c in remaining]
        t0 = time.perf_counter()
        vecs = _emb_module.embedding_service.embed_documents(texts)
        self.add_chunks(remaining, vecs)
        logger.info(f"Rebuild complete in {time.perf_counter()-t0:.1f}s")
        return True


# ── singleton ─────────────────────────────────────────────────
vector_store_service = VectorStoreService()
