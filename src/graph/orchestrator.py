from pathlib import Path
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import sys, pypdf

# Ensure repo root is importable when running as a script:
#   python src/graph/orchestrator.py
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ingestion helpers

from src.ingestion.pdf_extractor import extract_text_from_pdf, extract_text_by_blocks
from src.ingestion.text_cleaner import clean_pages
from src.ingestion.chunker import chunk_by_paragraphs, chunk_with_overlap


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

def is_multi_column_pdf(pdf_path: str, sample_pages: int = 3) -> bool:
    """
    Multi-column detector using combined heuristics.

    Strategy:
    1. Look for indentation patterns (separate left/right content)
    2. Look for short-line constraints (narrow column width)
    3. Require BOTH signals to confidently classify as multi-column
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(str(path), "rb") as f:
        reader = pypdf.PdfReader(f)
        pages_to_check = min(sample_pages, len(reader.pages))

        indentation_signals = 0
        short_line_signals = 0

        for page_idx in range(pages_to_check):
            page = reader.pages[page_idx]
            
            try:
                layout_text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                layout_text = page.extract_text() or ""

            if not layout_text.strip():
                continue

            lines = layout_text.splitlines()
            
            if len(lines) < 10:
                continue

            # Analyze indentation patterns
            indents = []
            for line in lines:
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip())
                indents.append(indent)

            if not indents:
                continue

            # Analyze short lines (column constraint indicator)
            non_empty_lines = [ln for ln in lines if ln.strip()]
            short_lines = sum(1 for ln in non_empty_lines if len(ln.strip()) < 50)
            short_line_ratio = short_lines / len(non_empty_lines) if non_empty_lines else 0

            # Signal 1: Indentation clustering
            indent_counts = {}
            for indent in indents:
                bin_indent = (indent // 10) * 10
                indent_counts[bin_indent] = indent_counts.get(bin_indent, 0) + 1

            indent_bins = sorted(indent_counts.keys())
            
            # Check for 2 distinct indent clusters with significant separation
            if len(indent_bins) >= 2:
                for i in range(len(indent_bins) - 1):
                    bin1, bin2 = indent_bins[i], indent_bins[i + 1]
                    count1, count2 = indent_counts[bin1], indent_counts[bin2]
                    
                    # Two clusters: enough lines in each, moderate separation
                    if count1 >= 10 and count2 >= 10 and (bin2 - bin1) >= 15:
                        indentation_signals += 1
                        break

            # Signal 2: High short-line ratio (>40%)
            if short_line_ratio > 0.40:
                short_line_signals += 1
            elif short_line_ratio > 0.30:
                pass  # Near threshold but not quite


        # Require either strong indentation or high short-line ratio
        # Just 1 page with clear pattern is sufficient
        result = (indentation_signals >= 1) or (short_line_signals >= 1)
        return result


def extract_pages_with_layout_awareness(pdf_path: str) -> List[dict]:
    """Choose extractor based on detected layout, with fallback for robustness."""
    multi_column = is_multi_column_pdf(pdf_path)

    if multi_column:
        print(f"[ingest_node] {pdf_path}: multi-column detected -> block extraction")
        pages = extract_text_by_blocks(pdf_path)
        if not pages or not any((p.get("text") or "").strip() for p in pages):
            print(f"[ingest_node] {pdf_path}: block extraction empty, falling back to default extractor")
            pages = extract_text_from_pdf(pdf_path)
        return pages

    print(f"[ingest_node] {pdf_path}: single-column detected -> default extraction")
    return extract_text_from_pdf(pdf_path)

def ingest_node(state: AgentState) -> dict:
    """Loads PDFs, extracts text, chunks, embeds into ChromaDB."""
    print(f"[ingest_node] Received {len(state.get('pdf_paths', []))} PDFs")

    pdf_paths = state.get("pdf_paths") or []
    all_chunks = []
    next_chunk_id = 0

    try:
        for pdf_path in pdf_paths:
            # Stage 1: layout-aware extraction
            pages = extract_pages_with_layout_awareness(pdf_path)

            # Stage 2: cleaning
            cleaned = clean_pages(pages)

            # Stage 3: chunking — prefer paragraph chunking, fall back to overlap if empty
            chunks = chunk_by_paragraphs(cleaned, min_length=100, max_length=1500)
            if not chunks:
                chunks = chunk_with_overlap(cleaned, chunk_size=512, overlap=64)

            # Reassign chunk ids to be globally unique across all PDFs
            for c in chunks:
                c["chunk_id"] = next_chunk_id
                next_chunk_id += 1
                all_chunks.append(c)

        if not all_chunks:
            return {"error": "Ingestion produced no chunks. Check PDF paths or chunking thresholds."}

        print(f"[ingest_node] Produced {len(all_chunks)} chunks")
        return {"chunks": all_chunks}

    except Exception as e:
        # Propagate error into shared agent state for the graph to handle
        state["error"] = str(e)
        return {"error": state["error"]}


def summarise_node(state: AgentState) -> dict:
    """Summarises each paper: methodology, findings, claims, limitations."""
    print(f"[summarise_node] Summarising {len(state['chunks'])} chunks")
    # TODO: implement summarisation agent
    return {"summaries": [{"paper": "paper_1", "summary": "placeholder"}]}


def analyse_node(state: AgentState) -> dict:
    """Compares summaries: finds contradictions, agreements, repeated limits."""
    print(f"[analyse_node] Analysing {len(state['summaries'])} summaries")
    # TODO: implement cross-paper analysis agent
    return {"analysis": {"contradictions": [], "agreements": []}}


def gap_finder_node(state: AgentState) -> dict:
    """Identifies and ranks research gaps from the analysis."""
    print(f"[gap_finder_node] Finding gaps from analysis")
    # TODO: implement gap identification agent
    return {"gaps": [{"gap": "placeholder gap", "severity": "high"}]}


def report_node(state: AgentState) -> dict:
    """Generates the final structured Markdown report."""
    print(f"[report_node] Generating report for {len(state['gaps'])} gaps")
    # TODO: implement report generator
    return {"final_report": "# Research Gap Report\n\nPlaceholder."}


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
    app = build_graph()

    # Test run with dummy input
    initial_state = {
        "pdf_paths": collect_pdfs(sys.argv[1:]),
        "chunks": [],
        "summaries": [],
        "analysis": {},
        "gaps": [],
        "final_report": "",
        "error": ""
    }

    result = app.invoke(initial_state)
    print("\n── Final Report ──")
    print(result["final_report"])