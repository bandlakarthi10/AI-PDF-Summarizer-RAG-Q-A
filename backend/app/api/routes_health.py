"""Health check and diagnostic endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.repositories.document_repository import document_repo
from app.services.llm_service import llm_service
from app.services.vector_store_service import vector_store_service

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Returns the health of every subsystem:
    - Embedding model status (configured vs loaded)
    - FAISS vector count & total database chunks (in_sync detection)
    - Document registry summary counts
    - Ollama connectivity and model availability
    """
    ollama_info = await llm_service.check()

    if ollama_info["available"]:
        ollama_status = "available" if ollama_info["has_model"] else "model_missing"
    else:
        ollama_status = f"unavailable — {ollama_info.get('reason', '')}"

    # Embedding model status
    from app.services.embedding_service import embedding_service
    if embedding_service._model is not None:
        emb_status = "loaded"
    else:
        emb_status = "configured"

    faiss_vectors = vector_store_service.total_vectors
    total_db_chunks = document_repo.get_total_chunk_count()
    ready_docs = document_repo.get_ready_documents_count()
    total_docs = document_repo.get_total_documents_count()

    # Index is in sync if vector count matches database chunk count
    # (If there are 0 ready docs and 0 chunks and 0 vectors, it is in sync)
    index_in_sync = (faiss_vectors == total_db_chunks)

    return HealthResponse(
        status="ok",
        embedding_model=emb_status,
        embedding_model_name=settings.EMBEDDING_MODEL,
        faiss="ready" if vector_store_service._index is not None else "not_ready",
        faiss_total_vectors=faiss_vectors,
        total_chunks=total_db_chunks,
        index_in_sync=index_in_sync,
        ready_documents_count=ready_docs,
        total_documents_count=total_docs,
        ollama=ollama_status,
        ollama_model=settings.OLLAMA_MODEL,
        ollama_available_models=ollama_info.get("models", []),
    )
