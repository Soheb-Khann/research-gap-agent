# src/ingestion/test_embedder.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.embedder import embed_and_store, retrieve, reset_collection

dummy_chunks = [
    {"chunk_id": 0, "text": "Transformer models use self-attention mechanisms to process sequences.", "source": "paper1.pdf", "page": 1},
    {"chunk_id": 1, "text": "BERT is a bidirectional transformer pretrained on masked language modelling.", "source": "paper1.pdf", "page": 2},
    {"chunk_id": 2, "text": "GPT uses unidirectional attention and is trained autoregressively.", "source": "paper2.pdf", "page": 1},
    {"chunk_id": 3, "text": "Few-shot learning allows models to generalise from very few examples.", "source": "paper2.pdf", "page": 3},
    {"chunk_id": 4, "text": "Limitations of current LLMs include hallucination and lack of grounding.", "source": "paper3.pdf", "page": 5},
]

def test_embed_and_retrieve():
    # ✅ always start clean
    reset_collection()

    embed_and_store(dummy_chunks)

    query = "What are the limitations of large language models?"
    results = retrieve(query, n_results=3)

    print(f"\nQuery: '{query}'")
    print(f"Top {len(results)} results:\n")
    for i, r in enumerate(results):
        print(f"  [{i+1}] score={r['similarity_score']} | source={r['source']} p{r['page']}")
        print(f"       {r['text'][:120]}")
        print()

    assert len(results) == 3
    assert results[0]["similarity_score"] > 0.37

    # Check the right chunk won
    top_text = results[0]["text"].lower()
    assert "limitation" in top_text or "hallucination" in top_text, \
        f"Wrong chunk ranked first: {results[0]['text'][:80]}"

    print("✅ test passed")

if __name__ == "__main__":
    test_embed_and_retrieve()