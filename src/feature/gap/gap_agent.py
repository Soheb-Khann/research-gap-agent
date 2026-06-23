# src/feature/gap/gap_agent.py

import json
from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# ── Prompts ───────────────────────────────────────────────────────────────────

GAP_SYSTEM_PROMPT = """You are an expert research analyst specialising in identifying gaps in academic literature.
You will be given structured summaries of multiple research papers.
Your job is to identify research gaps across these papers and return them as valid JSON only.
Do not include any explanation, markdown, or text outside the JSON."""


def build_gap_prompt(summaries: List[dict]) -> str:
    summaries_text = ""
    for s in summaries:
        limitations = s.get("limitations") or ["Not stated"]
        findings    = s.get("findings")    or ["Not stated"]
        claims      = s.get("claims")      or ["Not stated"]

        summaries_text += f"""
Paper: {s.get('title', s.get('paper_id', 'Unknown'))}
Methodology: {s.get('methodology') or 'Not stated'}
Findings: {json.dumps(findings)}
Claims: {json.dumps(claims)}
Limitations: {json.dumps(limitations)}
---"""

    return f"""Here are structured summaries of {len(summaries)} research papers:

{summaries_text}

Identify the most important research gaps across ALL these papers combined.
Classify each gap into one of these three categories:
- methodology: gaps in research design, experimental approach, or evaluation methods
- data: gaps in datasets — language coverage, domain diversity, realism, availability
- theory: gaps in conceptual understanding or untested theoretical claims

Return a JSON array. Each item must have exactly these fields:
{{
  "gap": "clear one-sentence description of the gap",
  "category": "methodology | data | theory",
  "severity": "high | medium | low",
  "evidence": ["direct quote or paraphrase from a paper limitation or finding that supports this gap"],
  "papers_affected": ["paper title or paper_id that exhibits this gap"],
  "suggested_future_work": "one sentence on how this gap could be addressed"
}}

Return ONLY the JSON array. No explanation, no markdown, no text outside the array."""


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_and_rank(gaps: List[dict], total_papers: int) -> List[dict]:
    """
    Adds frequency_score and priority_score to each gap, then sorts.

    priority_score = severity_weight × frequency
    This means a high-severity gap appearing in 3/5 papers
    ranks above a low-severity gap appearing in 5/5 papers.
    """
    severity_weight = {"high": 3, "medium": 2, "low": 1}

    for gap in gaps:
        affected  = gap.get("papers_affected") or []
        frequency = len(affected) / total_papers if total_papers > 0 else 0
        weight    = severity_weight.get(gap.get("severity", "low"), 1)

        gap["frequency_score"] = round(frequency, 2)
        gap["priority_score"]  = round(weight * frequency, 2)

    gaps.sort(key=lambda g: g["priority_score"], reverse=True)
    return gaps


# ── Main entry point ──────────────────────────────────────────────────────────

def run_gap_agent(summaries: List[dict]) -> List[dict]:
    """
    Takes List[dict] from summarise_node.
    Each dict must have: paper_id, title, methodology, findings, claims, limitations.
    Returns ranked list of gap dicts.
    """
    if not summaries:
        print("[gap_agent] No summaries provided, returning empty gaps")
        return []

    print(f"[gap_agent] Analysing {len(summaries)} summaries...")

    llm    = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    prompt = build_gap_prompt(summaries)

    response = llm.invoke([
        SystemMessage(content=GAP_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])

    # ── Parse JSON, strip markdown fences defensively ─────────────────────────
    raw = response.content.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        gaps = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[gap_agent] ❌ JSON parse failed: {e}")
        print(f"[gap_agent] Raw response (first 500 chars):\n{response.content[:500]}")
        return []

    print(f"[gap_agent] Extracted {len(gaps)} gaps before scoring")

    gaps = score_and_rank(gaps, total_papers=len(summaries))

    if gaps:
        print(f"[gap_agent] Top gap: '{gaps[0]['gap'][:80]}'")

    return gaps