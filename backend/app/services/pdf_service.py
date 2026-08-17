"""
PDF extraction service (PyMuPDF + RapidOCR Fallback).

Extracts text page-by-page. If a page contains no extractable text layer
(such as scanned documents or vector-outline text), it automatically renders
the page at 250 DPI and runs multi-stage OCR to extract the text while preserving
exact page numbers and source metadata.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pymupdf

from app.core.config import settings
from app.core.logging_config import logger
from app.services.ocr_service import ocr_service
from app.utils.text_utils import clean_text


def extract_pages(
    filename: str,
    content: bytes,
    document_id: str,
    progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Extract cleaned per-page text from a PDF byte stream with OCR fallback.

    Returns:
        {
            "document_id": str,
            "filename": str,
            "file_path": str,
            "total_pages": int,
            "pages_with_text": int,
            "pages_without_text": int,
            "pages_ocr_processed": int,
            "extraction_method": str,   # "native" | "ocr" | "none"
            "pages": [
                {
                    "page_number": int,   # 1-based
                    "has_text": bool,
                    "is_ocr": bool,
                    "text": str,
                }
            ]
        }
    """
    t0 = time.perf_counter()

    # Persist raw PDF
    safe_name = filename.replace(" ", "_")
    file_path = settings.upload_dir / f"{document_id}_{safe_name}"
    file_path.write_bytes(content)

    doc = pymupdf.open(stream=content, filetype="pdf")
    total_pages = len(doc)
    pages: List[Dict[str, Any]] = []
    pages_with_text = 0
    pages_without_text = 0
    pages_ocr_processed = 0

    for i in range(total_pages):
        page_num = i + 1
        page = doc.load_page(i)
        progress_pct = int(((i + 1) / max(total_pages, 1)) * 100)
        
        # 1. First attempt native text extraction
        raw_text = page.get_text("text") or ""
        clean = clean_text(raw_text)
        is_ocr = False

        # 2. Check if text is insufficient (< 15 chars or < 10 alphanumeric chars)
        alnum_chars = sum(1 for c in clean if c.isalnum())
        if len(clean) < 15 or alnum_chars < 10:
            if progress_callback:
                progress_callback(
                    page_num,
                    total_pages,
                    progress_pct,
                    f"OCR processing page {page_num}/{total_pages}...",
                )
            
            try:
                # 250 DPI rendering provides high fidelity for OCR
                pix = page.get_pixmap(dpi=250)
                ocr_raw = ocr_service.ocr_pixmap(pix)
                ocr_clean = clean_text(ocr_raw)
                if ocr_clean and len(ocr_clean) >= 15:
                    clean = ocr_clean
                    is_ocr = True
                    pages_ocr_processed += 1
            except Exception as e:
                logger.warning(f"[{document_id}] OCR error on page {page_num}: {e}")
        else:
            if progress_callback:
                progress_callback(
                    page_num,
                    total_pages,
                    progress_pct,
                    f"Extracting page {page_num}/{total_pages}...",
                )

        has_text = bool(clean)
        if has_text:
            pages_with_text += 1
        else:
            pages_without_text += 1

        pages.append(
            {
                "page_number": page_num,
                "has_text": has_text,
                "is_ocr": is_ocr,
                "text": clean,
            }
        )

    doc.close()
    elapsed = time.perf_counter() - t0

    if pages_ocr_processed > 0 and pages_ocr_processed >= (pages_with_text / 2):
        extraction_method = "ocr"
    elif pages_with_text > 0:
        extraction_method = "native"
    else:
        extraction_method = "none"

    logger.info(
        f"[{document_id}] Extracted {total_pages} pages from '{filename}' "
        f"({pages_with_text} with text, {pages_ocr_processed} via OCR, method={extraction_method}) in {elapsed:.2f}s"
    )

    return {
        "document_id": document_id,
        "filename": safe_name,
        "file_path": str(file_path),
        "total_pages": total_pages,
        "pages_with_text": pages_with_text,
        "pages_without_text": pages_without_text,
        "pages_ocr_processed": pages_ocr_processed,
        "extraction_method": extraction_method,
        "pages": pages,
    }
