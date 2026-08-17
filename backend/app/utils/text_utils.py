"""
Text cleaning utilities for PDF-extracted content.
"""
from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Normalise Unicode, remove control characters, fix ligatures, collapse
    whitespace — but preserve paragraph structure and meaningful punctuation.
    """
    if not text:
        return ""

    # 1. Unicode NFC normalisation
    text = unicodedata.normalize("NFC", text)

    # 2. Drop control characters except \n \r \t
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\r", "\t") or unicodedata.category(ch)[0] != "C"
    )

    # 3. Repair soft-hyphen line breaks  ("docu-\nment" → "document")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # 4. Collapse horizontal whitespace (spaces/tabs) to a single space per line
    text = re.sub(r"[ \t]+", " ", text)

    # 5. Max two consecutive newlines (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# Simple heuristic: common page-number patterns
_PAGE_NUM_RE = re.compile(
    r"^\s*(page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+|-\s*\d+\s*-)\s*$",
    re.IGNORECASE,
)


def is_likely_header_footer(line: str) -> bool:
    return bool(_PAGE_NUM_RE.match(line))
