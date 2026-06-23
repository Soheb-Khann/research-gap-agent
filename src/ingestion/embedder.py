# src/ingestion/embedder.py

from pathlib import Path
from typing import List
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "chroma_db"

# This model downloads once (~90MB), then runs fully offline
# all-MiniLM-L6-v2 is the sweet spot: fast, small, good quality
MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_or_create_collection(client, collection_name: str = "research_papers"):
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

def embed_and_store(chunks: List[dict], collection_name: str = "research_papers"):
    """
    Embeds chunks locally using sentence-transformers
    and stores them in ChromaDB.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    texts = [c["text"] for c in chunks]
    ids = [str(c["chunk_id"]) for c in chunks]
    metadatas = [
        {
            "source": c.get("source", "unknown"),
            "page":   str(c.get("page", 0)),
            "chunk_id": str(c["chunk_id"])
        }
        for c in chunks
    ]

    print(f"[embedder] Embedding {len(texts)} chunks locally...")
    embeddings = MODEL.encode(texts, show_progress_bar=True).tolist()

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"[embedder] Stored {len(texts)} chunks in ChromaDB at '{CHROMA_PATH}'")
    return collection

def retrieve_by_source(
    source: str,
    query: str = "methodology findings results limitations",
    collection_name: str = "research_papers",
    n_results: int = 30
) -> List[dict]:
    """
    Retrieves chunks filtered to a specific source PDF.
    Uses ChromaDB's where clause to filter by metadata before semantic search.

    Args:
        source:    The filename e.g. 'retrieval_augmented_generation.pdf'
        query:     Semantic query to rank the filtered chunks
        n_results: Max chunks to return
    """
    client     = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    query_embedding = MODEL.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"source": source},          # ← this is the key fix
        include=["documents", "metadatas", "distances"]
    )

    # ChromaDB returns empty lists if no results, not an error
    if not results["documents"] or not results["documents"][0]:
        print(f"[embedder] No chunks found for source='{source}'")
        return []

    retrieved = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        retrieved.append({
            "text":             doc,
            "source":           meta.get("source"),
            "page":             meta.get("page"),
            "similarity_score": round(1 - dist, 4)
        })

    return retrieved


def list_sources(collection_name: str = "research_papers") -> List[str]:
    """
    Returns all unique source filenames currently stored in ChromaDB.
    Useful for the summariser to know which papers are available.
    """
    client     = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    # Get all metadata (no query needed)
    results = collection.get(include=["metadatas"])
    sources = list({m["source"] for m in results["metadatas"] if m.get("source")})
    return sorted(sources)

def retrieve(query: str, collection_name: str = "research_papers", n_results: int = 5) -> List[dict]:
    """
    Embeds a query locally and retrieves the top-n most similar chunks.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    query_embedding = MODEL.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    retrieved = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        retrieved.append({
            "text":             doc,
            "source":           meta.get("source"),
            "page":             meta.get("page"),
            "similarity_score": round(1 - dist, 4)
        })

    return retrieved

def reset_collection(collection_name: str = "research_papers"):
    """Deletes and recreates the collection. Use in tests to ensure clean state."""
    client = get_chroma_client()
    try:
        client.delete_collection(collection_name)
        print(f"[embedder] Deleted collection '{collection_name}'")
    except Exception:
        pass  # collection didn't exist yet, that's fine
    return get_or_create_collection(client, collection_name)