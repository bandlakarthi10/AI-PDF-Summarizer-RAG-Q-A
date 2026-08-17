"""
SQLite-backed document and chunk repository.

Persists document metadata and chunk records in backend/data/documents.db.
Survives backend restarts and allows instant zero-reprocessing FAISS index rebuilds.
"""
from __future__ import annotations

import sqlite3
import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.models.schemas import DocumentRecord, DocumentStatus


_DOCUMENTS_DDL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id        TEXT PRIMARY KEY,
    filename           TEXT NOT NULL,
    original_filename  TEXT NOT NULL,
    file_path          TEXT NOT NULL,
    file_size_bytes    INTEGER NOT NULL,
    file_hash          TEXT NOT NULL,
    total_pages        INTEGER NOT NULL DEFAULT 0,
    pages_with_text    INTEGER NOT NULL DEFAULT 0,
    pages_without_text INTEGER NOT NULL DEFAULT 0,
    chunk_count        INTEGER NOT NULL DEFAULT 0,
    extraction_method  TEXT NOT NULL DEFAULT 'pending',
    status             TEXT NOT NULL DEFAULT 'uploaded',
    current_page       INTEGER NOT NULL DEFAULT 0,
    progress_percent   INTEGER NOT NULL DEFAULT 0,
    error_message      TEXT,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
"""

_CHUNKS_DDL = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id           TEXT PRIMARY KEY,
    document_id        TEXT NOT NULL,
    filename           TEXT NOT NULL,
    page_number        INTEGER NOT NULL,
    start_char         INTEGER NOT NULL,
    end_char           INTEGER NOT NULL,
    text               TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);
"""


class DocumentRepository:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    # ── connection helper with foreign key enforcement ────────
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _row_to_record(self, row: sqlite3.Row) -> DocumentRecord:
        d = dict(row)
        d.setdefault("extraction_method", "pending")
        d.setdefault("current_page", 0)
        d.setdefault("progress_percent", 0)
        return DocumentRecord(**d)

    # ── initialization and column migration ───────────────────
    def _init_db(self):
        with self._conn() as conn:
            conn.execute(_DOCUMENTS_DDL)
            conn.execute(_CHUNKS_DDL)

            # Auto-migrate new columns into existing documents table if needed
            existing_cols = {
                r["name"] for r in conn.execute("PRAGMA table_info(documents)").fetchall()
            }
            if "extraction_method" not in existing_cols:
                conn.execute("ALTER TABLE documents ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'pending'")
            if "current_page" not in existing_cols:
                conn.execute("ALTER TABLE documents ADD COLUMN current_page INTEGER NOT NULL DEFAULT 0")
            if "progress_percent" not in existing_cols:
                conn.execute("ALTER TABLE documents ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")

        logger.info(f"Document repository initialized at {self.db_path} (foreign_keys ON)")

    # ── document CRUD ─────────────────────────────────────────
    def create(self, record: DocumentRecord) -> DocumentRecord:
        data = record.model_dump(mode="json")
        data.setdefault("extraction_method", "pending")
        data.setdefault("current_page", 0)
        data.setdefault("progress_percent", 0)
        data.setdefault("error_message", None)
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO documents (
                    document_id, filename, original_filename, file_path,
                    file_size_bytes, file_hash, total_pages, pages_with_text,
                    pages_without_text, chunk_count, extraction_method, status,
                    current_page, progress_percent, error_message,
                    created_at, updated_at
                ) VALUES (
                    :document_id, :filename, :original_filename, :file_path,
                    :file_size_bytes, :file_hash, :total_pages, :pages_with_text,
                    :pages_without_text, :chunk_count, :extraction_method, :status,
                    :current_page, :progress_percent, :error_message,
                    :created_at, :updated_at
                )""",
                data,
            )
        return record

    def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
        error_message: str | None = None,
    ):
        with self._conn() as conn:
            conn.execute(
                """UPDATE documents
                   SET status=?, error_message=?, updated_at=?
                   WHERE document_id=?""",
                (status.value, error_message, self._now(), document_id),
            )

    def update_progress(
        self,
        document_id: str,
        *,
        current_page: int,
        total_pages: int,
        progress_percent: int,
        status: DocumentStatus = DocumentStatus.OCR_PROCESSING,
        error_message: str | None = None,
    ):
        with self._conn() as conn:
            conn.execute(
                """UPDATE documents
                   SET current_page=?, total_pages=?, progress_percent=?,
                       status=?, error_message=?, updated_at=?
                   WHERE document_id=?""",
                (
                    current_page,
                    total_pages,
                    progress_percent,
                    status.value,
                    error_message,
                    self._now(),
                    document_id,
                ),
            )

    def update_stats(
        self,
        document_id: str,
        *,
        total_pages: int,
        pages_with_text: int,
        pages_without_text: int,
        chunk_count: int,
        extraction_method: str,
        status: DocumentStatus,
        error_message: str | None = None,
    ):
        with self._conn() as conn:
            conn.execute(
                """UPDATE documents
                   SET total_pages=?, pages_with_text=?, pages_without_text=?,
                       chunk_count=?, extraction_method=?, status=?,
                       current_page=?, progress_percent=100,
                       error_message=?, updated_at=?
                   WHERE document_id=?""",
                (
                    total_pages,
                    pages_with_text,
                    pages_without_text,
                    chunk_count,
                    extraction_method,
                    status.value,
                    total_pages,
                    error_message,
                    self._now(),
                    document_id,
                ),
            )

    def get(self, document_id: str) -> Optional[DocumentRecord]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id=?", (document_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_hash(self, file_hash: str) -> Optional[DocumentRecord]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE file_hash=?", (file_hash,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_all(self) -> List[DocumentRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def delete(self, document_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            cur = conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
        return cur.rowcount > 0

    # ── chunk operations ──────────────────────────────────────
    def save_chunks(self, document_id: str, chunks: List[Dict[str, Any]]):
        now = self._now()
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            for c in chunks:
                conn.execute(
                    """INSERT OR REPLACE INTO chunks (
                        chunk_id, document_id, filename, page_number,
                        start_char, end_char, text, created_at
                    ) VALUES (
                        :chunk_id, :document_id, :filename, :page_number,
                        :start_char, :end_char, :text, :created_at
                    )""",
                    {
                        "chunk_id": c.get("chunk_id", ""),
                        "document_id": document_id,
                        "filename": c.get("filename", ""),
                        "page_number": c.get("page_number", 1),
                        "start_char": c.get("start_char", 0),
                        "end_char": c.get("end_char", 0),
                        "text": c.get("text", ""),
                        "created_at": now,
                    },
                )

    def get_chunks(self, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            if document_id:
                rows = conn.execute(
                    "SELECT * FROM chunks WHERE document_id=? ORDER BY page_number, start_char",
                    (document_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM chunks ORDER BY document_id, page_number, start_char"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_total_chunk_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
            return int(row["count"]) if row else 0

    def get_ready_documents_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE status='ready'"
            ).fetchone()
            return int(row["count"]) if row else 0

    def get_total_documents_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
            return int(row["count"]) if row else 0


# ── singleton ─────────────────────────────────────────────────
document_repo = DocumentRepository()
