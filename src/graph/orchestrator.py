from pathlib import Path
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
# from src.feature.rag.rag_agent import run_rag
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ingestion
from src.ingestion.pdf_extractor import extract_pdf   
from src.ingestion.text_cleaner import clean_pages
from src.ingestion.chunker import chunk_by_paragraphs, chunk_with_overlap
from src.ingestion.embedder import embed_and_store, list_sources

# agent imports
from src.feature.summariser.summariser_agent import summarise_paper
from src.feature.gap.gap_agent import run_gap_agent
from src.feature.report.report_agent import build_report




# STATE - this state is shared across all nodes in the graph. Each node can read and write to this state.
class AgentState(TypedDict):
    pdf_paths: List[str]        # input: paths to uploaded PDFs
    chunks: List[dict]          # output of ingestion node
    summaries: List[dict]       # output of summarisation node
    analysis: dict              # output of cross-paper analysis node
    gaps: List[dict]            # output of gap finder node
    final_report: str           # output of report generator node
    error: str                  # populated if any node fails


# NODES - these are nodes of the graph, each representing a step in the pipeline. Each node takes the current state as input and returns an updated state.

def ingest_node(state: AgentState) -> dict:
    """
    Stage 1: Load PDFs, detect layout, extract text
    Stage 2: Clean pages
    Stage 3: Chunk (paragraph-first, overlap fallback)
    Stage 4: Embed and store in ChromaDB
    """
    pdf_paths = state.get("pdf_paths") or []
    print(f"[ingest_node] Received {len(pdf_paths)} PDF(s)")

    if not pdf_paths:
        return {"error": "No PDF paths provided."}

    all_chunks = []
    next_chunk_id = 0

    try:
        for pdf_path in pdf_paths:
            print(f"[ingest_node] Processing: {pdf_path}")

            # Stage 1: layout-aware extraction
            pages, layout = extract_pdf(pdf_path)
            print(f"[ingest_node]   → layout={layout}, pages={len(pages)}")

            # Stage 2: clean
            cleaned = clean_pages(pages)
            print(f"[ingest_node]   → cleaned pages={len(cleaned)}")

            if not cleaned:
                print(f"[ingest_node]   ⚠ No content after cleaning, skipping {pdf_path}")
                continue
            # Stage 3: chunk
            chunks = chunk_by_paragraphs(cleaned, min_length=100, max_length=1500)
            if not chunks:
                print(f"[ingest_node]   ⚠ Paragraph chunking produced nothing, falling back to overlap")
                chunks = chunk_with_overlap(cleaned, chunk_size=512, overlap=64)
            # Reassign chunk IDs to be globally unique across all PDFs
            for c in chunks:
                c["chunk_id"] = next_chunk_id
                next_chunk_id += 1
                all_chunks.append(c)
            print(f"[ingest_node]   → chunks={len(chunks)}")
        if not all_chunks:
            return {"error": "Ingestion produced no chunks. Check PDF paths or content."}

        # Stage 4: embed and store
        print(f"[ingest_node] Total chunks across all PDFs: {len(all_chunks)}")
        embed_and_store(all_chunks)

        return {"chunks": all_chunks}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def summarise_node(state: AgentState) -> dict:
    """
    Summarises each paper by retrieving its chunks from ChromaDB by source filename.
    """
    chunks = state.get("chunks") or []

    # Get unique source filenames from the chunks stored in state
    sources = list({c["source"] for c in chunks})
    print(f"[summarise_node] Summarising {len(sources)} papers: {sources}")

    summaries = []
    for source in sources:
        summary = summarise_paper(
            paper_id=source,               # filename IS the paper_id
            title=source.replace("_", " ").replace(".pdf", "").title()
        )
        summaries.append(summary)

    if not summaries:
        return {"error": "Summarisation produced no output."}

    return {"summaries": summaries}


def analyse_node(state: AgentState) -> dict:
    """Compares summaries: finds contradictions, agreements, repeated limits."""
    from src.feature.cross_paper.cross_paper_agent import run_cross_paper_agent

    summaries = state.get("summaries", [])
    print(f"[analyse_node] Analysing {len(summaries)} summaries")

    if len(summaries) < 2:
        return {"error": f"Need at least 2 paper summaries for cross-paper analysis, got {len(summaries)}."}

    try:
        result = run_cross_paper_agent(summaries)
        return {"analysis": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Cross-paper agent failed: {e}"}


def gap_finder_node(state: AgentState) -> dict:
    summaries = state.get("summaries") or []
    analysis  = state.get("analysis")  or {}   # ← pull analysis from state

    if not summaries:
        return {"error": "No summaries in state — cannot run gap agent."}

    print(f"[gap_finder_node] Running gap analysis on {len(summaries)} paper summaries")

    try:
        gaps = run_gap_agent(summaries, analysis)   # ← pass it through
        if not gaps:
            return {"error": "Gap agent returned no gaps."}
        print(f"[gap_finder_node] Found {len(gaps)} gaps")
        return {"gaps": gaps}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    

def report_node(state: AgentState) -> dict:
    """Generates the final structured Markdown report."""
    gaps      = state.get("gaps")      or []
    summaries = state.get("summaries") or []
    analysis  = state.get("analysis")  or {}

    print(f"[report_node] Generating report — {len(gaps)} gaps across {len(summaries)} papers")

    try:
        report = build_report(gaps, summaries, analysis)
        return {"final_report": report}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def error_node(state: AgentState) -> dict:
    """Handles errors from any node."""
    print(f"[error_node] Error caught: {state.get('error')}")
    return {"final_report": f"Pipeline failed: {state.get('error')}"}


# CONDITIONAL EDGE - this is a conditional edge where the agent checks for errors after each major step. If an error is found, it transitions to the error handling node; otherwise, it continues to the next step. 

def check_for_errors(state: AgentState) -> str:
    """After each major step, check if an error occurred."""
    if state.get("error"):
        return "handle_error"
    return "continue"


# BUILD THE GRAPH - this function constructs the graph by registering nodes, defining edges, and setting the entry point. It returns a compiled StateGraph ready for execution.

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes - each node is added to the graph with a unique name
    graph.add_node("ingest",        ingest_node)
    graph.add_node("summarise",     summarise_node)
    graph.add_node("analyse",       analyse_node)
    graph.add_node("find_gaps",     gap_finder_node)
    graph.add_node("generate_report", report_node)
    graph.add_node("handle_error",  error_node)

    # Entry point - this is the first node that will be executed when the graph is invoked
    graph.set_entry_point("ingest")

    # Edges with error checking between each major step
    graph.add_conditional_edges(
        "ingest",
        check_for_errors,
        {"continue": "summarise", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "summarise",
        check_for_errors,
        {"continue": "analyse", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "analyse",
        check_for_errors,
        {"continue": "find_gaps", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "find_gaps",
        check_for_errors,
        {"continue": "generate_report", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "generate_report",
        check_for_errors,
        {"continue": END, "handle_error": "handle_error"},
    )
    graph.add_edge("handle_error", END)

    return graph.compile()


# RUNNER


def collect_pdfs(args) -> list:
    """
    Accept any mix of:
      - individual PDF files  →  paper1.pdf paper2.pdf
      - a folder              →  papers/
      - no args: defaults to ./test_pdfs/
    Returns a flat list of PDF path strings.
    """
    pdfs = []
    
    # If no args provided, use default test_pdfs folder
    if not args:
        args = ["test_pdfs"]
    
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            found = sorted(p.glob("*.pdf"))
            if not found:
                print(f"  ⚠  No PDFs found in folder: {p}")
            pdfs.extend([str(pdf) for pdf in found])
        elif p.suffix.lower() == ".pdf":
            if p.exists():
                pdfs.append(str(p))
            else:
                print(f"  ⚠  File not found, skipping: {p}")
        else:
            print(f"  ⚠  Not a PDF, skipping: {p}")
    return pdfs

if __name__ == "__main__":
    import os
    app = build_graph()

    initial_state = {
        "pdf_paths":    collect_pdfs(sys.argv[1:]),
        "chunks":       [],
        "summaries":    [],
        "analysis":     {},
        "gaps":         [],
        "final_report": "",
        "error":        ""
    }

    result = app.invoke(initial_state)

    report = result.get("final_report", "")
    print("\n── Final Report ──")
    print(report)

    # Save to disk
    os.makedirs("outputs", exist_ok=True)
    out_path = "outputs/report.md"
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\n✅ Report saved to {out_path}")