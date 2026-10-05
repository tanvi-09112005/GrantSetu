"""Darpan certificate verification.

Replaces the old "does the string the user typed appear in the PDF text?" check:

  1. read the PDF text layer (pdfplumber, then pypdf)
  2. REGEX-extract every Darpan ID printed on the certificate
  3. no ID found (scan, stylised font, blank)?  ->  Gemini Vision reads it
  4. compare the extracted ID - and the NGO name - with what the user entered

The expected ID is never sent to Gemini, so it can't be nudged into agreeing.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 2-letter state / 4-digit year / 7 digits, tolerant of spaces around the slashes.
DARPAN_FIND_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2})\s*/\s*(\d{4})\s*/\s*(\d{7})(?!\d)")
MAX_PAGES = 5

_NAME_STOPWORDS = {
    "the", "of", "and", "for", "an", "ngo", "trust", "society", "foundation",
    "samiti", "sansthan", "india", "private", "pvt", "ltd", "limited",
}
NAME_MATCH_THRESHOLD = 0.6  # share of the typed name's words that must appear


@dataclass
class DarpanCheck:
    ok: bool
    reason: str  # matched | id_mismatch | no_id_found | name_mismatch | unreadable
    message: str  # safe to show the user
    found_id: str | None = None
    found_name: str | None = None
    method: str = "text"  # text | vision


def normalise_id(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").upper())


def find_darpan_ids(text: str | None) -> list[str]:
    """Every Darpan-shaped ID in ``text`` (upper-cased, de-duplicated, in order)."""
    seen: list[str] = []
    for m in DARPAN_FIND_RE.finditer((text or "").upper()):
        found = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        if found not in seen:
            seen.append(found)
    return seen


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def name_overlap(typed_name: str, haystack: str) -> float:
    """Share (0-1) of the typed name's meaningful words found in ``haystack``."""
    words = _words(typed_name)
    tokens = [w for w in words if w not in _NAME_STOPWORDS and len(w) >= 2] or words
    if not tokens:
        return 1.0
    present = set(_words(haystack))
    return sum(t in present for t in tokens) / len(tokens)


def _text_layer(pdf_bytes: bytes) -> str:
    """Embedded text only (no OCR). Empty string for scans."""
    text = ""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:MAX_PAGES]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed during Darpan check: %s", exc)
    if text.strip():
        return text
    try:
        try:
            from pypdf import PdfReader
        except ImportError:  # pragma: no cover
            from PyPDF2 import PdfReader
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages[:MAX_PAGES]:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as exc:  # noqa: BLE001
        logger.warning("pypdf failed during Darpan check: %s", exc)
    return text


def verify_darpan_certificate(pdf_bytes: bytes, typed_id: str, typed_name: str = "") -> DarpanCheck:
    typed = normalise_id(typed_id)
    text = _text_layer(pdf_bytes)
    ids = find_darpan_ids(text)
    method = "text"
    haystack = text
    found_name: str | None = None
    readable = bool(text.strip())

    if not ids:
        # Scanned / graphic / blank - let Gemini Vision have a go.
        from app.services.vision import read_darpan_certificate

        data = read_darpan_certificate(pdf_bytes)
        if data is not None:
            method = "vision"
            readable = True
            ids = find_darpan_ids(str(data.get("darpan_id") or ""))
            if data.get("is_darpan_certificate") is False:
                ids = []
            found_name = (str(data.get("entity_name") or "").strip()) or None
            haystack = found_name or ""

    if not ids:
        if not readable:
            return DarpanCheck(
                False, "unreadable",
                "We couldn't read this PDF. If it is a scan, upload a clearer copy "
                "(or try again in a minute).",
                method=method,
            )
        return DarpanCheck(
            False, "no_id_found",
            "We couldn't find a Darpan ID in this file. Upload your NGO Darpan "
            "enrolment certificate (the one that shows 'Unique Id').",
            method=method,
        )

    if typed not in ids:
        shown = ids[0]
        return DarpanCheck(
            False, "id_mismatch",
            f"The certificate shows Darpan ID {shown}, but you entered {typed or '(blank)'}. "
            "Correct the ID or upload the matching certificate.",
            found_id=shown, found_name=found_name, method=method,
        )

    # Name check (skipped only when vision couldn't read a name at all).
    skip_name = method == "vision" and not found_name
    if typed_name and not skip_name and name_overlap(typed_name, haystack) < NAME_MATCH_THRESHOLD:
        return DarpanCheck(
            False, "name_mismatch",
            f"The Darpan ID matches, but the NGO name on the certificate doesn't match "
            f"\"{typed_name}\". Enter the name exactly as it appears on the certificate.",
            found_id=typed, found_name=found_name, method=method,
        )

    return DarpanCheck(
        True, "matched", "Darpan ID and NGO name match the certificate.",
        found_id=typed, found_name=found_name, method=method,
    )
