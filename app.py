"""
app.py — single-page Streamlit dashboard for the EF Version Explainer.

Run:  streamlit run app.py

Sidebar: pick the two DEFRA workbooks (real files in data/ or the synthetic demo
files) and upload a product BOM CSV. Main: headline delta, coverage, biggest
movers, an expandable explanation per flagged material, and a download button.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from paths import resolve_paths          # noqa: E402
from pipeline import run_pipeline         # noqa: E402
from report import build_markdown_report  # noqa: E402
from explain import active_backend        # noqa: E402

st.set_page_config(page_title="EF Version Explainer", layout="wide")

st.title("Emission-Factor Version Explainer")
st.caption(
    "Compare two annual DEFRA GHG conversion-factor releases, recompute a "
    "product's footprint under each, and explain what changed — grounded in the "
    "official DEFRA changes report."
)

defaults = resolve_paths()

with st.sidebar:
    st.header("Inputs")
    if defaults["using_real_data"]:
        st.success("Using REAL DEFRA full-set workbooks found in data/.")
    else:
        st.info(
            "Using SYNTHETIC demo data. Drop real DEFRA full-set workbooks into "
            "data/ (e.g. ghg-conversion-factors-2025-full-set.xlsx and the 2026 "
            "file) to use genuine figures."
        )

    old_label = st.text_input("Old version label", defaults["old_label"])
    new_label = st.text_input("New version label", defaults["new_label"])

    st.markdown("**Product bill-of-materials (CSV)**")
    st.caption("Columns: line_item, quantity, unit")
    uploaded = st.file_uploader("Upload a BOM CSV", type=["csv"])

    backend = active_backend()
    if backend["live"]:
        st.caption(f"Explanation layer: {backend['provider']} ({backend['model']}) ✓")
    else:
        st.caption(
            "Explanation layer: offline mode. Set GEMINI_API_KEY (Gemini) or "
            "ANTHROPIC_API_KEY (Claude) to use a live model."
        )

    run = st.button("Run analysis", type="primary")


@st.cache_data(show_spinner=False)
def _run(old_p, new_p, pdf_p, bom_csv_bytes, bom_path, old_l, new_l):
    if bom_csv_bytes is not None:
        import io

        bom_df = pd.read_csv(io.BytesIO(bom_csv_bytes))
    else:
        bom_df = pd.read_csv(bom_path)
    return run_pipeline(old_p, new_p, pdf_p, bom_df, old_l, new_l)


if run or "results" not in st.session_state:
    with st.spinner("Loading, diffing, matching, recomputing, explaining…"):
        results = _run(
            defaults["defra_old"],
            defaults["defra_new"],
            defaults["changes_pdf"],
            uploaded.getvalue() if uploaded else None,
            defaults["bom"],
            old_label,
            new_label,
        )
        st.session_state["results"] = results

results = st.session_state["results"]
s = results["summary"]

# --- Headline metrics ---
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Footprint ({results['labels']['old']})", f"{s['total_old']:.3g} kg")
c2.metric(
    f"Footprint ({results['labels']['new']})",
    f"{s['total_new']:.3g} kg",
    delta=f"{s['pct_delta']}%" if s["pct_delta"] is not None else None,
)
c3.metric("Coverage", f"{s['coverage_pct']}%")
c4.metric("Flagged movers", int(results["diff_df"]["flagged"].sum()))

if results["context"].get("breaches_baseline"):
    st.warning(
        "⚠️ The footprint increased — this would **breach a flat baseline**. "
        "Flag for review against active targets (e.g. SBTi)."
    )
else:
    st.success("Footprint did not increase against a flat baseline.")

ds = results.get("diff_stats")
if ds:
    st.caption(
        f"Version scan: {ds['flagged']} factors moved past DEFRA thresholds across "
        f"{ds['joined']} present in both years · {ds['added']} added, "
        f"{ds['removed']} removed (added/removed include DEFRA relabels)."
    )

# --- Biggest movers ---
st.subheader("Biggest contributors to the change")
top = results["top_delta"]
if top is not None and not top.empty:
    show = top[["line_item", "factor_old", "factor_new", "co2e_old", "co2e_new", "line_delta"]]
    st.dataframe(show, width="stretch", hide_index=True)
else:
    st.write("No computable movers.")

# --- Explanations ---
st.subheader("What changed and why")
st.caption(
    "Grounded strictly in the DEFRA changes notes (a Major Changes PDF if "
    "provided, otherwise the workbook's 'What's new' sheet). Where the notes are "
    "silent, the tool says so instead of inventing a reason."
)
if not results["explanations"]:
    st.write("No flagged, footprint-relevant factor changes.")
for e in results["explanations"]:
    header = (
        f"{e['activity']}  ·  {e['scope']}  ·  "
        f"{e['kg_co2e_old']:g} → {e['kg_co2e_new']:g}  ({e['pct_change']:+.1f}%)"
    )
    with st.expander(header):
        st.markdown(f"**Why it changed.** {e['plain_english_reason']}")
        st.markdown(f"**Methodology note.** {e['methodology_note']}")
        st.markdown(f"**Target impact.** {e['target_impact_flag']}")
        st.caption(f"retrieval relevance score: {e['retrieval_score']}")

# --- Needs review ---
st.subheader("Needs review (never guessed)")
review = results["matched_df"][results["matched_df"]["needs_review"]]
if review.empty:
    st.write("Every BOM line matched with confidence.")
else:
    st.dataframe(
        review[["line_item", "unit", "match_score", "match_method"]],
        width="stretch",
        hide_index=True,
    )

# --- Download ---
st.subheader("Export")
report_md = build_markdown_report(results)
st.download_button(
    "Download report (Markdown)",
    data=report_md,
    file_name="ef_version_report.md",
    mime="text/markdown",
)
