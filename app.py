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

# Load a local .env (git-ignored) so GEMINI_API_KEY / ANTHROPIC_API_KEY are
# picked up automatically. Optional — no-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

from paths import resolve_paths          # noqa: E402
from pipeline import run_pipeline         # noqa: E402
from report import build_markdown_report  # noqa: E402
from explain import active_backend        # noqa: E402
from ingest import read_table, guess_mapping, build_inventory  # noqa: E402

st.set_page_config(page_title="EF Version Explainer", layout="wide")


@st.cache_data(show_spinner=False)
def _read_raw(file_bytes, file_name):
    """Read an uploaded .csv/.xlsx into a raw DataFrame (cached on its bytes)."""
    import io

    bio = io.BytesIO(file_bytes)
    bio.name = file_name  # read_table picks the reader from the extension
    return read_table(bio)

st.title("Emission-Factor Version Explainer")
st.caption(
    "Compare two annual DEFRA GHG conversion-factor releases, recompute a "
    "product's footprint under each, and explain what changed, grounded in the "
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

    st.markdown("**Product inventory / bill-of-materials**")
    st.caption(
        "Upload a .csv or .xlsx. Any column names are fine (Material, Qty, UoM "
        "and so on). You confirm which is which below. Nothing is assumed silently."
    )
    uploaded = st.file_uploader("Upload an inventory file", type=["csv", "xlsx"])

    # A real client file rarely has the exact columns the pipeline needs, so we
    # guess the mapping and let the user confirm or fix it (the no-guess rule,
    # applied at the column level). clean_bom_df stays None when nothing is
    # uploaded, in which case the sample BOM is used.
    clean_bom_df = None
    set_aside: list = []
    ingest_ready = True  # the built-in sample path is always ready

    if uploaded is not None:
        try:
            raw_df = _read_raw(uploaded.getvalue(), uploaded.name)
        except Exception as exc:
            st.error(f"Could not read that file: {exc}")
            raw_df = None
            ingest_ready = False

        if raw_df is not None and len(raw_df.columns) > 0:
            cols = [str(c) for c in raw_df.columns]
            guessed, confidence = guess_mapping(cols)

            st.markdown("**Confirm your columns**")
            placeholder = "(select a column)"
            options = [placeholder] + cols

            def _default_index(field):
                g = guessed.get(field)
                return (cols.index(g) + 1) if g in cols else 0

            sel_item = st.selectbox("Item / material", options, index=_default_index("line_item"))
            sel_qty = st.selectbox("Quantity", options, index=_default_index("quantity"))
            sel_unit = st.selectbox("Unit", options, index=_default_index("unit"))

            mapping = {
                "line_item": None if sel_item == placeholder else sel_item,
                "quantity": None if sel_qty == placeholder else sel_qty,
                "unit": None if sel_unit == placeholder else sel_unit,
            }
            picked = [c for c in mapping.values() if c]
            if len(picked) < 3:
                st.warning("Pick the item, quantity, and unit columns to continue.")
                ingest_ready = False
            elif len(set(picked)) < 3:
                st.warning("Each column can be used once. Pick three different columns.")
                ingest_ready = False
            else:
                clean_bom_df, set_aside = build_inventory(raw_df, mapping)
                if clean_bom_df.empty:
                    st.error("No usable rows after applying that mapping. Check the columns.")
                    ingest_ready = False
                else:
                    st.success(f"{len(clean_bom_df)} of {len(raw_df)} rows ready.")
                    if set_aside:
                        st.caption(f"{len(set_aside)} row(s) set aside (shown in the report).")
        elif raw_df is not None:
            st.error("That file has no columns to read.")
            ingest_ready = False

    backend = active_backend()
    if backend["live"]:
        st.caption(f"Explanation layer: {backend['provider']} ({backend['model']}) ✓")
    else:
        st.caption(
            "Explanation layer: offline mode. Set GEMINI_API_KEY (Gemini) or "
            "ANTHROPIC_API_KEY (Claude) to use a live model."
        )

    run = st.button("Run analysis", type="primary", disabled=not ingest_ready)


@st.cache_data(show_spinner=False)
def _run(old_p, new_p, pdf_p, bom_df, old_l, new_l):
    return run_pipeline(old_p, new_p, pdf_p, bom_df, old_l, new_l)


if (run or "results" not in st.session_state) and ingest_ready:
    bom_df = clean_bom_df if clean_bom_df is not None else pd.read_csv(defaults["bom"])
    with st.spinner("Loading, diffing, matching, recomputing, explaining…"):
        results = _run(
            defaults["defra_old"],
            defaults["defra_new"],
            defaults["changes_pdf"],
            bom_df,
            old_label,
            new_label,
        )
        st.session_state["results"] = results
        st.session_state["set_aside"] = set_aside

if "results" not in st.session_state:
    st.info("Upload a file, confirm your columns in the sidebar, then click Run analysis.")
    st.stop()

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
        "⚠️ The footprint increased. This would **breach a flat baseline**. "
        "Flag for review against active targets (e.g. SBTi)."
    )
else:
    st.success("Footprint did not increase against a flat baseline.")

ds = results.get("diff_stats")
if ds:
    relabels_n = ds.get("relabels", 0)
    relabel_note = (
        f" · {relabels_n} paired as relabels "
        f"({ds.get('added_net', ds['added'])} genuinely new, "
        f"{ds.get('removed_net', ds['removed'])} genuinely removed)"
        if relabels_n
        else ""
    )
    st.caption(
        f"Version scan: {ds['flagged']} factors moved past DEFRA thresholds across "
        f"{ds['joined']} present in both years · {ds['added']} added, "
        f"{ds['removed']} removed{relabel_note}."
    )

groups = results.get("relabel_groups")
if groups is not None and not groups.empty:
    n_pairs = int(groups["n_variants"].sum())
    with st.expander(
        f"Relabels paired ({n_pairs} renamed factors in {len(groups)} families)"
    ):
        st.caption(
            "Same factor, renamed across versions, grouped into rename families so "
            "they do not read as real movement. Only high-confidence matches (same "
            "unit and scope) are paired; anything unclear stays added/removed rather "
            "than guessed. Value movement is a range across the family, never a "
            "single figure standing in for many."
        )
        st.dataframe(
            groups[
                ["old_name", "new_name", "scope", "units",
                 "n_variants", "n_material", "movement"]
            ],
            hide_index=True,
        )
        rel_expl = results.get("relabel_explanations") or []
        if rel_expl:
            st.markdown(
                "**Renamed and moved.** These rename families also crossed DEFRA's "
                "materiality threshold, so each is explained once here (grounded the "
                "same way as the flagged factors)."
            )
            for e in rel_expl:
                variants = (
                    f"{e['n_variants']} variants" if e["n_variants"] > 1 else "1 variant"
                )
                header = (
                    f"{e['old_name']} → {e['new_name']}  ·  {e['scope']}  ·  "
                    f"{variants} ({e['units']})"
                )
                with st.expander(header):
                    st.markdown(f"**How the values moved.** {e['value_movement']}")
                    st.markdown(f"**Why it changed.** {e['plain_english_reason']}")
                    st.markdown(f"**Methodology note.** {e['methodology_note']}")
                    st.markdown(f"**Target impact.** {e['target_impact_flag']}")
                    st.caption(f"retrieval relevance score: {e['retrieval_score']}")

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
    "Ordered by how much each change moved this product's footprint (largest "
    "first). Grounded strictly in the DEFRA changes notes (a Major Changes PDF "
    "if provided, otherwise the workbook's 'What's new' sheet). Where the notes "
    "are silent, the tool says so instead of inventing a reason."
)
if not results["explanations"]:
    st.write("No flagged, footprint-relevant factor changes.")
for e in results["explanations"]:
    imp = e.get("footprint_impact")
    imp_txt = f"  ·  {imp:+.3g} kg impact" if imp is not None else ""
    header = (
        f"{e['activity']}  ·  {e['scope']}  ·  "
        f"{e['kg_co2e_old']:g} → {e['kg_co2e_new']:g}  ({e['pct_change']:+.1f}%)"
        f"{imp_txt}"
    )
    with st.expander(header):
        if imp is not None:
            share = e.get("footprint_impact_pct")
            share_txt = f" ({share:+.1f}% of the total change)" if share is not None else ""
            st.markdown(f"**Impact on your footprint.** {imp:+,.4f} kg CO₂e{share_txt}.")
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

# --- Rows set aside from the uploaded file (before matching) ---
aside = st.session_state.get("set_aside") or []
if aside:
    st.subheader("Rows set aside from your file (never guessed)")
    st.caption(
        "These lines were skipped because a required value was missing or "
        "unreadable (no item name, no unit, or a blank/garbled quantity). Fix "
        "them in your file and re-upload to include them."
    )
    st.dataframe(
        pd.DataFrame(aside)[["row_number", "line_item", "reason"]],
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
