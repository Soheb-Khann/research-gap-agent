from typing import List
from datetime import datetime


def build_report(gaps: List[dict], summaries: List[dict], analysis: dict) -> str:
    """
    Generates a structured Markdown report from gaps, summaries, and analysis.
    Pure formatting — no LLM call needed, the hard thinking already happened upstream.
    """
    now          = datetime.now().strftime("%Y-%m-%d %H:%M")
    paper_titles = [s.get("title", s.get("paper_id", "Unknown")) for s in summaries]

    # ── Header ────────────────────────────────────────────────────────────────
    lines = [
        "# Research Gap Analysis Report",
        f"\n_Generated: {now}_\n",
        "---\n",
        "## Papers Analysed\n",
    ]
    for i, title in enumerate(paper_titles, 1):
        lines.append(f"{i}. {title}")

    # ── Stats ─────────────────────────────────────────────────────────────────
    high   = sum(1 for g in gaps if g.get("severity") == "high")
    medium = sum(1 for g in gaps if g.get("severity") == "medium")
    low    = sum(1 for g in gaps if g.get("severity") == "low")

    cat_counts = {}
    for g in gaps:
        cat = g.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    cat_summary = " · ".join(f"{v} {k}" for k, v in cat_counts.items())

    lines += [
        "\n---\n",
        "## Summary\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Papers analysed | {len(summaries)} |",
        f"| Total gaps found | {len(gaps)} |",
        f"| High severity | {high} |",
        f"| Medium severity | {medium} |",
        f"| Low severity | {low} |",
        f"| By category | {cat_summary} |",
    ]

    # ── Cross-paper analysis ──────────────────────────────────────────────────
    if analysis:
        contradictions = analysis.get("contradictions")       or []
        agreements     = analysis.get("agreements")           or []
        repeated       = analysis.get("repeated_limitations") or []
        synthesis      = analysis.get("synthesis_note",       "")

        lines += ["\n---\n", "## Cross-Paper Analysis\n"]

        if synthesis:
            lines += [f"> {synthesis}\n"]

        if agreements:
            lines.append("### Agreements Across Papers\n")
            for a in agreements:
                papers = ", ".join(a.get("papers", []))
                lines.append(f"- **{a.get('topic', '')}**: {a.get('shared_claim', '')}  ")
                lines.append(f"  _{papers}_\n")

        if contradictions:
            lines.append("### Contradictions & Tensions\n")
            for c in contradictions:
                lines.append(f"- **{c.get('topic', '')}**")
                lines.append(f"  - _{c.get('paper_a', '')}_: {c.get('claim_a', '')}")
                lines.append(f"  - _{c.get('paper_b', '')}_: {c.get('claim_b', '')}")
                if c.get('explanation'):
                    lines.append(f"  - 💡 {c.get('explanation')}\n")

        if repeated:
            lines.append("### Shared Limitations Across Papers\n")
            for r in repeated:
                papers = ", ".join(r.get("papers", []))
                lines.append(f"- **{r.get('limitation_theme', '')}** "
                             f"(appears in {r.get('frequency', '?')} papers)")
                lines.append(f"  _{papers}_\n")

    # ── Gaps by category ──────────────────────────────────────────────────────
    lines += ["\n---\n", "## Research Gaps\n"]

    SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    for category in ["methodology", "data", "theory"]:
        cat_gaps = [g for g in gaps if g.get("category") == category]
        if not cat_gaps:
            continue

        lines.append(f"### {category.title()} Gaps\n")

        for i, gap in enumerate(cat_gaps, 1):
            severity    = gap.get("severity", "low")
            emoji       = SEVERITY_EMOJI.get(severity, "⚪")
            score       = gap.get("priority_score", 0)
            papers      = gap.get("papers_affected") or []
            evidence    = gap.get("evidence")         or []
            future_work = gap.get("suggested_future_work", "")

            lines.append(f"#### {i}. {gap.get('gap', 'No description')}\n")
            lines.append(f"{emoji} **Severity:** {severity.title()} · "
                        f"**Priority score:** {score} · "
                        f"**Frequency:** {gap.get('frequency_score', 0)}\n")

            if papers:
                lines.append(f"**Appears in:** {', '.join(papers)}\n")

            if evidence:
                lines.append("**Evidence:**\n")
                for e in evidence:
                    lines.append(f"> {e}\n")

            if future_work:
                lines.append(f"**Suggested future work:** {future_work}\n")

    # ── Footer ────────────────────────────────────────────────────────────────
    lines += [
        "---\n",
        "_This report was generated automatically by the Research Gap Agent._  ",
        "_All findings should be verified by a domain expert before use._"
    ]

    return "\n".join(lines)