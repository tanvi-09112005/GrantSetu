"""NGO document ingestion pipeline.

    parse (pdfplumber / PyPDF2 / Tesseract OCR / python-docx)
    → chunk (~350 tokens, ~60 overlap, section-aware)
    → embed (BGE-M3 via ``embed_texts``)
    → store (``ngo_documents`` + ``document_chunks``)

The pipeline updates ``ngo_documents.ingest_status`` through:
    pending → parsing → chunking → embedding → ready   (happy path)
    pending → parsing → … → failed                     (on error)

Usage::

    from app.services.ingestion import ingest_document
    result = ingest_document(document_id, file_bytes=raw_bytes)
    # {"status": "ready", "chunk_count": 42}
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

from app.core.config import settings
from app.db import pool

logger = logging.getLogger(__name__)

# Chunking parameters — must match config.py values.
_CHUNK_TOKENS = settings.chunk_tokens   # 350
_CHUNK_OVERLAP = settings.chunk_overlap  # 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough token count: words × 1.3 (covers sub-word tokenisation)."""
    return int(len(text.split()) * 1.3)


_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:\d+\.)+\s+"          # numbered: 1.  1.1  2.3.4
    r"|[A-Z][A-Z\s]{3,}$"    # ALL-CAPS lines (≥4 chars)
    r"|.+:\s*$"               # lines ending with colon
    r")",
    re.MULTILINE,
)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.isupper() and len(stripped) > 3:
        return True
    if stripped.endswith(":"):
        return True
    if re.match(r"^(\d+\.)+\s+", stripped):
        return True
    return False


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF, falling back through three strategies."""
    text = ""

    # 1. pdfplumber — best for structured PDFs with tables.
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:
        logger.warning("pdfplumber failed: %s", exc)

    if text.strip():
        return text

    # 2. PyPDF2 — lighter, handles some PDFs pdfplumber can't.
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as exc:
        logger.warning("PyPDF2 failed: %s", exc)

    if text.strip():
        return text

    # 3. OCR fallback for scanned documents.
    try:
        import pdfplumber
        import pytesseract

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                page_text = pytesseract.image_to_string(img)
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:
        logger.warning("Tesseract OCR fallback failed: %s", exc)

    return text


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from a .docx file."""
    import docx

    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs)


def _extract_text(file_bytes: bytes) -> str:
    """Auto-detect format and extract text."""
    if file_bytes[:5] == b"%PDF-":
        return _extract_pdf(file_bytes)

    # DOCX / XLSX / PPTX are all ZIP-based.
    if file_bytes[:2] == b"PK":
        try:
            return _extract_docx(file_bytes)
        except Exception:
            # Not a docx — might be a scanned PDF mis-detected.
            return _extract_pdf(file_bytes)

    # Image → OCR.
    try:
        from PIL import Image
        import pytesseract

        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)
    except Exception:
        pass

    # Last resort: treat as plain text.
    return file_bytes.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str) -> list[dict]:
    """Section-aware chunking.

    Returns a list of ``{"text": ..., "section_title": ...}`` dicts.
    Prefers to break at section boundaries; otherwise breaks at the token
    target with an overlap window.
    """
    lines = text.split("\n")
    chunks: list[dict] = []

    current_lines: list[str] = []
    current_tokens = 0
    current_section: str | None = None
    last_heading: str | None = None

    def _flush() -> None:
        nonlocal current_lines, current_tokens
        chunk_body = "\n".join(current_lines)
        if chunk_body.strip():
            chunks.append({
                "text": chunk_body,
                "section_title": current_section,
            })

        # Keep overlap lines for continuity.
        overlap_lines: list[str] = []
        overlap_tokens = 0
        for line in reversed(current_lines):
            lt = _estimate_tokens(line)
            if overlap_tokens + lt > _CHUNK_OVERLAP:
                break
            overlap_lines.insert(0, line)
            overlap_tokens += lt

        current_lines = overlap_lines
        current_tokens = overlap_tokens

    for line in lines:
        line_tokens = _estimate_tokens(line)

        if _is_heading(line):
            # If we have accumulated enough content, flush before the heading.
            if current_tokens > _CHUNK_TOKENS // 2:
                _flush()
                current_section = line.strip()
            last_heading = line.strip()
            if current_section is None:
                current_section = last_heading

        current_lines.append(line)
        current_tokens += line_tokens

        if current_tokens >= _CHUNK_TOKENS:
            _flush()
            current_section = last_heading

    # Flush remainder.
    if current_lines and current_tokens > 0:
        chunk_body = "\n".join(current_lines)
        if chunk_body.strip():
            chunks.append({
                "text": chunk_body,
                "section_title": current_section,
            })

    return chunks


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _set_status(
    doc_id: str,
    status: str,
    *,
    error: str | None = None,
    raw_text: str | None = None,
) -> None:
    if raw_text is not None:
        pool.execute(
            "update ngo_documents "
            "set ingest_status = %s, ingest_error = %s, raw_text = %s "
            "where id = %s",
            (status, error, raw_text, doc_id),
        )
    else:
        pool.execute(
            "update ngo_documents "
            "set ingest_status = %s, ingest_error = %s "
            "where id = %s",
            (status, error, doc_id),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_document(
    document_id: str,
    *,
    file_path: str | None = None,
    file_bytes: bytes | None = None,
) -> dict:
    """Run the full ingestion pipeline for one document.

    Either *file_path* or *file_bytes* must be provided.

    Returns ``{"status": "ready"|"failed", "chunk_count": int, "error"?: str}``.
    """
    try:
        # -- 1. Load bytes ---------------------------------------------------
        _set_status(document_id, "parsing")

        doc_row = pool.fetch_one(
            "select id, ngo_id from ngo_documents where id = %s",
            (document_id,),
        )
        if not doc_row:
            return {"status": "failed", "error": "document not found", "chunk_count": 0}

        ngo_id = str(doc_row["ngo_id"])

        if file_bytes is None and file_path is not None:
            file_bytes = Path(file_path).read_bytes()

        if not file_bytes:
            raise ValueError("no file content provided")

        # -- 2. Extract text --------------------------------------------------
        text = _extract_text(file_bytes)
        if not text.strip():
            raise ValueError("could not extract any text from document")

        _set_status(document_id, "chunking", raw_text=text)

        # -- 3. Chunk ---------------------------------------------------------
        chunks = _chunk_text(text)
        logger.info(
            "document %s: %d chars → %d chunks", document_id, len(text), len(chunks)
        )

        # -- 4. Embed ---------------------------------------------------------
        _set_status(document_id, "embedding")

        from app.services.embeddings import embed_texts

        texts = [c["text"] for c in chunks]
        vectors = embed_texts(texts)

        # -- 5. Store chunks --------------------------------------------------
        for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            pool.execute(
                """
                insert into document_chunks
                    (document_id, ngo_id, chunk_text, chunk_index,
                     section_title, embedding)
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    document_id,
                    ngo_id,
                    chunk["text"],
                    i,
                    chunk.get("section_title"),
                    vector,
                ),
            )

        _set_status(document_id, "ready")
        return {"status": "ready", "chunk_count": len(chunks)}

    except Exception as exc:
        logger.exception("ingestion failed for document %s", document_id)
        _set_status(document_id, "failed", error=str(exc))
        return {"status": "failed", "error": str(exc), "chunk_count": 0}
