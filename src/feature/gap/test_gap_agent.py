# src/feature/gap/test_gap_agent.py

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.feature.gap.gap_agent import run_gap_agent

MOCK_PATH = Path(__file__).parent / "test_summaries.json"

def test_gap_agent():
    summaries = json.loads(MOCK_PATH.read_text())
    gaps      = run_gap_agent(summaries)

    print(f"\n{'='*60}")
    print(f"Found {len(gaps)} gaps (ranked by priority):")
    print(f"{'='*60}\n")

    for i, g in enumerate(gaps, 1):
        print(f"[{i}] [{g['category'].upper()}] severity={g['severity']} | "
              f"frequency={g['frequency_score']} | priority={g['priority_score']}")
        print(f"     GAP:         {g['gap']}")
        print(f"     PAPERS:      {g['papers_affected']}")
        print(f"     FUTURE WORK: {g['suggested_future_work']}")
        print()

    # ── Assertions ────────────────────────────────────────────────────────────
    assert len(gaps) > 0,  "No gaps returned"

    for g in gaps:
        assert "gap"                   in g, f"Missing 'gap' key in: {g}"
        assert "category"              in g, f"Missing 'category' key"
        assert "severity"              in g, f"Missing 'severity' key"
        assert "papers_affected"       in g, f"Missing 'papers_affected' key"
        assert "suggested_future_work" in g, f"Missing 'suggested_future_work' key"
        assert "priority_score"        in g, f"Missing 'priority_score' key"
        assert g["category"] in ("methodology", "data", "theory"), \
            f"Invalid category: {g['category']}"
        assert g["severity"] in ("high", "medium", "low"), \
            f"Invalid severity: {g['severity']}"

    # Sorted correctly
    scores = [g["priority_score"] for g in gaps]
    assert scores == sorted(scores, reverse=True), "Gaps not sorted by priority_score"

    print("✅ test_gap_agent passed")

if __name__ == "__main__":
    test_gap_agent()