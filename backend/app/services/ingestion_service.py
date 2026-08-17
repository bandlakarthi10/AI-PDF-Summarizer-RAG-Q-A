"""
Background document-processing pipeline with OCR support and status tracking.

Orchestrates: extract (with OCR fallback) -> chunk -> persist chunks to SQLite ->
embed -> index into FAISS -> mark READY.

Invariant:
A document is only marked READY after its chunks have been saved to SQLite,
embedded, and persisted to FAISS. If 0 chunks are found, it is marked OCR_REQUIRED.
"""
from __future__ import annotations

import time
from typing import Any, Dict

from app.core.logging_config import logger
from app.models.schemas import DocumentStatus
from app.repositories.document_repository import document_repo
from app.services.pdf_service import extract_pages
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service


def process_document(document_id: str, filename: str, content: bytes):
    """
    Full ingestion pipeline. Runs in a background thread.
    Errors are caught and written to document.error_message.
    """
    t_start = time.perf_counter()

    try:
        # ── Phase 1: extraction & OCR fallback ────────────────
        document_repo.update_status(document_id, DocumentStatus.EXTRACTING)

        def progress_cb(current_page: int, total_pages: int, pct: int, msg: str):
            document_repo.update_progress(
                document_id,
                current_page=current_page,
                total_pages=total_pages,
                progress_percent=pct,
                status=DocumentStatus.OCR_PROCESSING,
                error_message=msg,
            )

        extraction = extract_pages(filename, content, document_id, progress_callback=progress_cb)
        extraction_method = extraction.get("extraction_method", "native")

        # ── Phase 2: chunking ────────────────────────────────
        document_repo.update_status(document_id, DocumentStatus.CHUNKING, error_message=None)
        chunks = chunking_service.chunk_document(extraction)

        # ── Check if any chunks were generated ────────────────
        if len(chunks) == 0:
            final_status = DocumentStatus.OCR_REQUIRED
            err_msg = "No extractable text found in PDF. Outline or scanned content requires OCR."
            document_repo.update_stats(
                document_id=document_id,
                total_pages=extraction["total_pages"],
                pages_with_text=extraction["pages_with_text"],
                pages_without_text=extraction["pages_without_text"],
                chunk_count=0,
                extraction_method="none",
                status=final_status,
                error_message=err_msg,
            )
            logger.warning(f"[{document_id}] Ingestion completed with 0 chunks: marked as {final_status}.")
            return

        # ── Phase 3: Persist Chunks in SQLite ────────────────
        document_repo.save_chunks(document_id, chunks)
        logger.info(f"[{document_id}] Saved {len(chunks)} chunks to SQLite repository.")

        # ── Phase 4: embedding ───────────────────────────────
        document_repo.update_status(document_id, DocumentStatus.EMBEDDING)
        texts = [c["text"] for c in chunks]
        embeddings = embedding_service.embed_documents(texts) if texts else None

        # ── Phase 5: FAISS indexing ──────────────────────────
        document_repo.update_status(document_id, DocumentStatus.INDEXING)
        if embeddings is not None and len(embeddings):
            vector_store_service.add_chunks(chunks, embeddings)

        # ── Finalise: READY ──────────────────────────────────
        document_repo.update_stats(
            document_id=document_id,
            total_pages=extraction["total_pages"],
            pages_with_text=extraction["pages_with_text"],
            pages_without_text=extraction["pages_without_text"],
            chunk_count=len(chunks),
            extraction_method=extraction_method,
            status=DocumentStatus.READY,
            error_message=None,
        )

        elapsed = time.perf_counter() - t_start
        logger.info(
            f"[{document_id}] Processing complete in {elapsed:.1f}s — "
            f"{len(chunks)} chunks saved to DB & indexed into FAISS ({extraction_method})."
        )

    except Exception as exc:
        logger.error(f"[{document_id}] Processing FAILED: {exc}", exc_info=True)
        document_repo.update_status(
            document_id,
            DocumentStatus.FAILED,
            error_message=str(exc),
        )
