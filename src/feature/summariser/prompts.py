CHUNK_SUMMARY_PROMPT = """
You are reading an excerpt from a research paper.
Extract only what is clearly present in this text.

Text:
{chunk_text}

Respond in this exact format:
METHODOLOGY: <one sentence or 'not mentioned'>
FINDINGS: <bullet points or 'not mentioned'>
CLAIMS: <bullet points or 'not mentioned'>
LIMITATIONS: <bullet points or 'not mentioned'>
"""

FINAL_SUMMARY_PROMPT = """
You are consolidating partial summaries of a research paper into one structured JSON output.

Partial summaries from different sections of the paper:
{partial_summaries}

Return ONLY valid JSON, no explanation, no markdown fences:
{{
  "methodology": "single consolidated string",
  "findings": ["finding 1", "finding 2"],
  "claims": ["claim 1", "claim 2"],
  "limitations": ["limitation 1", "limitation 2"]
}}

Rules:
- Merge duplicates, keep unique points only
- If a field has nothing across all summaries, use an empty list [] or empty string ""
- Do NOT add anything outside the JSON
"""