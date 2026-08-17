"""
Retrieval service - query -> FAISS -> structured Citation list.

Citations are constructed ENTIRELY from retrieval metadata.
The LLM never parses or invents citation data.
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.models.schemas import Citation
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service


class RetrievalService:
    MIN_SCORE = 0.10   # discard below this cosine-similarity threshold

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[Citation]:
        k = top_k or settings.TOP_K
        t0 = time.perf_counter()

        query_vec = embedding_service.embed_query(query)
        raw = vector_store_service.search(query_vec, top_k=k, document_ids=document_ids)

        citations: List[Citation] = []
        for meta, score in raw:
            if score < self.MIN_SCORE:
                continue
            citations.append(
                Citation(
                    chunk_id=meta["chunk_id"],
                    document_id=meta["document_id"],
                    filename=meta["filename"],
                    page_number=meta["page_number"],
                    score=round(score, 4),
                    snippet=meta["text"],
                )
            )

        logger.info(
            f"Retrieved {len(citations)}/{k} citations for query "
            f"'{query[:50]}…' in {(time.perf_counter()-t0)*1000:.0f}ms"
        )
        return citations

    def build_context(self, citations: List[Citation]) -> str:
        """Format citations into a numbered context block for the LLM prompt."""
        if not citations:
            return "NO RELEVANT CONTEXT FOUND IN THE UPLOADED DOCUMENTS."
        blocks = []
        for i, c in enumerate(citations, 1):
            blocks.append(
                f"[{i}] Source: {c.filename} — Page {c.page_number} "
                f"(relevance {c.score:.2f})\n{c.snippet.strip()}"
            )
        return "\n\n---\n\n".join(blocks)


# ── singleton ─────────────────────────────────────────────────
retrieval_service = RetrievalService()
