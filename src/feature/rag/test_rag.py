"""
CLI test for the RAG loop.
Run from project root: python test_rag.py
"""

from src.feature.rag.rag_agent import run_rag

TEST_QUESTIONS = [
    "What are the main research gaps identified across these papers?",
    "What methodologies are most commonly used in these studies?",
    "What limitations do the authors acknowledge?",
    "Are there any contradictions between findings of different papers?",
    "What datasets are referenced across these studies?",
]

if __name__ == "__main__":
    print("=" * 60)
    print("RAG LOOP TEST")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[Q{i}] {q}")
        try:
            result = run_rag(q)

            # Basic validation
            assert result["answer"],           "answer is empty"
            assert result["sources"],          "no sources returned"
            assert result["retrieved_chunks"], "no chunks retrieved"

            print(f"  SOURCES : {result['sources']}")
            print(f"  CHUNKS  : {len(result['retrieved_chunks'])} retrieved")
            print(f"  ANSWER  :\n{result['answer']}")
            passed += 1

        except AssertionError as e:
            print(f"  ❌ FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR  — {e}")
            failed += 1

        print("-" * 60)

    print(f"\nRESULT: {passed}/{len(TEST_QUESTIONS)} passed", "✅" if failed == 0 else "❌")