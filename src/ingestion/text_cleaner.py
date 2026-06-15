# ingestion/text_cleaner.py
import re
from typing import List, Dict


# ── Compiled regex patterns ────────────────────────────────────────────────────

# "meth-\nodology" → "methodology"  (hyphenated line breaks)
HYPHEN_LINEBREAK = re.compile(r"(\w+)-\n(\w+)")

# Two or more spaces/tabs → single space
MULTI_SPACE = re.compile(r"[ \t]{2,}")

# Standalone page numbers on their own line (e.g. "  42  ")
PAGE_NUMBER_LINE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)

# Common journal header/footer lines (DOI, ISSN, copyright, download notices)
HEADER_FOOTER = re.compile(
    r"^.{0,120}(doi:|www\.|©|\bISSN\b|All rights reserved|Downloaded from|"
    r"Published by|Received:|Accepted:|Correspondence:).*$",
    re.IGNORECASE | re.MULTILINE,
)

# Three or more consecutive newlines → paragraph break (2 newlines)
EXCESS_NEWLINES = re.compile(r"\n{3,}")


# ── Unicode / ligature fix map ─────────────────────────────────────────────────
# PDF extraction often preserves typographic ligatures and smart quotes
# as raw Unicode code points; map them back to ASCII equivalents.

LIGATURE_MAP = {
    "\ufb01": "fi",   # ﬁ
    "\ufb02": "fl",   # ﬂ
    "\ufb00": "ff",   # ﬀ
    "\ufb03": "ffi",  # ﬃ
    "\ufb04": "ffl",  # ﬄ
    "\u2019": "'",    # right single quotation mark
    "\u2018": "'",    # left single quotation mark
    "\u201c": '"',    # left double quotation mark
    "\u201d": '"',    # right double quotation mark
    "\u2013": "-",    # en dash
    "\u2014": "--",   # em dash
    "\u00ad": "",     # soft hyphen (invisible; safe to remove)
    "\u200b": "",     # zero-width space
}


# ── Individual cleaning functions ──────────────────────────────────────────────

def fix_ligatures(text: str) -> str:
    """Replace Unicode ligatures and typographic punctuation with ASCII."""
    for char, replacement in LIGATURE_MAP.items():
        text = text.replace(char, replacement)
    return text


def remove_headers_footers(text: str) -> str:
    """Strip standalone page numbers and common journal header/footer lines."""
    text = PAGE_NUMBER_LINE.sub("", text)
    text = HEADER_FOOTER.sub("", text)
    return text


def fix_hyphenation(text: str) -> str:
    """Rejoin words that were hyphenated across a line break."""
    return HYPHEN_LINEBREAK.sub(r"\1\2", text)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs; reduce 3+ newlines to a paragraph break."""
    text = MULTI_SPACE.sub(" ", text)
    text = EXCESS_NEWLINES.sub("\n\n", text)
    return text.strip()


# ── Master cleaning pipeline ───────────────────────────────────────────────────

def clean_text(raw_text: str) -> str:
    """
    Run all cleaning steps in order:
      1. fix_ligatures        — must be first, regex patterns assume ASCII
      2. remove_headers_footers
      3. fix_hyphenation
      4. normalize_whitespace — must be last, earlier steps introduce spaces
    """
    text = fix_ligatures(raw_text)
    text = remove_headers_footers(text)
    text = fix_hyphenation(text)
    text = normalize_whitespace(text)
    return text


def clean_pages(pages: List[Dict]) -> List[Dict]:
    """
    Apply clean_text() to every page dict produced by the extractor.
    Empty pages (nothing left after cleaning) are dropped.

    Args:
        pages: output of extract_text_from_pdf() or extract_text_by_blocks()

    Returns:
        Cleaned list of page dicts with the same structure.
    """
    cleaned = []
    for page in pages:
        cleaned_text = clean_text(page["text"])
        if cleaned_text:                          # drop blank pages
            cleaned.append({**page, "text": cleaned_text})
    return cleaned