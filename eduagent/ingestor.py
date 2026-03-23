"""File ingestion pipeline — extracts text from PDFs, DOCX, PPTX, TXT, MD, and ZIP archives."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from eduagent.models import DocType, Document


# ── File-type detection ──────────────────────────────────────────────────

EXTENSION_MAP: dict[str, DocType] = {
    ".pdf": DocType.PDF,
    ".docx": DocType.DOCX,
    ".pptx": DocType.PPTX,
    ".txt": DocType.TXT,
    ".md": DocType.MD,
}

SUPPORTED_EXTENSIONS = set(EXTENSION_MAP.keys())


def _detect_type(path: Path) -> DocType:
    return EXTENSION_MAP.get(path.suffix.lower(), DocType.UNKNOWN)


# ── Individual extractors ────────────────────────────────────────────────


def _extract_pdf(path: Path) -> tuple[str, Optional[int]]:
    """Extract text from a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    pages: list[str] = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text)
    page_count = len(doc)
    doc.close()
    return "\n\n".join(pages), page_count


def _extract_docx(path: Path) -> str:
    """Extract text from a DOCX file."""
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))
    return "\n\n".join(paragraphs)


def _extract_pptx(path: Path) -> str:
    """Extract text from a PPTX file."""
    from pptx import Presentation

    prs = Presentation(str(path))
    slides_text: list[str] = []
    for i, slide in enumerate(prs.slides, 1):
        parts: list[str] = [f"[Slide {i}]"]
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        parts.append(text)
        if len(parts) > 1:  # More than just the slide marker
            slides_text.append("\n".join(parts))
    return "\n\n".join(slides_text)


def _extract_text(path: Path) -> str:
    """Extract text from a plain text or Markdown file."""
    return path.read_text(encoding="utf-8", errors="replace")


# ── Dispatch ─────────────────────────────────────────────────────────────

EXTRACTORS = {
    DocType.PDF: lambda p: _extract_pdf(p),
    DocType.DOCX: lambda p: (_extract_docx(p), None),
    DocType.PPTX: lambda p: (_extract_pptx(p), None),
    DocType.TXT: lambda p: (_extract_text(p), None),
    DocType.MD: lambda p: (_extract_text(p), None),
}


def _extract_single(path: Path) -> Optional[Document]:
    """Extract a single file into a Document, or None if unsupported/empty."""
    doc_type = _detect_type(path)
    if doc_type == DocType.UNKNOWN:
        return None

    extractor = EXTRACTORS[doc_type]
    result = extractor(path)
    if isinstance(result, tuple):
        content, page_count = result
    else:
        content, page_count = result, None

    if not content or not content.strip():
        return None

    return Document(
        title=path.stem.replace("_", " ").replace("-", " ").title(),
        content=content.strip(),
        doc_type=doc_type,
        source_path=str(path),
        page_count=page_count,
    )


# ── Public API ───────────────────────────────────────────────────────────


def ingest_directory(path: Path) -> list[Document]:
    """Recursively scan a directory and extract all supported documents."""
    documents: list[Document] = []
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            doc = _extract_single(file_path)
            if doc:
                documents.append(doc)
    return documents


def ingest_zip(path: Path) -> list[Document]:
    """Extract a ZIP file to a temp directory, then ingest its contents."""
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ValueError(f"Not a ZIP file: {path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(str(path), "r") as zf:
            zf.extractall(tmp_dir)
        return ingest_directory(Path(tmp_dir))


def ingest_path(path: Path) -> list[Document]:
    """Smart ingestion: accepts a directory, ZIP file, or single file."""
    path = Path(path).expanduser().resolve()

    if path.is_dir():
        return ingest_directory(path)
    elif path.is_file() and path.suffix.lower() == ".zip":
        return ingest_zip(path)
    elif path.is_file():
        doc = _extract_single(path)
        return [doc] if doc else []
    else:
        raise FileNotFoundError(f"Path not found: {path}")
