import os
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
import streamlit as st
import tempfile, os, sys
from pathlib import Path

st.set_page_config(page_title="Research Gap Agent", page_icon="🔬")
st.title("🔬 Research Gap Agent")

uploaded = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

if st.button("▶ Run Pipeline", type="primary", disabled=not uploaded):

    # Save uploads to temp dir
    tmp_dir = tempfile.mkdtemp()
    pdf_paths = []
    for uf in uploaded:
        dest = os.path.join(tmp_dir, uf.name)
        with open(dest, "wb") as f:
            f.write(uf.getbuffer())
        pdf_paths.append(dest)

    # Add project root so src.* imports work
    root = Path(__file__).parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.graph.orchestrator import build_graph

    with st.status("Running pipeline...", expanded=True) as status:
        st.write("⏳ Ingesting and embedding PDFs...")
        graph = build_graph()
        result = graph.invoke({
            "pdf_paths": pdf_paths,
            "chunks": [], "summaries": [], "analysis": {},
            "gaps": [], "final_report": "", "error": ""
        })
        if result.get("error"):
            status.update(label="❌ Pipeline failed", state="error")
            st.error(result["error"])
            st.stop()
        status.update(label="✅ Done!", state="complete")

    report = result.get("final_report", "")

    st.divider()
    st.markdown(report)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇ Download Markdown", data=report,
                           file_name="research_gap_report.md", mime="text/markdown",
                           use_container_width=True)
    with col2:
        try:
            from docx import Document
            import io
            doc = Document()
            for line in report.split("\n"):
                line = line.rstrip()
                if line.startswith("# "):      doc.add_heading(line[2:], 1)
                elif line.startswith("## "):   doc.add_heading(line[3:], 2)
                elif line.startswith("### "):  doc.add_heading(line[4:], 3)
                elif line.startswith("#### "): doc.add_heading(line[5:], 4)
                elif line.startswith("- "):    doc.add_paragraph(line[2:], style="List Bullet")
                elif line == "---":            pass
                elif line:                     doc.add_paragraph(line)
            buf = io.BytesIO()
            doc.save(buf)
            st.download_button("⬇ Download Word (.docx)", data=buf.getvalue(),
                               file_name="research_gap_report.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)
        except ImportError:
            st.info("Install `python-docx` to enable Word export.")