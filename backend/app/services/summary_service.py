"""
Map-Reduce summarisation service for large PDFs.

Uses batched chunk summaries (map phase) then consolidates them (reduce phase).
Collects page texts directly from SQLite chunks repository or FAISS metadata side-car.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.core.logging_config import logger
from app.models.schemas import DocumentStatus, SummaryResponse
from app.prompts.rag_prompts import MAP_PROMPT_TEMPLATE, REDUCE_PROMPT_TEMPLATE
from app.repositories.document_repository import document_repo
from app.services.llm_service import llm_service
from app.services.vector_store_service import vector_store_service


class SummaryService:
    MAP_BATCH_PAGES = 4      # pages summarised per map call
    MAX_TEXT_PER_CALL = 4000 # chars fed to each LLM call

    async def summarise(self, document_id: str, summary_type: str) -> SummaryResponse:
        rec = document_repo.get(document_id)
        if rec is None:
            raise ValueError(f"Document '{document_id}' not found.")

        if rec.status == DocumentStatus.OCR_REQUIRED or rec.chunk_count == 0:
            raise ValueError(
                f"Document '{rec.filename}' contains 0 extractable chunks (status: {rec.status.value}). "
                "OCR processing is required before summarization."
            )

        # Collect page texts from SQLite chunks (primary source of truth)
        page_texts = self._collect_page_texts(document_id)

        if not page_texts:
            raise ValueError(f"Document '{rec.filename}' has no extractable text chunks available.")

        # ── Map phase ────────────────────────────────────────
        intermediates: List[str] = []
        for i in range(0, len(page_texts), self.MAP_BATCH_PAGES):
            batch = page_texts[i : i + self.MAP_BATCH_PAGES]
            combined = "\n\n".join(batch)[: self.MAX_TEXT_PER_CALL]
            prompt = MAP_PROMPT_TEMPLATE.format(text=combined)
            try:
                partial = await llm_service.generate(prompt, temperature=0.1)
                intermediates.append(partial)
            except Exception as exc:
                logger.warning(f"Map phase failed for batch {i}: {exc}")
                intermediates.append(combined[:400])

        # ── Reduce phase ─────────────────────────────────────
        combined_intermediates = "\n\n".join(intermediates)[: 6000]
        reduce_prompt = REDUCE_PROMPT_TEMPLATE.format(
            summary_type=summary_type,
            intermediates=combined_intermediates,
        )
        try:
            raw = await llm_service.generate(reduce_prompt, temperature=0.15)
        except Exception as exc:
            logger.warning(f"Reduce phase failed: {exc}")
            raw = "\n\n".join(intermediates)

        parsed = _parse_sections(raw)
        return SummaryResponse(
            document_id=document_id,
            filename=rec.filename,
            summary_type=summary_type,
            overview=parsed.get("overview", ""),
            key_points=parsed.get("key_points", []),
            important_procedures=parsed.get("important_procedures", []),
            warnings=parsed.get("warnings", []),
            conclusions=parsed.get("conclusions"),
            raw_summary=raw,
        )

    def _collect_page_texts(self, document_id: str) -> List[str]:
        """
        Reconstruct per-page text from SQLite chunks or vector store metadata.
        Pages are returned in order.
        """
        # Primary: query SQLite chunks
        db_chunks = document_repo.get_chunks(document_id)
        if db_chunks:
            pages: Dict[int, str] = {}
            for c in db_chunks:
                pn = c["page_number"]
                pages[pn] = pages.get(pn, "") + " " + c["text"]
            return [pages[k].strip() for k in sorted(pages)]

        # Fallback: query vector store metadata
        meta = vector_store_service._meta
        pages = {}
        for m in meta:
            if m.get("document_id") != document_id:
                continue
            pn = m.get("page_number", 1)
            pages[pn] = pages.get(pn, "") + " " + m.get("text", "")
        return [pages[k].strip() for k in sorted(pages)]


# ── helpers ────────────────────────────────────────────────────

def _parse_sections(text: str) -> Dict[str, Any]:
    def _between(header: str) -> str:
        m = re.search(
            rf"##\s*{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        return m.group(1).strip() if m else ""

    def _bullets(block: str) -> List[str]:
        return [
            ln.lstrip("-*•").strip()
            for ln in block.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

    return {
        "overview": _between("OVERVIEW"),
        "key_points": _bullets(_between("KEY POINTS")),
        "important_procedures": _bullets(_between("IMPORTANT PROCEDURES")),
        "warnings": _bullets(_between("WARNINGS AND SAFETY")),
        "conclusions": _between("CONCLUSION") or None,
    }


# ── singleton ─────────────────────────────────────────────────
summary_service = SummaryService()
