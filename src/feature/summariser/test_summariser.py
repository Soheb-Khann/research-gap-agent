import json
from src.feature.summariser.summariser_agent import summarise_paper, save_summaries


# ── change these to match a real paper_id in your ChromaDB ──────────────────
TEST_PAPER_ID = "paper_001"
TEST_TITLE    = "Test Paper One"
# ────────────────────────────────────────────────────────────────────────────


def test_structure():
    """Check all required keys exist and have correct types."""
    result = summarise_paper(TEST_PAPER_ID, TEST_TITLE)

    print("\n=== RAW OUTPUT ===")
    print(json.dumps(result, indent=2))

    assert "paper_id"     in result,               "Missing paper_id"
    assert "title"        in result,               "Missing title"
    assert "methodology"  in result,               "Missing methodology"
    assert "findings"     in result,               "Missing findings"
    assert "claims"       in result,               "Missing claims"
    assert "limitations"  in result,               "Missing limitations"

    assert isinstance(result["methodology"],  str),  "methodology should be a string"
    assert isinstance(result["findings"],     list), "findings should be a list"
    assert isinstance(result["claims"],       list), "claims should be a list"
    assert isinstance(result["limitations"],  list), "limitations should be a list"

    print("\n✅ Structure test passed")
    return result


def test_save():
    """Check the JSON file actually gets written to disk."""
    import os
    result = summarise_paper(TEST_PAPER_ID, TEST_TITLE)
    save_summaries([result], output_dir="src/summariser/outputs/test_summaries")

    expected_path = f"src/summariser/outputs/test_summaries/{TEST_PAPER_ID}.json"
    assert os.path.exists(expected_path), f"File not found: {expected_path}"

    with open(expected_path) as f:
        loaded = json.load(f)

    assert loaded["paper_id"] == TEST_PAPER_ID, "paper_id mismatch in saved file"
    print(f"\n✅ Save test passed — file at {expected_path}")


if __name__ == "__main__":
    test_structure()
    test_save()