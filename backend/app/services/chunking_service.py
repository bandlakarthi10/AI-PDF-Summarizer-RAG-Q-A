"""
Paragraph-aware text chunker.

Splits text at paragraph boundaries first, then sentence boundaries,
then word boundaries.  Every chunk carries its source metadata so
citations can be constructed purely from retrieval data.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging_config import logger


class ChunkingService:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    # ── public API ────────────────────────────────────────────

    def chunk_document(
        self, extraction: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Accept the dict returned by ``pdf_service.extract_pages`` and return
        a flat list of chunk records.
        """
        document_id = extraction["document_id"]
        filename = extraction["filename"]
        all_chunks: List[Dict[str, Any]] = []

        for page in extraction.get("pages", []):
            if not page["has_text"] or not page["text"]:
                continue
            page_chunks = self._split(
                text=page["text"],
                document_id=document_id,
                filename=filename,
                page_number=page["page_number"],
            )
            all_chunks.extend(page_chunks)

        logger.info(
            f"[{document_id}] Chunked '{filename}' -> {len(all_chunks)} chunks"
        )
        return all_chunks

    # ── internals ─────────────────────────────────────────────

    def _split(
        self,
        text: str,
        document_id: str,
        filename: str,
        page_number: int,
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        length = len(text)
        start = 0

        while start < length:
            end = min(start + self.chunk_size, length)

            # Try to break at a natural boundary near the end of the window
            if end < length:
                search_from = max(start, end - self.chunk_size // 4)
                # 1. Paragraph break
                para = text.rfind("\n\n", search_from, end)
                if para > start:
                    end = para + 2
                else:
                    # 2. Sentence boundary
                    m = re.search(r"[.!?]\s", text[search_from:end])
                    if m:
                        end = search_from + m.end()
                    else:
                        # 3. Word boundary
                        space = text.rfind(" ", search_from, end)
                        if space > start:
                            end = space + 1

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    {
                        "chunk_id": f"chk_{uuid.uuid4().hex[:12]}",
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page_number,
                        "start_char": start,
                        "end_char": end,
                        "text": chunk_text,
                    }
                )

            if end >= length:
                break
            start = max(start + 1, end - self.chunk_overlap)

        return chunks


# ── singleton ─────────────────────────────────────────────────
chunking_service = ChunkingService()
