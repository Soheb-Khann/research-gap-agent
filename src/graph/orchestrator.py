from typing import TypedDict, List
from langgraph.graph import StateGraph, END


# STATE - this state is shared across all nodes in the graph. Each node can read and write to this state.
class AgentState(TypedDict):
    pdf_paths: List[str]        # input: paths to uploaded PDFs
    chunks: List[str]           # output of ingestion node
    summaries: List[dict]       # output of summarisation node
    analysis: dict              # output of cross-paper analysis node
    gaps: List[dict]            # output of gap finder node
    final_report: str           # output of report generator node
    error: str                  # populated if any node fails


# NODES - these are nodes of the graph, each representing a step in the pipeline. Each node takes the current state as input and returns an updated state.

def ingest_node(state: AgentState) -> dict:
    """Loads PDFs, extracts text, chunks, embeds into ChromaDB."""
    print(f"[ingest_node] Received {len(state['pdf_paths'])} PDFs")
    # TODO: Person A implements real ingestion here
    return {"chunks": ["chunk_1_placeholder", "chunk_2_placeholder"]}


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

    # Edges (with error checking between each major step)
    graph.add_edge("ingest", "summarise")
    graph.add_edge("summarise", "analyse")
    graph.add_edge("analyse", "find_gaps")
    graph.add_edge("find_gaps", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


# RUNNER

if __name__ == "__main__":
    app = build_graph()

    # Test run with dummy input
    initial_state = {
        "pdf_paths": ["paper1.pdf", "paper2.pdf"],
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