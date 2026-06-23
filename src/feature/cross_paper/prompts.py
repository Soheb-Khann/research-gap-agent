CROSS_PAPER_PROMPT = """
You are an expert academic analyst comparing multiple research paper summaries.

Paper summaries:
{paper_summaries}

Analyse across all papers and return ONLY valid JSON, no explanation, no markdown fences:
{{
  "contradictions": [
    {{
      "topic": "short label",
      "paper_a": "paper_id",
      "paper_b": "paper_id",
      "claim_a": "what paper_a claims",
      "claim_b": "what paper_b claims that contradicts it",
      "explanation": "why these contradict"
    }}
  ],
  "agreements": [
    {{
      "topic": "short label",
      "papers": ["paper_id", "paper_id"],
      "shared_claim": "what they all agree on"
    }}
  ],
  "repeated_limitations": [
    {{
      "limitation_theme": "theme label",
      "papers": ["paper_id"],
      "frequency": 2,
      "representative_quote": "closest verbatim limitation from one paper"
    }}
  ],
  "synthesis_note": "1-2 sentence high-level takeaway from comparing these papers"
}}

Rules:
- Only include contradictions where papers make genuinely opposing claims
- Agreements need at least 2 papers
- Repeated limitations need at least 2 papers sharing the same theme
- Do NOT add anything outside the JSON
"""