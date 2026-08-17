"""
OCR Service wrapper around RapidOCR (ONNX-runtime based) with multi-stage preprocessing.

Designed to handle:
- Standard scanned PDF documents.
- Low-contrast / faint vector-outline PDFs (e.g. jsPDF / Canva generated resumes).
- Multi-stage image enhancement: Raw -> Grayscale Autocontrast -> Adaptive Thresholding.
"""
from __future__ import annotations

import io
import time
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageOps, ImageFilter

from app.core.logging_config import logger


class OCRService:
    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            logger.info("Initializing RapidOCR engine...")
            t0 = time.perf_counter()
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            logger.info(f"RapidOCR engine initialized in {time.perf_counter()-t0:.2f}s")
        return self._engine

    def _eval_text_quality(self, text: str) -> bool:
        """
        Evaluate if OCR extracted meaningful content.
        Checks length and alphanumeric character density.
        """
        if not text:
            return False
        clean = text.strip()
        if len(clean) < 15:
            return False
        alnum_count = sum(1 for c in clean if c.isalnum())
        return alnum_count >= 10

    def ocr_pixmap(self, pixmap) -> str:
        """
        Run multi-stage OCR on a PyMuPDF Pixmap object.
        Stage 1: Direct OCR on pixmap bytes.
        Stage 2: Autocontrast enhancement on grayscale image (recovers faint vector-outline text).
        Stage 3: High-contrast thresholding fallback.
        """
        engine = self._get_engine()

        # Convert pixmap to PIL Image
        try:
            img_bytes = pixmap.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as exc:
            logger.warning(f"Failed to convert pixmap to PIL image: {exc}")
            return ""

        # ── Stage 1: Standard OCR ─────────────────────────────
        try:
            res_raw, _ = engine(np.array(pil_img))
            if res_raw:
                lines = [line[1] for line in res_raw if line and len(line) > 1 and line[1]]
                text1 = "\n".join(lines).strip()
                if self._eval_text_quality(text1):
                    return text1
        except Exception as exc:
            logger.debug(f"Stage 1 OCR error: {exc}")

        # ── Stage 2: Grayscale Autocontrast ───────────────────
        # Crucial for low-contrast PDFs (e.g. Resume.pdf where pixel values are 243-255)
        try:
            gray_img = pil_img.convert("L")
            auto_img = ImageOps.autocontrast(gray_img, cutoff=2)
            auto_np = np.array(auto_img)
            res_auto, _ = engine(auto_np)
            if res_auto:
                lines = [line[1] for line in res_auto if line and len(line) > 1 and line[1]]
                text2 = "\n".join(lines).strip()
                if self._eval_text_quality(text2):
                    logger.info(f"Stage 2 (Autocontrast) succeeded: extracted {len(text2)} chars")
                    return text2
        except Exception as exc:
            logger.debug(f"Stage 2 Autocontrast OCR error: {exc}")

        # ── Stage 3: Adaptive Binarization / Sharpening ───────
        try:
            sharp_img = auto_img.filter(ImageFilter.SHARPEN)
            # Simple thresholding
            arr = np.array(sharp_img)
            thresh = int(arr.mean() - 10) if arr.mean() > 50 else 128
            bin_arr = np.where(arr > thresh, 255, 0).astype(np.uint8)
            res_bin, _ = engine(bin_arr)
            if res_bin:
                lines = [line[1] for line in res_bin if line and len(line) > 1 and line[1]]
                text3 = "\n".join(lines).strip()
                if text3:
                    logger.info(f"Stage 3 (Binarization) extracted {len(text3)} chars")
                    return text3
        except Exception as exc:
            logger.debug(f"Stage 3 OCR error: {exc}")

        return ""


# ── singleton ─────────────────────────────────────────────────
ocr_service = OCRService()
