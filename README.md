# AI PDF Summarizer & RAG Q&A

A production-grade, local Retrieval-Augmented Generation (RAG) and document summarization application for PDF manuals. Built with **FastAPI**, **PyMuPDF**, **SentenceTransformers**, **FAISS**, **Ollama (Local LLM)**, and **React + Vite**.

![Architecture Diagram](docs/architecture_diagram.png)

---

## Key Features

- **Robust PDF Ingestion**: Page-by-page extraction using PyMuPDF, preserving page numbers, detecting non-text pages, calculating document hashes (SHA256) for deduplication, and storing metadata in SQLite.
- **Asynchronous Background Processing**: PDF uploads return `202 Accepted` immediately with status progression (`uploaded` → `extracting` → `chunking` → `embedding` → `indexing` → `ready`).
- **Semantic Text Chunking**: Paragraph and sentence boundary-aware text splitter preserving chunk metadata (`document_id`, `filename`, `page_number`, `start_char`, `end_char`, `text`).
- **Vector Search Persistence**: L2-normalized embeddings via `BAAI/bge-small-en-v1.5` sentence-transformers and persistent **FAISS** index with full rebuild capability on document deletion.
- **Local LLM via Ollama**: Connects to local Ollama instance (`llama3.2` or configurable model). Gracefully detects server and model availability.
- **Grounded RAG Q&A & Source Citations**: Zero hallucination design. Source citations (`filename`, `page_number`, `score`, `snippet`) are constructed directly from retrieval metadata, never parsed from arbitrary LLM text.
- **Map-Reduce Summarization**: Batched summarization for large PDF manuals (Map phase for page batches, Reduce phase for consolidation into Overview, Key Points, Procedures, Safety Warnings, and Conclusion).
- **Conversation Memory**: Sliding-window session memory for multi-turn Q&A context ("What is the warranty?" → "What does it cover?").
- **Modern Glassmorphism UI**: Tabbed React UI (Chat Q&A, Map-Reduce Summaries, Document Registry) with real-time status indicators and document scope filters.
- **Comprehensive Offline Test Suite**: 42+ unit and integration tests using mocked embedding and LLM models.

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js v18+ & npm
- [Ollama](https://ollama.com/) (Optional for vector retrieval & offline testing, required for local LLM generation)

### 2. Environment Setup
Copy the environment template:
```bash
cp .env.example .env
```

Default configuration in `.env`:
```env
APP_ENV=development
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=5
MAX_FILE_SIZE_MB=50
```

---

### 3. Backend Setup & Startup

Install Python dependencies:
```bash
pip install -r backend/requirements.txt
```

Run tests to verify installation:
```bash
python -m pytest backend/tests/ -v
```

Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

---

### 4. Ollama LLM Setup

Start the Ollama daemon:
```bash
ollama serve
```

Pull the target model (in another terminal):
```bash
ollama pull llama3.2
```

---

### 5. Frontend Startup

Install dependencies & launch Vite dev server:
```bash
cd frontend
npm install
npm run dev
```

Open browser at `http://localhost:5173`.

---

## System Architecture

```
                       ┌────────────────────────┐
                       │     React + Vite UI    │
                       │   (Chat, Summary, Reg) │
                       └───────────┬────────────┘
                                   │ REST API
                                   ▼
                       ┌────────────────────────┐
                       │    FastAPI Backend     │
                       └───────────┬────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  Document Service           RAG Service             Summary Service
 (PyMuPDF + SQLite)        (Context Builder)           (Map-Reduce)
         │                         │                         │
         ▼                         ▼                         ▼
  Chunking Service           Retriever Service       Local Ollama LLM
 (Paragraph Splitter)              │                 (llama3.2 / HTTP)
         │                         ▼                         │
         ▼                 Persistent FAISS                  ▼
 Embedding Service       (IndexFlatIP + Metadata)    Grounded Answer
 (BAAI/bge-small-en)                                 + Citations
```

---

## API Summary

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Check health of backend, FAISS index, and Ollama connectivity |
| `/api/documents/upload` | POST | Upload PDF for background extraction and indexing (returns 202) |
| `/api/documents` | GET | List all registered documents and processing statuses |
| `/api/documents/{id}` | GET | Get processing status for a single document |
| `/api/documents/{id}` | DELETE | Delete document metadata and remove vectors from FAISS |
| `/api/chat` | POST | Grounded Q&A over uploaded documents with citations |
| `/api/summary/{id}` | POST | Generate Map-Reduce summary (short, medium, detailed) |

---

## Running with Docker Compose

```bash
docker-compose up --build
```

---

## Testing & Quality Assurance

Run the test suite:
```bash
python -m pytest backend/tests/ -v
```

Tests include:
- `test_pdf.py`: PDF validation, magic bytes, multi-page extraction.
- `test_chunking.py`: Chunk size, overlap bounds, unique IDs, empty text.
- `test_embeddings.py`: Vector dimensions, L2 normalization, query embedding.
- `test_retrieval.py`: FAISS index creation, search, persistence, and deletion rebuild.
- `test_rag.py`: Grounded Q&A and explicit **Rule 27 No-Hallucination verification**.
- `test_api.py`: FastAPI endpoints and error handling.
