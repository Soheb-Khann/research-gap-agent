import json
from pathlib import Path
from src.feature.cross_paper.cross_paper_agent import run_cross_paper_agent

# Load real summaries from your existing outputs if available
SUMMARIES_DIR = Path("src/feature/summariser/outputs/test_summaries")


def load_test_summaries() -> list[dict]:
    """Load whatever JSON summaries exist in outputs/test_summaries."""
    summaries = []
    if SUMMARIES_DIR.exists():
        for f in sorted(SUMMARIES_DIR.glob("*.json")):
            with open(f) as fp:
                summaries.append(json.load(fp))
            print(f"  Loaded: {f.name}")
    return summaries


# Fallback mock data matching your summariser's exact output schema
MOCK_SUMMARIES = [
    {
        "paper_id": "agentic_rag_survey",
        "title": "Agentic Retrieval Augmented Generation: A Survey",
        "methodology": "Systematic literature review of agentic RAG frameworks",
        "findings": [
            "Agentic RAG outperforms naive RAG on multi-hop queries",
            "Tool use is a key differentiator in agentic systems"
        ],
        "claims": [
            "Agentic RAG represents the next evolution of retrieval systems",
            "Static RAG pipelines are insufficient for complex reasoning tasks"
        ],
        "limitations": [
            "Most benchmarks are on closed-domain QA only",
            "Latency overhead of multi-agent systems not well studied"
        ]
    },
    {
        "paper_id": "tearag_framework",
        "title": "TeaRAG: A Token-Efficient Agentic RAG Framework",
        "methodology": "Proposed token efficiency metrics and ablation study on RAG pipelines",
        "findings": [
            "Token reduction of 40% with minimal accuracy loss",
            "Chunking strategy has larger impact than retrieval model choice"
        ],
        "claims": [
            "Token efficiency should be a primary metric for RAG evaluation",
            "Smaller context windows force better retrieval precision"
        ],
        "limitations": [
            "Only evaluated on closed-domain QA datasets",
            "No comparison against non-agentic baselines"
        ]
    },
    {
        "paper_id": "rag_for_llm_survey",
        "title": "Retrieval Augmented Generation for LLMs: A Survey",
        "methodology": "Taxonomy and comparative analysis of RAG approaches",
        "findings": [
            "Dense retrieval consistently outperforms sparse retrieval on open-domain QA",
            "Re-ranking significantly improves final answer quality"
        ],
        "claims": [
            "RAG is now essential infrastructure for production LLM deployments",
            "Retrieval quality is the bottleneck, not generation quality"
        ],
        "limitations": [
            "Survey coverage limited to English-language papers",
            "Latency overhead of multi-agent systems is underreported"
        ]
    }
]


if __name__ == "__main__":
    print("=== Cross-Paper Agent Test ===\n")

    # Try real summaries first, fall back to mocks
    summaries = load_test_summaries()
    if len(summaries) < 2:
        print(f"  Only {len(summaries)} real summaries found, using mock data instead.\n")
        summaries = MOCK_SUMMARIES

    result = run_cross_paper_agent(summaries)

    print("\n--- Result ---")
    print(json.dumps(result, indent=2))

    # Basic assertions
    assert "contradictions" in result, "Missing contradictions key"
    assert "agreements" in result, "Missing agreements key"
    assert "repeated_limitations" in result, "Missing repeated_limitations key"
    assert "synthesis_note" in result, "Missing synthesis_note key"
    assert isinstance(result["contradictions"], list)
    assert isinstance(result["agreements"], list)
    assert isinstance(result["repeated_limitations"], list)
    assert len(result["synthesis_note"]) > 0

    print("\n All assertions passed.")