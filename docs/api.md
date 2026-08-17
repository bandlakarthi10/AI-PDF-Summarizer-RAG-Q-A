# REST API Reference

The FastAPI backend exposes OpenAPI documentation at `http://127.0.0.1:8000/docs`.

---

## Endpoints

### 1. Health Check
`GET /api/health`

**Response:**
```json
{
  "status": "ok",
  "embedding_model": "loaded",
  "embedding_model_name": "BAAI/bge-small-en-v1.5",
  "faiss": "ready",
  "faiss_total_vectors": 128,
  "ollama": "available",
  "ollama_model": "llama3.2",
  "ollama_available_models": ["llama3.2:latest"]
}
```

---

### 2. Document Upload
`POST /api/documents/upload`

**Form Data:**
- `file`: PDF file stream

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "'manual.pdf' accepted. Processing started in background.",
  "document_id": "doc_9f8a2c1b",
  "filename": "manual.pdf",
  "processing_status": "uploaded"
}
```

---

### 3. List Documents
`GET /api/documents`

**Response:**
```json
[
  {
    "document_id": "doc_9f8a2c1b",
    "filename": "manual.pdf",
    "total_pages": 42,
    "file_size_bytes": 1048576,
    "chunk_count": 56,
    "status": "ready",
    "error_message": null,
    "created_at": "2026-08-11T17:30:00Z"
  }
]
```

---

### 4. Delete Document
`DELETE /api/documents/{document_id}`

**Response:**
```json
{
  "status": "deleted",
  "document_id": "doc_9f8a2c1b"
}
```

---

### 5. Chat & Grounded RAG Q&A
`POST /api/chat`

**Request:**
```json
{
  "question": "What is the warranty period?",
  "document_ids": ["doc_9f8a2c1b"],
  "conversation_id": "conv_a1b2c3",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "According to manual.pdf (page 12), the warranty period is 2 years from purchase date.",
  "sources": [
    {
      "chunk_id": "chk_1a2b3c",
      "document_id": "doc_9f8a2c1b",
      "filename": "manual.pdf",
      "page_number": 12,
      "score": 0.892,
      "snippet": "The product includes a 2-year warranty covering manufacturing defects..."
    }
  ],
  "conversation_id": "conv_a1b2c3"
}
```

---

### 6. Map-Reduce Document Summarization
`POST /api/summary/{document_id}?summary_type=medium`

**Response:**
```json
{
  "document_id": "doc_9f8a2c1b",
  "filename": "manual.pdf",
  "summary_type": "medium",
  "overview": "This document is the operating manual for industrial machinery...",
  "key_points": ["24V DC operating voltage", "Monthly inspection required"],
  "important_procedures": ["Turn off main circuit breaker before servicing"],
  "warnings": ["Do not operate in wet conditions"],
  "conclusions": "Follow recommended maintenance schedule for optimal operation.",
  "raw_summary": "..."
}
```
