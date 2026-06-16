RAG_SYSTEM_PROMPT = """You are a research assistant analysing a set of academic papers.
Answer the user's question using ONLY the context chunks provided below.
Always cite the source paper and page number for every claim you make.
If the context does not contain enough information to answer, say so explicitly — do not guess or hallucinate."""

def build_rag_prompt(question: str, chunks: list[dict]) -> str:
    """
    Builds the user-facing prompt by injecting retrieved chunks as context.

    Args:
        question: The question to answer.
        chunks:   List of dicts with keys: text, source, page, similarity_score.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    if not chunks:
        return f"""No relevant context was retrieved from the papers.

Question: {question}

Answer: I was unable to find relevant information in the ingested papers to answer this question."""

    context_str = "\n\n".join([
        f"[Source: {c['source']} | Page: {c['page']} | Relevance: {c['similarity_score']}]\n{c['text']}"
        for c in chunks
    ])

    return f"""Context retrieved from research papers:

{context_str}

---
Question: {question}

Answer (cite source and page for every claim):"""