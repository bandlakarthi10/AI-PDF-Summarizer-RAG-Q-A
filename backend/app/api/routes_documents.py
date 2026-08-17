"""Document upload, list, reprocess, and delete routes."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.logging_config import logger
from app.models.schemas import (
    DocumentListItem,
    DocumentRecord,
    DocumentStatus,
    UploadResponse,
)
from app.repositories.document_repository import document_repo
from app.services.ingestion_service import process_document
from app.services.vector_store_service import vector_store_service
from app.utils.file_utils import (
    generate_document_id,
    sanitize_filename,
    sha256_of_bytes,
    validate_pdf_upload,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a PDF. Returns 202 immediately; processing runs in the background.
    Poll GET /api/documents to see the document status progress to 'ready'.
    """
    content = await file.read()
    validate_pdf_upload(file, content, max_size_mb=settings.MAX_FILE_SIZE_MB)

    # ── Deduplication ─────────────────────────────────────────
    file_hash = sha256_of_bytes(content)
    existing = document_repo.get_by_hash(file_hash)
    if existing and existing.status == DocumentStatus.READY:
        logger.info(
            f"Duplicate upload detected for hash {file_hash[:8]}… "
            f"Returning existing document '{existing.document_id}'."
        )
        return UploadResponse(
            status="duplicate",
            message=(
                f"This PDF was already uploaded as '{existing.filename}'. "
                "Using existing indexed document."
            ),
            document_id=existing.document_id,
            filename=existing.filename,
            processing_status=existing.status,
        )

    document_id = generate_document_id()
    safe_name = sanitize_filename(file.filename or "document.pdf")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = DocumentRecord(
        document_id=document_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        file_path="",
        file_size_bytes=len(content),
        file_hash=file_hash,
        total_pages=0,
        pages_with_text=0,
        pages_without_text=0,
        chunk_count=0,
        extraction_method="pending",
        status=DocumentStatus.UPLOADED,
        current_page=0,
        progress_percent=0,
        created_at=now,
        updated_at=now,
    )
    document_repo.create(record)

    # Kick off background ingestion pipeline
    background_tasks.add_task(process_document, document_id, safe_name, content)

    logger.info(f"Accepted '{safe_name}' as {document_id} — processing started.")
    return UploadResponse(
        status="accepted",
        message=f"'{safe_name}' accepted. Processing started in background.",
        document_id=document_id,
        filename=safe_name,
        processing_status=DocumentStatus.UPLOADED,
    )


@router.post("/{document_id}/reprocess", response_model=UploadResponse, status_code=202)
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Re-run ingestion / OCR on an existing document (e.g. for documents in OCR_REQUIRED state).
    """
    doc = document_repo.get(document_id)
    if not doc:
        raise HTTPException(404, f"Document '{document_id}' not found.")

    # Find the persisted PDF file in uploads
    file_candidates = list(settings.upload_dir.glob(f"{document_id}_*"))
    if not file_candidates or not file_candidates[0].exists():
        raise HTTPException(404, f"Underlying PDF file for '{document_id}' not found on disk.")

    file_path = file_candidates[0]
    content = file_path.read_bytes()

    document_repo.update_status(document_id, DocumentStatus.PROCESSING, error_message="Starting re-processing...")
    background_tasks.add_task(process_document, document_id, doc.filename, content)

    return UploadResponse(
        status="accepted",
        message=f"Re-processing started for '{doc.filename}'.",
        document_id=document_id,
        filename=doc.filename,
        processing_status=DocumentStatus.PROCESSING,
    )


@router.get("", response_model=List[DocumentListItem])
async def list_documents():
    """List all documents with their current processing status."""
    docs = document_repo.list_all()
    return [
        DocumentListItem(
            document_id=d.document_id,
            filename=d.filename,
            total_pages=d.total_pages,
            file_size_bytes=d.file_size_bytes,
            chunk_count=d.chunk_count,
            extraction_method=d.extraction_method,
            status=d.status,
            current_page=d.current_page,
            progress_percent=d.progress_percent,
            error_message=d.error_message,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentListItem)
async def get_document(document_id: str):
    """Get status of a single document (useful for polling)."""
    doc = document_repo.get(document_id)
    if not doc:
        raise HTTPException(404, f"Document '{document_id}' not found.")
    return DocumentListItem(
        document_id=doc.document_id,
        filename=doc.filename,
        total_pages=doc.total_pages,
        file_size_bytes=doc.file_size_bytes,
        chunk_count=doc.chunk_count,
        extraction_method=doc.extraction_method,
        status=doc.status,
        current_page=doc.current_page,
        progress_percent=doc.progress_percent,
        error_message=doc.error_message,
        created_at=doc.created_at,
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document's metadata, SQLite chunks, and remove its vectors from FAISS."""
    doc = document_repo.get(document_id)
    if not doc:
        raise HTTPException(404, f"Document '{document_id}' not found.")

    vector_store_service.delete_document(document_id)
    document_repo.delete(document_id)

    # Clean up PDF file on disk
    for f in settings.upload_dir.glob(f"{document_id}_*"):
        try:
            f.unlink()
        except Exception:
            pass

    logger.info(f"Deleted document '{document_id}' ({doc.filename}).")
    return {"status": "deleted", "document_id": document_id}
