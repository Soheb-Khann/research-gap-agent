# ingestion/chunker.py
import re
from typing import List, Dict


# ── Sentence boundary splitter ─────────────────────────────────────────────────
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _split_at_sentences(text: str, max_length: int) -> List[str]:
    """
    Break a paragraph that exceeds max_length into sub-chunks at sentence
    boundaries. If a single sentence is itself longer than max_length it is
    kept whole (hard split avoided to preserve meaning).
    """
    sentences = SENTENCE_END.split(text)
    result: List[str] = []
    current = ""

    for sentence in sentences:
        candidate = (current + " " + sentence).strip()
        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                result.append(current)
            current = sentence

    if current:
        result.append(current)

    return result


# ── Chunking strategies ────────────────────────────────────────────────────────
# chunk_by_para is the default but if the function is not able to clearly identify para then it falls back on chunk_by_overlap which uses window slide
def chunk_by_paragraphs(
    pages: List[Dict],
    min_length: int = 100,
    max_length: int = 1500,
) -> List[Dict]:
    """
    Split cleaned pages into chunks at paragraph boundaries (blank lines).

    Why paragraphs?
        Academic text organises ideas at paragraph level. Cutting within a
        paragraph loses the argument; merging paragraphs blurs distinct ideas.
        Preferred strategy for well-structured PDFs.

    Args:
        pages:      Output of clean_pages().
        min_length: Paragraphs shorter than this are discarded (captions,
                    isolated headings, stray lines).
        max_length: Paragraphs longer than this are split at sentence
                    boundaries so no chunk is unmanageably large.

    Returns:
        List of chunk dicts with keys:
            chunk_id, text, page, source, char_count
    """
    chunks: List[Dict] = []
    chunk_id = 0

    for page in pages:
        paragraphs = page["text"].split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if len(para) < min_length:
                continue

            sub_chunks = (
                _split_at_sentences(para, max_length)
                if len(para) > max_length
                else [para]
            )

            for sub in sub_chunks:
                sub = sub.strip()
                if sub:
                    chunks.append({
                        "chunk_id":   chunk_id,
                        "text":       sub,
                        "page":       page["page"],
                        "source":     page["source"],
                        "char_count": len(sub),
                    })
                    chunk_id += 1

    return chunks


def chunk_with_overlap(
    pages: List[Dict],
    chunk_size: int = 512,
    overlap: int = 64,
) -> List[Dict]:
    """
    Fixed-size sliding-window chunking with overlap.

    Why overlap?
        A sentence that straddles a chunk boundary is fully present in at
        least one chunk, so no context is silently lost.

    When to use instead of chunk_by_paragraphs?
        - Scanned / OCR'd PDFs where paragraph breaks are unreliable.
        - Very dense text with few blank lines.
        - When downstream embedding model expects fixed-length input.

    Args:
        pages:      Output of clean_pages().
        chunk_size: Maximum characters per chunk.
        overlap:    Characters shared between consecutive chunks.

    Returns:
        List of chunk dicts with keys:
            chunk_id, text, source, char_start, char_end, char_count
    """
    if not pages:
        return []

    full_text = "\n\n".join(p["text"] for p in pages)
    source = pages[0]["source"]

    chunks: List[Dict] = []
    chunk_id = 0
    start = 0

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        chunk_text = full_text[start:end].strip()

        if chunk_text:
            chunks.append({
                "chunk_id":   chunk_id,
                "text":       chunk_text,
                "source":     source,
                "char_start": start,
                "char_end":   end,
                "char_count": len(chunk_text),
            })
            chunk_id += 1

        start += chunk_size - overlap

    return chunks