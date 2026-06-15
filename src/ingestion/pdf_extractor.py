# ingestion/pdf_extractor.py
from pathlib import Path
from typing import List, Dict
import pypdf


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract text from a PDF, page by page.

    Uses pypdf — pure Python, no C extensions, works on all Python versions
    including 3.13 free-threading builds.

    Returns:
        List of dicts: [{"page": 1, "text": "...", "source": "file.pdf"}, ...]

    Best for: single-column PDFs (theses, reports, books).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with open(str(path), "rb") as f:
        reader = pypdf.PdfReader(f)

        for page_num, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            pages.append({
                "page":   page_num,
                "text":   raw_text,
                "source": path.name,
            })

    return pages


def extract_text_by_blocks(pdf_path: str) -> List[Dict]:
    """
    Layout-oriented extractor for PDFs that may have multiple columns.

    pypdf can return text using a layout-preserving strategy.
    This often improves reading order in multi-column papers compared
    to the default extraction mode.

    Returns:
        List of dicts: [{"page": 1, "text": "...", "source": "file.pdf"}, ...]
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with open(str(path), "rb") as f:
        reader = pypdf.PdfReader(f)

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                # Prefer layout-preserving extraction for complex page layouts.
                text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                # Fallback to standard extraction if layout mode fails.
                text = page.extract_text() or ""

            pages.append({
                "page":   page_num,
                "text":   text,
                "source": path.name,
            })

    return pages