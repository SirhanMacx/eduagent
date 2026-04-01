"""File ingestion pipeline — extracts text, images, and URLs from teacher curriculum files.

Supported formats: PDF, DOCX, PPTX, TXT, MD, SMART Notebook (.notebook),
SMART Board (.xbk), ActivInspire (.flipchart), and ZIP archives.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Optional

from clawed.asset_registry import ExtractedImage, ExtractedURL, ExtractionResult, extract_urls, extract_youtube_ids
from clawed.models import DocType, Document

logger = logging.getLogger(__name__)

# ── File-type detection ──────────────────────────────────────────────────

EXTENSION_MAP: dict[str, DocType] = {
    ".pdf": DocType.PDF,
    ".docx": DocType.DOCX,
    ".pptx": DocType.PPTX,
    ".txt": DocType.TXT,
    ".md": DocType.MD,
    ".notebook": DocType.NOTEBOOK,
    ".xbk": DocType.XBK,
    ".flipchart": DocType.FLIPCHART,
    # Added for v2.3.7 — common legacy/teacher formats
    ".doc": DocType.DOCX,
    ".ppt": DocType.PPTX,
    ".xls": DocType.TXT,
    ".xlsx": DocType.TXT,
    ".csv": DocType.TXT,
    ".rtf": DocType.TXT,
    ".html": DocType.TXT,
    ".htm": DocType.TXT,
    ".odt": DocType.TXT,
    ".odp": DocType.TXT,
}

SUPPORTED_EXTENSIONS = set(EXTENSION_MAP.keys())


def _detect_type(path: Path) -> DocType:
    return EXTENSION_MAP.get(path.suffix.lower(), DocType.UNKNOWN)


# ── URL extraction helpers ───────────────────────────────────────────────

_YT_RE = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)'
    r'([a-zA-Z0-9_-]{11})'
)


def _extract_urls_from_text(text: str) -> list[ExtractedURL]:
    """Extract URLs from plain text, classifying YouTube vs other."""
    urls: list[ExtractedURL] = []
    seen: set[str] = set()
    for url in extract_urls(text):
        if url in seen:
            continue
        seen.add(url)
        yt_ids = extract_youtube_ids(url)
        if yt_ids:
            urls.append(ExtractedURL(
                url=f"https://youtube.com/watch?v={yt_ids[0]}",
                link_type="youtube",
            ))
        elif 'docs.google.com' in url or 'drive.google.com' in url:
            urls.append(ExtractedURL(url=url, link_type="google_doc"))
        else:
            urls.append(ExtractedURL(url=url, link_type="website"))
    return urls


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


def _extract_pdf_rich(path: Path) -> ExtractionResult:
    """Extract text, images, and URLs from a PDF."""
    import fitz

    doc = fitz.open(str(path))
    pages: list[str] = []
    images: list[ExtractedImage] = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        slide_context = ""
        if text.strip():
            pages.append(text)
            slide_context = text.strip()
        for img_info in page.get_images():
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image.get("image"):
                    img_bytes = base_image["image"]
                    ext = base_image.get("ext", "png")
                    if len(img_bytes) > 2000:  # Skip tiny icons
                        images.append(ExtractedImage(
                            image_bytes=img_bytes,
                            format=ext,
                            context_text=slide_context[:200] if slide_context else "",
                        ))
            except Exception as e:
                logger.debug("Failed to extract image xref %d: %s", xref, e)
    page_count = len(doc)
    doc.close()

    full_text = "\n\n".join(pages)
    urls = _extract_urls_from_text(full_text)

    return ExtractionResult(
        text=full_text,
        page_count=page_count,
        word_count=len(full_text.split()),
        urls=urls,
        images=images,
    )


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


def _extract_docx_rich(path: Path) -> ExtractionResult:
    """Extract text, images, and hyperlinks from a DOCX."""
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    paragraphs: list[str] = []
    urls: list[ExtractedURL] = []
    images: list[ExtractedImage] = []

    # Extract text
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)

    # Extract table text
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    full_text = "\n\n".join(paragraphs)

    # Extract hyperlinks from document XML
    try:
        rels = doc.part.rels
        for rel in rels.values():
            if "hyperlink" in rel.reltype:
                url = rel._target  # noqa: SLF001
                if url and isinstance(url, str) and url.startswith("http"):
                    yt_ids = extract_youtube_ids(url)
                    if yt_ids:
                        urls.append(ExtractedURL(
                            url=f"https://youtube.com/watch?v={yt_ids[0]}",
                            link_type="youtube",
                        ))
                    else:
                        urls.append(ExtractedURL(url=url, link_type="website"))
    except (AttributeError, KeyError, ValueError) as e:
        logger.warning("Failed to extract DOCX hyperlinks from %s: %s", path.name, e)

    # Also find URLs in plain text
    for text_url in _extract_urls_from_text(full_text):
        if not any(u.url == text_url.url for u in urls):
            urls.append(text_url)

    # Extract inline images
    try:
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                try:
                    img_part = rel.target_part
                    img_bytes = img_part.blob
                    ct = img_part.content_type or ""
                    fmt = "png" if "png" in ct else "jpeg"
                    if len(img_bytes) > 1000:  # skip tiny icons
                        images.append(ExtractedImage(
                            image_bytes=img_bytes,
                            format=fmt,
                            alt_text="",
                            context_text="",
                        ))
                except (AttributeError, OSError, ValueError) as e:
                    logger.debug("Failed to extract DOCX image: %s", e)
    except (AttributeError, KeyError) as e:
        logger.warning("Failed to enumerate DOCX image rels from %s: %s", path.name, e)

    return ExtractionResult(
        text=full_text,
        word_count=len(full_text.split()),
        urls=urls,
        images=images,
    )


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


def _extract_pptx_rich(path: Path) -> ExtractionResult:
    """Extract text, images, and hyperlinks from a PPTX."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(str(path))
    slides_text: list[str] = []
    urls: list[ExtractedURL] = []
    images: list[ExtractedImage] = []
    seen_urls: set[str] = set()

    for i, slide in enumerate(prs.slides, 1):
        parts: list[str] = [f"[Slide {i}]"]
        slide_context = ""

        for shape in slide.shapes:
            # Extract text
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        parts.append(text)
                        slide_context = text[:100] if not slide_context else slide_context

                    # Extract hyperlinks from runs
                    for run in paragraph.runs:
                        try:
                            if run.hyperlink and run.hyperlink.address:
                                url = run.hyperlink.address
                                if url not in seen_urls:
                                    seen_urls.add(url)
                                    yt_ids = extract_youtube_ids(url)
                                    if yt_ids:
                                        urls.append(ExtractedURL(
                                            url=f"https://youtube.com/watch?v={yt_ids[0]}",
                                            link_type="youtube",
                                            context_text=run.text[:100],
                                        ))
                                    else:
                                        urls.append(ExtractedURL(
                                            url=url,
                                            link_type="website",
                                            context_text=run.text[:100],
                                        ))
                        except (AttributeError, ValueError) as e:
                            logger.debug("Failed to extract PPTX hyperlink: %s", e)

            # Extract images
            try:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    img = shape.image
                    ct = img.content_type or ""
                    # Skip EMF/WMF (not reusable in new PPTX easily)
                    if 'emf' in ct.lower() or 'wmf' in ct.lower():
                        continue
                    fmt = "png" if "png" in ct else "jpeg"
                    img_bytes = img.blob
                    if len(img_bytes) > 2000:  # skip tiny icons/bullets
                        images.append(ExtractedImage(
                            image_bytes=img_bytes,
                            format=fmt,
                            width=shape.width,
                            height=shape.height,
                            context_text=slide_context,
                            slide_number=i,
                        ))
            except (AttributeError, OSError, ValueError) as e:
                logger.debug("Failed to extract PPTX image on slide %d: %s", i, e)

        if len(parts) > 1:
            slides_text.append("\n".join(parts))

    full_text = "\n\n".join(slides_text)

    # Also find URLs in plain text
    for text_url in _extract_urls_from_text(full_text):
        if text_url.url not in seen_urls:
            urls.append(text_url)

    return ExtractionResult(
        text=full_text,
        slide_count=len(prs.slides),
        word_count=len(full_text.split()),
        urls=urls,
        images=images,
    )


def _extract_text(path: Path) -> str:
    """Extract text from a plain text or Markdown file."""
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_notebook(path: Path) -> tuple[str, Optional[int]]:
    """Extract text from a SMART Notebook file via formats plugin."""
    from clawed.formats.notebook import extract_notebook

    return extract_notebook(path)


def _extract_xbk(path: Path) -> tuple[str, Optional[int]]:
    """Extract text from a SMART Board file via formats plugin."""
    from clawed.formats.xbk import extract_xbk

    return extract_xbk(path)


def _extract_flipchart(path: Path) -> tuple[str, Optional[int]]:
    """Extract text from an ActivInspire file via formats plugin."""
    from clawed.formats.flipchart import extract_flipchart

    return extract_flipchart(path)


# ── Legacy/additional format extractors (v2.3.7) ────────────────────────


def _extract_doc(path: Path) -> str:
    """Extract text from a legacy .doc file (binary Word format).

    Tries textutil (macOS), then catdoc/antiword, then raw text fallback.
    """
    # macOS built-in
    if shutil.which("textutil"):
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.warning("textutil failed on %s: %s", path.name, e)
    # catdoc fallback
    for tool in ("catdoc", "antiword"):
        if shutil.which(tool):
            try:
                result = subprocess.run(
                    [tool, str(path)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired) as e:
                logger.warning("%s failed on %s: %s", tool, path.name, e)
    # Raw text fallback (often garbled but better than nothing)
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        # Strip null bytes and control chars
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
        text = re.sub(r"\s{3,}", "\n", text).strip()
        if len(text) > 50:
            return text
    except OSError as e:
        logger.warning("Failed to read .doc raw bytes from %s: %s", path.name, e)
    return ""


def _extract_ppt(path: Path) -> str:
    """Extract text from a legacy .ppt file (binary PowerPoint format).

    Tries textutil (macOS), then raw text extraction.
    """
    if shutil.which("textutil"):
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.warning("textutil failed on %s: %s", path.name, e)
    # Raw text fallback
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
        text = re.sub(r"\s{3,}", "\n", text).strip()
        if len(text) > 50:
            return text
    except OSError as e:
        logger.warning("Failed to read .ppt raw bytes from %s: %s", path.name, e)
    return ""


def _extract_csv(path: Path) -> str:
    """Extract text from a CSV file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(content))
        rows = []
        for i, row in enumerate(reader):
            if i >= 5000:  # Cap at 5000 rows
                rows.append(f"... ({i} rows total, truncated)")
                break
            rows.append(" | ".join(row))
        return "\n".join(rows)
    except (OSError, csv.Error, ValueError) as e:
        logger.warning("Failed to extract CSV from %s: %s", path.name, e)
        return ""


def _extract_xlsx(path: Path) -> str:
    """Extract text from an .xlsx file using openpyxl."""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(path), read_only=True, data_only=True)
        rows: list[str] = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            rows.append(f"[Sheet: {sheet}]")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 5000:
                    rows.append("... (truncated at 5000 rows)")
                    break
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    rows.append(" | ".join(cells))
        wb.close()
        return "\n".join(rows)
    except ImportError:
        logger.debug("openpyxl not installed, cannot extract .xlsx: %s", path.name)
        return ""
    except Exception as exc:
        logger.debug("Failed to extract .xlsx %s: %s", path.name, exc)
        return ""


def _extract_xls(path: Path) -> str:
    """Extract text from a legacy .xls file. Tries reading as raw text."""
    # Try textutil on macOS
    if shutil.which("textutil"):
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.warning("textutil failed on %s: %s", path.name, e)
    return ""


def _extract_rtf(path: Path) -> str:
    """Extract text from an RTF file.

    Tries striprtf library first, then textutil (macOS), then regex fallback.
    """
    try:
        from striprtf.striprtf import rtf_to_text
        raw = path.read_text(encoding="utf-8", errors="replace")
        return rtf_to_text(raw).strip()
    except ImportError:
        pass
    except (OSError, ValueError) as e:
        logger.warning("striprtf failed on %s: %s", path.name, e)
    # macOS textutil
    if shutil.which("textutil"):
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.warning("textutil failed on RTF %s: %s", path.name, e)
    # Regex fallback: strip RTF control codes
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        # Remove RTF control words and braces
        text = re.sub(r"\\[a-z]+\d*\s?", " ", raw)
        text = re.sub(r"[{}]", "", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        if len(text) > 50:
            return text
    except OSError as e:
        logger.warning("Failed to read RTF file %s: %s", path.name, e)
    return ""


def _extract_html_file(path: Path) -> str:
    """Extract text from an HTML file by stripping tags."""
    try:
        from html.parser import HTMLParser

        class _TagStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style"):
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in ("script", "style"):
                    self._skip = False

            def handle_data(self, data):
                if not self._skip:
                    self.parts.append(data)

        raw = path.read_text(encoding="utf-8", errors="replace")
        stripper = _TagStripper()
        stripper.feed(raw)
        text = " ".join(stripper.parts)
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text
    except (OSError, ValueError) as e:
        logger.warning("Failed to extract HTML from %s: %s", path.name, e)
        return ""


def _extract_odt(path: Path) -> str:
    """Extract text from an OpenDocument Text (.odt) file.

    ODT is a ZIP containing content.xml. We extract text from XML tags.
    """
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            if "content.xml" not in zf.namelist():
                return ""
            content_xml = zf.read("content.xml").decode("utf-8", errors="replace")
            # Strip XML tags to get plain text
            text = re.sub(r"<[^>]+>", " ", content_xml)
            text = re.sub(r"\s{2,}", " ", text).strip()
            return text
    except Exception as exc:
        logger.debug("Failed to extract .odt %s: %s", path.name, exc)
        return ""


def _extract_odp(path: Path) -> str:
    """Extract text from an OpenDocument Presentation (.odp) file.

    ODP is a ZIP containing content.xml.
    """
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            if "content.xml" not in zf.namelist():
                return ""
            content_xml = zf.read("content.xml").decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", content_xml)
            text = re.sub(r"\s{2,}", " ", text).strip()
            return text
    except Exception as exc:
        logger.debug("Failed to extract .odp %s: %s", path.name, exc)
        return ""


# Extension-based extractors for new formats that need special handling
# (keyed by suffix, returns (text, page_count_or_None))
_EXTENSION_EXTRACTORS: dict[str, object] = {
    ".doc": lambda p: (_extract_doc(p), None),
    ".ppt": lambda p: (_extract_ppt(p), None),
    ".csv": lambda p: (_extract_csv(p), None),
    ".xlsx": lambda p: (_extract_xlsx(p), None),
    ".xls": lambda p: (_extract_xls(p), None),
    ".rtf": lambda p: (_extract_rtf(p), None),
    ".html": lambda p: (_extract_html_file(p), None),
    ".htm": lambda p: (_extract_html_file(p), None),
    ".odt": lambda p: (_extract_odt(p), None),
    ".odp": lambda p: (_extract_odp(p), None),
}


# ── Dispatch ─────────────────────────────────────────────────────────────

EXTRACTORS = {
    DocType.PDF: lambda p: _extract_pdf(p),
    DocType.DOCX: lambda p: (_extract_docx(p), None),
    DocType.PPTX: lambda p: (_extract_pptx(p), None),
    DocType.TXT: lambda p: (_extract_text(p), None),
    DocType.MD: lambda p: (_extract_text(p), None),
    DocType.NOTEBOOK: lambda p: _extract_notebook(p),
    DocType.XBK: lambda p: _extract_xbk(p),
    DocType.FLIPCHART: lambda p: _extract_flipchart(p),
}

# Rich extractors return ExtractionResult with images, URLs, metadata
RICH_EXTRACTORS = {
    DocType.PPTX: _extract_pptx_rich,
    DocType.DOCX: _extract_docx_rich,
    DocType.PDF: _extract_pdf_rich,
}


def _extract_single(path: Path) -> Optional[Document]:
    """Extract a single file into a Document, or None if unsupported/empty."""
    doc_type = _detect_type(path)
    if doc_type == DocType.UNKNOWN:
        logger.warning("Skipping unsupported format: %s", path.name)
        return None

    # Check extension-based extractors first (for legacy formats like .doc,
    # .ppt, .csv, etc. that map to a generic DocType but need special handling)
    ext_extractor = _EXTENSION_EXTRACTORS.get(path.suffix.lower())
    extractor = ext_extractor or EXTRACTORS.get(doc_type)
    if not extractor:
        logger.warning("No extractor for %s format: %s", doc_type.value, path.name)
        return None

    try:
        result = extractor(path)
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", path.name, exc)
        return None
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


def extract_rich(path: Path) -> Optional[ExtractionResult]:
    """Extract rich metadata (images, URLs, slide counts) from a file.

    Returns None if the file type doesn't support rich extraction or if
    extraction fails. The caller should fall back to _extract_single().
    """
    doc_type = _detect_type(path)
    extractor = RICH_EXTRACTORS.get(doc_type)
    if not extractor:
        return None
    try:
        return extractor(path)
    except Exception as exc:
        logger.debug("Rich extraction failed for %s: %s", path.name, exc)
        return None


# ── Format summary ──────────────────────────────────────────────────────


def _collect_files(path: Path) -> list[Path]:
    """Collect all supported files from a directory, sorted by modification
    time (newest first).

    Skips Office lock files (~$*) and macOS resource forks (._*).
    Sorting by mtime means the most recent materials come first, which is
    important when a cap is applied.
    """
    files = [
        f for f in path.rglob("*")
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
        and not f.name.startswith(("~$", "._"))
    ]
    # Sort newest first so caps keep the most recent materials
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def _format_summary(files: list[Path]) -> str:
    """Build a human-readable summary of found file types.

    Example: "Found 47 PDFs, 23 DOCX, 12 PPTX, 3 TXT — analyzing..."
    """
    counts: Counter[str] = Counter()
    for f in files:
        ext = f.suffix.lower().lstrip(".")
        counts[ext.upper()] += 1

    parts = [f"{count} {fmt}" for fmt, count in sorted(counts.items(), key=lambda x: -x[1])]
    return f"Found {', '.join(parts)} — analyzing..."


# ── Public API ───────────────────────────────────────────────────────────


def scan_directory(path: Path) -> tuple[list[Path], str]:
    """Scan a directory and return supported files with a format summary.

    Returns (file_list, summary_string).
    """
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    files = _collect_files(path)
    summary = _format_summary(files) if files else "No supported files found."
    return files, summary


def ingest_directory(
    path: Path,
    *,
    max_files: int = 0,
    progress_callback=None,
) -> list[Document]:
    """Recursively scan a directory and extract all supported documents.

    Args:
        path: Directory to scan.
        max_files: Maximum number of files to process (0 = unlimited).
            Files are already sorted newest-first by ``_collect_files``.
        progress_callback: Optional callable(current, total) for progress updates.
    """
    documents: list[Document] = []
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    files = _collect_files(path)
    if max_files > 0:
        files = files[:max_files]
    total = len(files)

    for i, file_path in enumerate(files):
        doc = _extract_single(file_path)
        if doc:
            documents.append(doc)
        if progress_callback:
            progress_callback(i + 1, total)

    return documents


MAX_UNZIP_SIZE = 500 * 1024 * 1024  # 500 MB


def ingest_zip(path: Path, *, progress_callback=None) -> list[Document]:
    """Extract a ZIP file to a temp directory, then ingest its contents."""
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ValueError(f"Not a ZIP file: {path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(str(path), "r") as zf:
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > MAX_UNZIP_SIZE:
                logger.warning(
                    "ZIP file too large when decompressed (%d bytes), skipping",
                    total_size,
                )
                return []
            zf.extractall(tmp_dir)
        return ingest_directory(Path(tmp_dir), progress_callback=progress_callback)


def ingest_path(
    path: Path,
    *,
    dry_run: bool = False,
    max_files: int = 0,
    progress_callback=None,
) -> list[Document]:
    """Smart ingestion: accepts a directory, ZIP file, or single file.

    Args:
        path: File or directory to ingest.
        dry_run: If True, scan and log what would be processed but don't extract.
        max_files: Maximum number of files to process (0 = unlimited).
        progress_callback: Optional callable(current, total) for progress updates.
    """
    path = Path(path).expanduser().resolve()

    if path.is_dir():
        if dry_run:
            files, summary = scan_directory(path)
            logger.info(summary)
            return _dry_run_results(files)
        return ingest_directory(
            path, max_files=max_files, progress_callback=progress_callback,
        )
    elif path.is_file() and path.suffix.lower() == ".zip":
        if dry_run:
            # For ZIP dry-run, list contents without extracting
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(str(path), "r") as zf:
                    total_size = sum(info.file_size for info in zf.infolist())
                    if total_size > MAX_UNZIP_SIZE:
                        logger.warning(
                            "ZIP file too large when decompressed (%d bytes), skipping",
                            total_size,
                        )
                        return []
                    zf.extractall(tmp_dir)
                files, summary = scan_directory(Path(tmp_dir))
                logger.info(summary)
                return _dry_run_results(files)
        return ingest_zip(path, progress_callback=progress_callback)
    elif path.is_file():
        if dry_run:
            return _dry_run_results([path])
        doc = _extract_single(path)
        return [doc] if doc else []
    else:
        raise FileNotFoundError(f"Path not found: {path}")


def _dry_run_results(files: list[Path]) -> list[Document]:
    """Create placeholder Documents for dry-run mode (no content extraction)."""
    results: list[Document] = []
    for f in files:
        doc_type = _detect_type(f)
        if doc_type != DocType.UNKNOWN:
            results.append(Document(
                title=f.stem.replace("_", " ").replace("-", " ").title(),
                content="[dry-run: content not extracted]",
                doc_type=doc_type,
                source_path=str(f),
            ))
    return results
