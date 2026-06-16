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