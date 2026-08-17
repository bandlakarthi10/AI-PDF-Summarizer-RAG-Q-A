"""Document summarisation endpoint with robust validation guards."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import DocumentStatus, SummaryResponse
from app.repositories.document_repository import document_repo
from app.services.summary_service import summary_service

router = APIRouter(prefix="/api/summary", tags=["Summary"])

_VALID_TYPES = {"short", "medium", "detailed"}


@router.post("/{document_id}", response_model=SummaryResponse)
async def summarise(
    document_id: str,
    summary_type: str = Query("medium", description="short | medium | detailed"),
):
    if summary_type not in _VALID_TYPES:
        raise HTTPException(
            400,
            f"Invalid summary_type '{summary_type}'. Choose from: {_VALID_TYPES}",
        )

    doc = document_repo.get(document_id)
    if not doc:
        raise HTTPException(404, f"Document '{document_id}' not found.")

    if doc.status == DocumentStatus.OCR_REQUIRED or doc.chunk_count == 0:
        raise HTTPException(
            400,
            f"Document '{doc.filename}' requires OCR before summarization. Please re-process the document with OCR first.",
        )

    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            400,
            f"Document '{doc.filename}' is currently {doc.status.value}. Please wait until processing completes.",
        )

    try:
        return await summary_service.summarise(document_id, summary_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except TimeoutError as exc:
        raise HTTPException(504, str(exc))
