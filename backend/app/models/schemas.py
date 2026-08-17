from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Document status lifecycle
# ──────────────────────────────────────────────
class DocumentStatus(str, Enum):
    UPLOADED        = "uploaded"
    PROCESSING      = "processing"
    EXTRACTING      = "extracting"
    OCR_REQUIRED    = "ocr_required"
    OCR_PROCESSING  = "ocr_processing"
    CHUNKING        = "chunking"
    EMBEDDING       = "embedding"
    INDEXING        = "indexing"
    READY           = "ready"
    FAILED          = "failed"
    OCR_FAILED      = "ocr_failed"
    INDEXING_FAILED = "indexing_failed"


# ──────────────────────────────────────────────
# Document & chunk schemas
# ──────────────────────────────────────────────
class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    original_filename: str
    file_path: str
    file_size_bytes: int
    file_hash: str
    total_pages: int
    pages_with_text: int
    pages_without_text: int
    chunk_count: int
    extraction_method: str = "pending"  # "native" | "ocr" | "pending" | "none"
    status: DocumentStatus
    current_page: int = 0
    progress_percent: int = 0
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class ChunkRecord(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    start_char: int
    end_char: int
    text: str


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    score: float
    snippet: str


# ──────────────────────────────────────────────
# API — Upload
# ──────────────────────────────────────────────
class UploadResponse(BaseModel):
    status: str
    message: str
    document_id: str
    filename: str
    processing_status: DocumentStatus


# ──────────────────────────────────────────────
# API — Documents list
# ──────────────────────────────────────────────
class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    file_size_bytes: int
    chunk_count: int
    extraction_method: str = "pending"
    status: DocumentStatus
    current_page: int = 0
    progress_percent: int = 0
    error_message: Optional[str] = None
    created_at: str


# ──────────────────────────────────────────────
# API — Index Rebuild
# ──────────────────────────────────────────────
class RebuildIndexResponse(BaseModel):
    status: str
    documents: int
    chunks: int
    vectors: int
    message: str


# ──────────────────────────────────────────────
# API — Chat
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    sources: List[Citation]
    conversation_id: str


# ──────────────────────────────────────────────
# API — Summary
# ──────────────────────────────────────────────
class SummaryRequest(BaseModel):
    summary_type: str = Field(default="medium")


class SummaryResponse(BaseModel):
    document_id: str
    filename: str
    summary_type: str
    overview: str
    key_points: List[str]
    important_procedures: List[str]
    warnings: List[str]
    conclusions: Optional[str] = None
    raw_summary: str


# ──────────────────────────────────────────────
# API — Health
# ──────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    embedding_model: str
    embedding_model_name: str
    faiss: str
    faiss_total_vectors: int
    total_chunks: int
    index_in_sync: bool
    ready_documents_count: int
    total_documents_count: int
    ollama: str
    ollama_model: str
    ollama_available_models: List[str] = []
