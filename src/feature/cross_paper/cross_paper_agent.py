import json
import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

from src.feature.cross_paper.prompts import CROSS_PAPER_PROMPT

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant")


def _format_summaries_for_prompt(summaries: list[dict]) -> str:
    """
    Serialises the list of summary dicts into a readable block for the LLM.
    Matches the dict structure output by summariser_agent.py:
      paper_id, title, methodology, findings, claims, limitations
    """
    lines = []
    for s in summaries:
        lines.append(f"### Paper ID: {s.get('paper_id', 'unknown')}")
        lines.append(f"Title: {s.get('title', 'unknown')}")
        lines.append(f"Methodology: {s.get('methodology', '')}")

        findings = s.get("findings", [])
        lines.append("Findings:")
        for f in findings:
            lines.append(f"  - {f}")

        claims = s.get("claims", [])
        lines.append("Claims:")
        for c in claims:
            lines.append(f"  - {c}")

        limitations = s.get("limitations", [])
        lines.append("Limitations:")
        for lim in limitations:
            lines.append(f"  - {lim}")

        lines.append("")

    return "\n".join(lines)


def run_cross_paper_agent(summaries: list[dict]) -> dict:
    """
    Compare a list of paper summary dicts (output of summarise_paper()).

    Args:
        summaries: list of dicts with keys:
                   paper_id, title, methodology, findings, claims, limitations

    Returns:
        dict with keys: contradictions, agreements, repeated_limitations, synthesis_note

    Raises:
        ValueError: if fewer than 2 summaries provided
        json.JSONDecodeError: if LLM returns malformed JSON
    """
    if len(summaries) < 2:
        raise ValueError(
            f"Cross-paper analysis needs at least 2 papers, got {len(summaries)}."
        )

    formatted = _format_summaries_for_prompt(summaries)
    prompt = CROSS_PAPER_PROMPT.format(paper_summaries=formatted)

    print(f"[cross_paper_agent] Comparing {len(summaries)} papers...")
    time.sleep(10)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content

    # Strip markdown fences if model adds them — same pattern as your summariser
    raw = re.sub(r"```json|```", "", raw).strip()
    raw = re.sub(r",\s*([}\]])", r"\1", raw)  

    result = json.loads(raw)

    print(f"  [cross_paper_agent] Found {len(result.get('contradictions', []))} contradictions")
    print(f"  [cross_paper_agent] Found {len(result.get('agreements', []))} agreements")
    print(f"  [cross_paper_agent] Found {len(result.get('repeated_limitations', []))} repeated limitations")

    return result