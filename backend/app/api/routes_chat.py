"""RAG chat endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question against one or more uploaded documents.

    - Retrieves the most relevant chunks from FAISS.
    - Constructs citations from retrieval metadata (no LLM parsing).
    - Generates a grounded answer via the local Ollama LLM.
    """
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    try:
        return await rag_service.answer(request)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except TimeoutError as exc:
        raise HTTPException(504, str(exc))
