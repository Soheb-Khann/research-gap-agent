import json
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from src.ingestion.embedder import retrieve, retrieve_by_source
from src.feature.summariser.prompts import CHUNK_SUMMARY_PROMPT, FINAL_SUMMARY_PROMPT


load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant")


def _get_chunks_for_paper(paper_id: str) -> list[dict]:
    """
    Pulls chunks for a specific paper using metadata filtering.
    paper_id must match the 'source' field stored in ChromaDB (i.e. the filename).
    """
    results = retrieve_by_source(
        source=paper_id,    # e.g. 'retrieval_augmented_generation_for_llm_a_survey.pdf'
        query="methodology findings results limitations conclusions",
        n_results=30
    )
    return results


def _summarise_chunks(chunks: list[str]) -> list[str]:
    """Map step: summarise each chunk individually."""
    partial_summaries = []

    for i, chunk in enumerate(chunks):
        prompt = CHUNK_SUMMARY_PROMPT.format(chunk_text=chunk)
        response = llm.invoke([HumanMessage(content=prompt)])
        partial_summaries.append(response.content)
        print(f"  [summariser] chunk {i+1}/{len(chunks)} done")

    return partial_summaries


def _consolidate_summaries(partial_summaries: list[str]) -> dict:
    """Reduce step: merge all partial summaries into one structured JSON."""
    combined = "\n\n---\n\n".join(partial_summaries)
    prompt = FINAL_SUMMARY_PROMPT.format(partial_summaries=combined)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content

    # Strip markdown fences
    raw = re.sub(r"```json|```", "", raw).strip()

    # Fix trailing commas before ] or } (invalid JSON but common LLM mistake)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    return json.loads(raw)


def summarise_paper(paper_id: str, title: str) -> dict:
    """
    Full map-reduce summarisation for one paper.
    Returns structured dict ready to be saved as JSON.
    """
    print(f"\n[summariser] Starting: {title}")

    chunks = _get_chunks_for_paper(paper_id)

    if not chunks:
        print(f"  [summariser] WARNING: No chunks found for {paper_id}")
        return {
            "paper_id": paper_id,
            "title": title,
            "methodology": "",
            "findings": [],
            "claims": [],
            "limitations": []
        }

    partial_summaries = _summarise_chunks(chunks)
    summary = _consolidate_summaries(partial_summaries)

    summary["paper_id"] = paper_id
    summary["title"] = title

    print(f"  [summariser] Done: {title}")
    return summary


def save_summaries(summaries: list[dict], output_dir: str = "outputs/summaries"):
    """Save each paper summary as its own JSON file."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    for s in summaries:
        path = os.path.join(output_dir, f"{s['paper_id']}.json")
        with open(path, "w") as f:
            json.dump(s, f, indent=2)
        print(f"  [summariser] Saved: {path}")