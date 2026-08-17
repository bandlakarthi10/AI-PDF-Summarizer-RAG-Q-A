"""FastAPI application factory and startup lifecycle."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import logger
from app.api.routes_health import router as health_router
from app.api.routes_documents import router as documents_router
from app.api.routes_index import router as index_router
from app.api.routes_chat import router as chat_router
from app.api.routes_summary import router as summary_router
from app.models.schemas import DocumentStatus
from app.repositories.document_repository import document_repo
from app.services.vector_store_service import vector_store_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup synchronization check
    try:
        ready_docs = [d for d in document_repo.list_all() if d.status == DocumentStatus.READY]
        total_chunks = document_repo.get_total_chunk_count()
        current_vectors = vector_store_service.total_vectors

        if ready_docs and current_vectors == 0:
            logger.warning(
                f"Startup detected {len(ready_docs)} ready documents ({total_chunks} chunks) "
                f"but FAISS has {current_vectors} vectors. Running automatic startup sync..."
            )
            # Rebuild index from SQLite chunks
            chunks = document_repo.get_chunks()
            if chunks:
                vector_store_service.rebuild_from_chunks(chunks)
                logger.info(f"Startup FAISS sync completed: {vector_store_service.total_vectors} vectors restored.")
    except Exception as exc:
        logger.error(f"Startup synchronization failed: {exc}")

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Production-grade RAG application: upload PDFs, ask questions, "
            "get grounded answers with page citations using a local LLM."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _global_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {exc}"},
        )

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(index_router)
    app.include_router(chat_router)
    app.include_router(summary_router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"app": settings.APP_NAME, "docs": "/docs"}

    return app


app = create_app()
