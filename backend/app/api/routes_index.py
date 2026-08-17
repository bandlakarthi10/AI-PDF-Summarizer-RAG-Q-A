"""Index management routes — FAISS rebuild and diagnostics."""
from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException

from app.core.logging_config import logger
from app.models.schemas import DocumentStatus, RebuildIndexResponse
from app.repositories.document_repository import document_repo
from app.services.chunking_service import chunking_service
from app.services.pdf_service import extract_pages
from app.services.vector_store_service import vector_store_service

router = APIRouter(prefix="/api/index", tags=["Index"])


@router.post("/rebuild", response_model=RebuildIndexResponse)
async def rebuild_index():
    """
    Canonical FAISS index rebuild endpoint.
    - Gathers all chunks for READY documents from the SQLite database.
    - If chunks table is empty for an existing ready document, regenerates chunks from disk.
    - Re-embeds all chunks and recreates the FAISS index cleanly.
    - Returns synchronized documents, chunks, and vector counts.
    """
    t0 = time.perf_counter()
    ready_docs = [d for d in document_repo.list_all() if d.status == DocumentStatus.READY]
    
    all_chunks = []
    
    for doc in ready_docs:
        chunks = document_repo.get_chunks(doc.document_id)
        if not chunks:
            # Migration fallback: if document was ready before SQLite chunks table existed, re-chunk from file
            file_candidates = list(document_repo.db_path.parent.joinpath("uploads").glob(f"{doc.document_id}_*"))
            if file_candidates and file_candidates[0].exists():
                logger.info(f"Re-chunking legacy document '{doc.document_id}' during rebuild...")
                content = file_candidates[0].read_bytes()
                extraction = extract_pages(doc.filename, content, doc.document_id)
                new_chunks = chunking_service.chunk_document(extraction)
                if new_chunks:
                    document_repo.save_chunks(doc.document_id, new_chunks)
                    chunks = new_chunks
        all_chunks.extend(chunks)

    total_vectors = vector_store_service.rebuild_from_chunks(all_chunks)
    elapsed = time.perf_counter() - t0

    logger.info(
        f"Index rebuild finished in {elapsed:.2f}s: {len(ready_docs)} ready docs, "
        f"{len(all_chunks)} chunks, {total_vectors} vectors."
    )

    return RebuildIndexResponse(
        status="success",
        documents=len(ready_docs),
        chunks=len(all_chunks),
        vectors=total_vectors,
        message=f"FAISS index successfully rebuilt with {total_vectors} vectors across {len(ready_docs)} documents in {elapsed:.2f}s.",
    )
