# src/ingestion/pdf_extractor.py
from pathlib import Path
from typing import List, Dict, Tuple
import fitz  # pymupdf
import pymupdf4llm


def detect_columns(pdf_path: str, sample_pages: int = 3) -> str:
    
    try:
        doc        = fitz.open(pdf_path)
        total      = len(doc)
        # Skip first page (usually title/abstract - single column even in 2-col papers)
        start      = min(1, total - 1)
        end        = min(start + sample_pages, total)

        multi_votes  = 0
        single_votes = 0

        for page_idx in range(start, end):
            page       = doc[page_idx]
            page_width = page.rect.width
            mid        = page_width / 2

            blocks = page.get_text("blocks")

            text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

            if len(text_blocks) < 3:
                single_votes += 1
                continue

            # Get left edge (x0) of each block
            x0_values = [b[0] for b in text_blocks]

            left_blocks  = [x for x in x0_values if x < mid * 0.8]
            right_blocks = [x for x in x0_values if x > mid * 0.4]

            right_starts_past_centre = [x for x in x0_values if x > mid * 0.6]

            is_multi = (
                len(left_blocks)              >= 2 and
                len(right_starts_past_centre) >= 2 and
                # Right column blocks must start well into right half
                any(x > mid * 0.7 for x in x0_values)
            )

            if is_multi:
                multi_votes += 1
            else:
                single_votes += 1

        doc.close()
        return "multi-column" if multi_votes > single_votes else "single-column"

    except Exception:
        return "single-column"


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []
    doc   = fitz.open(str(path))

    for page_num, page in enumerate(doc, start=1):
        raw_text = page.get_text("text")
        pages.append({
            "page":   page_num,
            "text":   raw_text,
            "source": path.name,
        })

    doc.close()
    return pages


def extract_text_by_blocks(pdf_path: str) -> List[Dict]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_chunks = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        show_progress=False,
    )

    pages = []
    for chunk in page_chunks:
        pages.append({
            "page":   chunk.get("metadata", {}).get("page", 0) + 1,
            "text":   chunk.get("text", ""),
            "source": path.name,
        })
    return pages


def extract_pdf(pdf_path: str) -> Tuple[List[Dict], str]:
    layout = detect_columns(pdf_path)

    if layout == "multi-column":
        pages = extract_text_by_blocks(pdf_path)
    else:
        pages = extract_text_from_pdf(pdf_path)

    return pages, layout