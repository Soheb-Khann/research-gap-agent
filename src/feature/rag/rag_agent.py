from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from src.ingestion.embedder import retrieve
from src.feature.rag.prompts import RAG_SYSTEM_PROMPT, build_rag_prompt

load_dotenv()

# ── Core RAG function — this is what the orchestrator nodes will call ─────────
def run_rag(question: str, n_results: int = 5) -> dict:
    """
    Retrieves relevant chunks from ChromaDB and generates an LLM answer.

    Args:
        question:  Natural language query about the ingested research papers.
        n_results: Number of chunks to retrieve (default 5).

    Returns:
        {
            "question":         str,
            "retrieved_chunks": list[dict],   # text, source, page, similarity_score
            "answer":           str,
            "sources":          list[str]      # unique source filenames
        }
    """
    # Step 1: Retrieve
    chunks = retrieve(
        query=question,
        collection_name="research_papers",
        n_results=n_results
    )
    unique_sources = list({c["source"] for c in chunks})
    print(f"[run_rag] Retrieved {len(chunks)} chunks from: {unique_sources}")

    # Step 2: Generate
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    prompt = build_rag_prompt(question, chunks)

    response = llm.invoke([
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    print(f"[run_rag] Answer generated ({len(response.content)} chars)")

    return {
        "question":         question,
        "retrieved_chunks": chunks,
        "answer":           response.content,
        "sources":          unique_sources
    }


# ── Quick manual test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_rag("What are the main research gaps in these papers?")
    print("\nANSWER:\n", result["answer"])
    print("\nSOURCES:", result["sources"])