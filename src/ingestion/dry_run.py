# dry_run.py
"""
Dry run to manually verify the full ingestion pipeline on one or more PDFs.

Usage:
    # Single PDF
    python dry_run.py paper1.pdf

    # Multiple PDFs
    python dry_run.py paper1.pdf paper2.pdf paper3.pdf

    # Entire folder of PDFs
    python dry_run.py papers/
"""

import sys
from pathlib import Path

from src.ingestion.pdf_extractor import extract_text_from_pdf
from src.ingestion.text_cleaner  import clean_pages
from src.ingestion.chunker       import chunk_by_paragraphs


# ── Helpers ────────────────────────────────────────────────────────────────────

def separator(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

def ok(msg):   print(f"  ✓  {msg}")
def fail(msg): print(f"  ✗  {msg}")
def info(msg): print(f"     {msg}")


# ── Collect PDF paths from args ────────────────────────────────────────────────

def collect_pdfs(args) -> list:
    """
    Accept any mix of:
      - individual PDF files  →  paper1.pdf paper2.pdf
      - a folder              →  papers/
    Returns a flat list of Path objects.
    """
    pdfs = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            found = sorted(p.glob("*.pdf"))
            if not found:
                print(f"  ⚠  No PDFs found in folder: {p}")
            pdfs.extend(found)
        elif p.suffix.lower() == ".pdf":
            if p.exists():
                pdfs.append(p)
            else:
                print(f"  ⚠  File not found, skipping: {p}")
        else:
            print(f"  ⚠  Not a PDF, skipping: {p}")
    return pdfs


# ── Per-PDF pipeline ───────────────────────────────────────────────────────────

def run_single(pdf_path: Path) -> dict:
    """Run extract → clean → chunk on one PDF. Returns a result summary dict."""
    result = {
        "file":    pdf_path.name,
        "passed":  False,
        "pages":   0,
        "cleaned": 0,
        "chunks":  0,
        "error":   None,
    }

    try:
        # Stage 1 — Extract
        pages = extract_text_from_pdf(str(pdf_path))
        if not pages:
            result["error"] = "No pages extracted"
            return result
        result["pages"] = len(pages)

        # Stage 2 — Clean
        cleaned = clean_pages(pages)
        if not cleaned:
            result["error"] = "All pages empty after cleaning"
            return result
        result["cleaned"] = len(cleaned)

        chars_before = sum(len(p["text"]) for p in pages)
        chars_after  = sum(len(p["text"]) for p in cleaned)
        reduction    = 100 * (1 - chars_after / chars_before) if chars_before else 0

        # Stage 3 — Chunk
        chunks = chunk_by_paragraphs(cleaned, min_length=100, max_length=1500)
        if not chunks:
            result["error"] = "No chunks produced — try lowering min_length"
            return result
        result["chunks"] = len(chunks)

        # Stage 4 — Structure check
        required_keys = {"chunk_id", "text", "page", "source", "char_count"}
        for chunk in chunks:
            missing = required_keys - set(chunk.keys())
            if missing:
                result["error"] = f"Chunk missing keys: {missing}"
                return result

        lengths  = [c["char_count"] for c in chunks]
        too_long = [c for c in chunks if c["char_count"] > 1500]

        # Print per-file detail
        ok(f"Extracted  : {len(pages)} pages")
        ok(f"Cleaned    : {len(cleaned)} pages  ({reduction:.1f}% noise removed)")
        ok(f"Chunks     : {len(chunks)}  |  avg {sum(lengths)//len(lengths)} chars  |  min {min(lengths)}  |  max {max(lengths)}")

        if too_long:
            fail(f"{len(too_long)} chunks exceed max_length=1500")
        else:
            ok(f"All chunks within size limits")

        # Preview first chunk
        info(f"\n  First chunk preview:")
        info(f"  {'-'*45}")
        info(f"  {chunks[0]['text'][:300].replace(chr(10), ' ')}")
        info(f"  {'-'*45}")

        result["passed"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python dry_run.py paper1.pdf")
        print("  python dry_run.py paper1.pdf paper2.pdf paper3.pdf")
        print("  python dry_run.py papers/\n")
        sys.exit(1)

    pdfs = collect_pdfs(sys.argv[1:])

    if not pdfs:
        print("\n✗  No valid PDF files found.\n")
        sys.exit(1)

    print(f"\n  Found {len(pdfs)} PDF(s) to process.")

    results = []

    for i, pdf_path in enumerate(pdfs, start=1):
        separator(f"PDF {i}/{len(pdfs)}  —  {pdf_path.name}")
        result = run_single(pdf_path)
        results.append(result)

        if not result["passed"]:
            fail(f"FAILED  →  {result['error']}")

    # ── Final summary table ────────────────────────────────────────────────────
    separator("SUMMARY")

    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    col = 30
    print(f"\n  {'File':<{col}} {'Pages':>6}  {'Cleaned':>8}  {'Chunks':>7}  {'Status'}")
    print(f"  {'-'*col}  {'------':>6}  {'--------':>8}  {'-------':>7}  {'------'}")

    for r in results:
        status = "✓ passed" if r["passed"] else f"✗ {r['error']}"
        print(f"  {r['file']:<{col}} {r['pages']:>6}  {r['cleaned']:>8}  {r['chunks']:>7}  {status}")

    print(f"\n  {len(passed)}/{len(results)} PDFs passed.")

    if failed:
        print(f"  {len(failed)} failed:")
        for r in failed:
            print(f"    ✗  {r['file']}  →  {r['error']}")

    print()


if __name__ == "__main__":
    main()