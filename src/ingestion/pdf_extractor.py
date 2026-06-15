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
    Word-level extractor that sorts text top-to-bottom, left-to-right.

    Useful for multi-column PDFs where default reading order interleaves
    the two columns. pypdf exposes word-level coordinates via
    page.extract_words(), which we sort by (y, x) position.

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
                words = page.extract_words()
                # Sort top-to-bottom (round y to 10px rows), then left-to-right
                words_sorted = sorted(
                    words,
                    key=lambda w: (round(float(w["y0"]) / 10), float(w["x0"]))
                )
                text = " ".join(w["text"] for w in words_sorted)
            except Exception:
                # Fallback to standard extraction if word-level fails
                text = page.extract_text() or ""

            pages.append({
                "page":   page_num,
                "text":   text,
                "source": path.name,
            })

    return pages