"""
app.py - single-page Streamlit dashboard for the EF Version Explainer.

Run:  streamlit run app.py

The sidebar is SETUP only: which two DEFRA workbooks, and the inventory file
plus the column confirmation. The main canvas is the answer, in the order a
reader actually needs it:

    Result -> Confidence -> Movers -> Explanations -> Export

Confidence comes second on purpose. The trust gate has to arrive before the
conclusion is acted on, not two sections after it: a footprint computed over 85%
of a bill of materials is a different claim from one computed over all of it, and
the reader deserves to know that while they are still looking at the number.

The Run control lives in the main canvas rather than the sidebar. Below 768px
Streamlit collapses the sidebar and takes every input with it, which left the app
looking read-only (defect A-09). Moving the one action out of the thing that
disappears is the fix that survives the collapse.

All visual decisions come from src/ui/ (tokens, components, formatting). This
file calls run_pipeline exactly as it always did: no pipeline, matching, diff or
explanation logic changes here.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load a local .env (git-ignored) so GEMINI_API_KEY / ANTHROPIC_API_KEY are
# picked up automatically. Optional - no-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

from paths import resolve_paths          # noqa: E402
from pipeline import run_pipeline         # noqa: E402
from report import build_markdown_report  # noqa: E402
from explain import active_backend, NO_REASON  # noqa: E402
from ingest import read_table, guess_mapping, build_inventory  # noqa: E402
from auth import sign_in_available, current_user, approval  # noqa: E402
from matching import DEFAULT_THRESHOLD    # noqa: E402
from ui import inject_styles              # noqa: E402
from ui.components import (               # noqa: E402
    SEMANTIC_TABLE_MAX_ROWS,
    alert,
    badge,
    definitions,
    disclosure,
    esc,
    movement,
    section,
    stat_row,
    table,
    write,
)
from ui.format import direction, kg, sig_figs, signed_pct  # noqa: E402

st.set_page_config(page_title="EF Version Explainer", layout="wide")

# The owned design layer (src/ui/). Streamlit's own chrome is themed by
# .streamlit/config.toml; this adds the tokens and the accessibility fixes the
# front-end audit measured. Must come before anything is rendered.
inject_styles()

# Coverage below this is reported as an incomplete answer rather than a clean
# one. Stating the bar is the point: an unqualified total over 85% of a bill of
# materials is the kind of quiet overclaim this tool exists to avoid.
COVERAGE_BAR = 95.0


@st.cache_data(show_spinner=False)
def _read_raw(file_bytes, file_name):
    """Read an uploaded .csv/.xlsx into a raw DataFrame (cached on its bytes)."""
    import io

    bio = io.BytesIO(file_bytes)
    bio.name = file_name  # read_table picks the reader from the extension
    return read_table(bio)


def show_table(df, caption, columns=None, **kwargs):
    """Render a table, semantic by default.

    Below SEMANTIC_TABLE_MAX_ROWS rows a real <table> wins on every count: it can
    be read aloud, selected, searched and printed. Above it, Streamlit's
    virtualised grid is genuinely the better tool, so it stays the default and
    the accessible version moves behind a toggle rather than disappearing.
    """
    if len(df) <= SEMANTIC_TABLE_MAX_ROWS:
        write(table(df, caption, columns=columns, **kwargs))
        return

    st.caption(caption)
    if st.toggle("Accessible, printable version", key=f"semantic:{caption}"):
        write(table(df, caption, columns=columns, **kwargs))
    else:
        st.dataframe(
            df[list(columns)] if columns else df,
            width="stretch",
            hide_index=True,
        )


def review_sentence(row):
    """Say in words why a line was held back, never in a bare score.

    "below_threshold" means nothing was assumed. That is the no-guess rule
    working, so it is written as a sentence a client can read rather than as a
    number they have to interpret.
    """
    score = row.get("match_score")
    method = row.get("match_method")
    if method == "below_threshold":
        return (
            f"Best match scored {sig_figs(score, 3)}, below the "
            f"{sig_figs(DEFAULT_THRESHOLD, 2)} confidence threshold, so nothing was assumed."
        )
    if method == "none":
        return "No candidate factor shares this unit, so nothing was assumed."
    return f"Held for review (match method: {method})."


# ===========================================================================
# Sidebar: setup only
# ===========================================================================

defaults = resolve_paths()

# --- Who's here, and may they use the paid AI explanations? ---
# The tool is open to everyone on the free offline explainer. The AI-written
# explanations cost API money, so they sit behind Google sign-in + an approved
# list. When no sign-in provider is configured (local dev / demo), we keep the
# old behaviour: the API key, if set, drives the explainer for everyone.
signin_on = sign_in_available()
user = current_user() if signin_on else None
appr = approval(user["email"]) if user else {"allowed": False, "reason": "not-signed-in"}
use_ai = True if not signin_on else appr["allowed"]

with st.sidebar:
    if signin_on:
        st.header("Account")
        if user:
            st.write(f"Signed in as **{user['name'] or user['email']}**")
            if appr["allowed"] and appr["reason"] == "open":
                st.warning(
                    "No approved list is set, so every signed-in user can spend "
                    "the API key. Add emails under [access] in your secrets to "
                    "lock this down before sharing widely."
                )
            elif appr["allowed"]:
                st.success("You have access to AI explanations.")
            else:
                st.info(
                    "You're on the free offline explanations. Ask the owner to "
                    "add your email for AI-written explanations."
                )
            if st.button("Sign out"):
                st.logout()
        else:
            st.write(
                "Free to use. Sign in with Google to unlock AI-written, "
                "client-ready explanations."
            )
            if st.button("Sign in with Google", type="primary"):
                st.login()
        st.divider()

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
    uploaded = st.file_uploader(
        "Inventory file (.csv or .xlsx)",
        type=["csv", "xlsx"],
        help="Your bill of materials. Column names do not need to match anything.",
    )

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

    backend = active_backend(force_offline=not use_ai)
    if backend["live"]:
        st.caption(f"Explanation layer: {backend['provider']} ({backend['model']}), full AI")
    elif signin_on and not user:
        st.caption("Explanation layer: free offline mode. Sign in to unlock AI explanations.")
    elif signin_on and user and not appr["allowed"]:
        st.caption("Explanation layer: free offline mode. Account not approved for AI yet.")
    else:
        st.caption(
            "Explanation layer: offline mode. Set GEMINI_API_KEY (Gemini) or "
            "ANTHROPIC_API_KEY (Claude) to use a live model."
        )


# ===========================================================================
# Main canvas
# ===========================================================================

st.title("Emission-Factor Version Explainer")
st.caption(
    "Compare two annual DEFRA GHG conversion-factor releases, recompute a "
    "product's footprint under each, and explain what changed, grounded in the "
    "official DEFRA changes report."
)

# --- Action bar (A-09) ------------------------------------------------------
# The one commit control, in the canvas, carrying run state. It stays reachable
# at every width because it is not inside the sidebar that auto-collapses.
action_left, action_right = st.columns([1, 3])
with action_left:
    run = st.button("Run analysis", type="primary", disabled=not ingest_ready, width="stretch")
run_state = action_right.empty()


@st.cache_data(show_spinner=False)
def _run(old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai):
    return run_pipeline(old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai=use_ai)


# Recompute when the user clicks Run, on first load, OR when the explainer tier
# changed (e.g. they just signed in and now qualify for AI). Both tiers are
# cached, so toggling back and forth is instant and never re-spends the key.
tier_changed = st.session_state.get("results_use_ai") != use_ai
if (run or "results" not in st.session_state or tier_changed) and ingest_ready:
    run_state.markdown(badge("Running", "neutral"), unsafe_allow_html=True)
    bom_df = clean_bom_df if clean_bom_df is not None else pd.read_csv(defaults["bom"])
    with st.spinner("Loading, diffing, matching, recomputing, explaining..."):
        results = _run(
            defaults["defra_old"],
            defaults["defra_new"],
            defaults["changes_pdf"],
            bom_df,
            old_label,
            new_label,
            use_ai,
        )
        st.session_state["results"] = results
        st.session_state["set_aside"] = set_aside
        st.session_state["results_use_ai"] = use_ai

if "results" not in st.session_state:
    run_state.markdown(badge("Ready", "neutral"), unsafe_allow_html=True)
    st.info("Upload a file, confirm your columns in the sidebar, then click Run analysis.")
    st.stop()

run_state.markdown(badge("Complete", "done"), unsafe_allow_html=True)

results = st.session_state["results"]
s = results["summary"]
labels = results["labels"]


# --- 1. Result --------------------------------------------------------------
# One card, one answer. The panel's green means "the run completed and this is
# the answer", not "good news", which is why the direction of travel lives
# inside it as a glyph and a word and the baseline judgement is a separate
# message below.
write(section("Result", caption=(
    f"Your product's footprint under {labels['old']} and under {labels['new']}, "
    "recomputed from the same bill of materials."
)))

pct = s["pct_delta"]
absolute = (s["total_new"] or 0) - (s["total_old"] or 0)
way = direction(absolute, rose="rose", fell="fell", flat="did not change")
coverage = s["coverage_pct"]
partial = coverage < COVERAGE_BAR

if pct is None:
    change_words = "The change could not be computed."
else:
    heavier = "heavier" if absolute > 0 else "lighter"
    change_words = (
        f"{way['word'].capitalize()} {abs(pct):.2f}%, "
        f"{sig_figs(abs(absolute), 3)} kg {heavier}."
        if absolute
        else "No change between the two versions."
    )

coverage_words = (
    f"Coverage {coverage}%, below the {COVERAGE_BAR:.0f}% bar, so this total is "
    "incomplete and should be read as a partial answer."
    if partial
    else f"Coverage {coverage}%, at or above the {COVERAGE_BAR:.0f}% bar."
)

write(
    f'<div class="panel{" panel--partial" if partial else ""}">'
    f'<div class="lab">Product footprint</div>'
    f'<div class="fig tnum">{sig_figs(s["total_old"])} to {sig_figs(s["total_new"])}</div>'
    f'<div class="sub">kg CO2e &nbsp; '
    f'{movement(absolute, way["glyph"], way["word"], figure=signed_pct(pct) if pct is not None else "")}'
    f"</div>"
    f'<div class="base">{change_words} {coverage_words}</div>'
    "</div>"
)

# The baseline judgement is a SEPARATE assessment, not the colour of the panel.
if results["context"].get("breaches_baseline"):
    write(alert(
        "The footprint increased, so it would breach a flat baseline. Flag for "
        "review against any active target (for example SBTi).",
        title="Assessment",
    ))
else:
    write(alert(
        "The footprint did not increase, so it stays within a flat baseline.",
        title="Assessment",
    ))


# --- 2. Confidence ----------------------------------------------------------
# The trust gate, before the conclusion gets acted on.
write(section("Confidence", caption=(
    "What matched, what did not, and what was deliberately left for a human. "
    "Nothing below the confidence threshold is ever assumed."
)))

review = results["matched_df"][results["matched_df"]["needs_review"]]
aside = st.session_state.get("set_aside") or []
matched_lines = len(results["matched_df"]) - len(review)

write(stat_row([
    (f"{coverage}%", f"Coverage ({matched_lines} of {len(results['matched_df'])} lines)"),
    (f"{int(results['diff_df']['flagged'].sum())}", "Factors past DEFRA thresholds"),
    (f"{len(review)}", "Held for review, never guessed"),
    (f"{len(aside)}", "Rows set aside from your file"),
]))

if review.empty:
    write(alert("Every line in your inventory matched with confidence.", kind="none"))
else:
    held = review.copy()
    held["reason"] = held.apply(review_sentence, axis=1)
    write(disclosure(
        "Lines held for review",
        # The yellow tint exists precisely for this state. Holding a line back is
        # the no-guess rule working, not a failure, so it must not borrow red
        # (which means error here) or grey (which also means inactive).
        f'<p>{badge("Held for review", "review")} '
        "Nothing below the confidence threshold was assumed. Each line needs a "
        "human to confirm the right DEFRA activity, or to say there isn't one.</p>"
        + table(
            held,
            caption="Inventory lines that did not match a DEFRA activity with confidence",
            columns=["line_item", "unit", "match_score", "reason"],
            numeric_cols=["match_score"],
        ),
        count=len(held),
        open_by_default=True,
    ))

if aside:
    write(disclosure(
        "Rows set aside from your file",
        "<p class=\"caption\">These lines were skipped before matching because a "
        "required value was missing or unreadable (no item name, no unit, or a "
        "blank or garbled quantity). Fix them in your file and re-upload to "
        "include them.</p>"
        + table(
            pd.DataFrame(aside),
            caption="Rows skipped before matching",
            columns=["row_number", "line_item", "reason"],
        ),
        count=len(aside),
    ))


# --- 3. Movers --------------------------------------------------------------
write(section("Movers", caption=(
    "Which factors moved, and which of your own lines those movements actually "
    "shifted. Renames are paired separately so they do not read as real movement."
)))

ds = results.get("diff_stats")
if ds:
    relabels_n = ds.get("relabels", 0)
    relabel_note = (
        f" {relabels_n} were paired as relabels, leaving "
        f"{ds.get('added_net', ds['added'])} genuinely new and "
        f"{ds.get('removed_net', ds['removed'])} genuinely removed."
        if relabels_n
        else ""
    )
    st.caption(
        f"Version scan: {ds['flagged']} factors moved past DEFRA thresholds across "
        f"{ds['joined']} present in both years. {ds['added']} added, "
        f"{ds['removed']} removed.{relabel_note}"
    )

st.markdown("### Biggest contributors to the change")
top = results["top_delta"]
if top is not None and not top.empty:
    show_table(
        top,
        "Your inventory lines, largest change first",
        columns=["line_item", "factor_old", "factor_new", "co2e_old", "co2e_new", "line_delta"],
        numeric_cols=["factor_old", "factor_new", "co2e_old", "co2e_new"],
        direction_cols=["line_delta"],
    )
else:
    write(alert("No computable movers.", kind="none"))

groups = results.get("relabel_groups")
if groups is not None and not groups.empty:
    n_pairs = int(groups["n_variants"].sum())
    body = (
        '<p class="caption">Same factor, renamed across versions, grouped into '
        "rename families so they do not read as real movement. Only "
        "high-confidence matches (same unit and scope) are paired; anything "
        "unclear stays added or removed rather than guessed. Value movement is a "
        "range across the family, never a single figure standing in for many.</p>"
        + table(
            groups,
            caption="DEFRA renames, grouped into families",
            columns=["old_name", "new_name", "scope", "units", "n_variants",
                     "n_material", "movement"],
            numeric_cols=["n_variants", "n_material"],
        )
    )

    rel_expl = results.get("relabel_explanations") or []
    for e in rel_expl:
        variants = f"{e['n_variants']} variants" if e["n_variants"] > 1 else "1 variant"
        body += disclosure(
            f"{e['old_name']} to {e['new_name']} ({e['scope']}, {variants}, {e['units']})",
            definitions([
                ("How the values moved", esc(e["value_movement"])),
                ("Why it changed", esc(e["plain_english_reason"])),
                ("Methodology note", esc(e["methodology_note"])),
                ("Target impact", esc(e["target_impact_flag"])),
            ]),
        )

    write(disclosure(
        f"Relabels paired ({n_pairs} renamed factors in {len(groups)} families)",
        body,
    ))


# --- 4. Explanations --------------------------------------------------------
write(section("Explanations", caption=(
    "Ordered by how much each change moved this product's footprint, largest "
    "first. Grounded strictly in the DEFRA changes notes (a Major Changes PDF if "
    "provided, otherwise the workbook's 'What's new' sheet). Where the notes are "
    "silent, the tool says so instead of inventing a reason."
)))

# Tell the reader which tier they're looking at, and offer the unlock if free.
showing_ai = bool(st.session_state.get("results_use_ai")) and active_backend()["live"]
if showing_ai:
    st.success("Showing full AI-written explanations.")
elif signin_on and not user:
    st.info(
        "These are the free offline explanations (official DEFRA extracts, not "
        "model-written). Sign in with Google in the sidebar to unlock AI-written, "
        "client-ready explanations."
    )
elif signin_on and user and not appr["allowed"]:
    st.info(
        "These are the free offline explanations. Your account isn't approved for "
        "AI explanations yet, ask the owner to add your email."
    )

if not results["explanations"]:
    write(alert("No flagged, footprint-relevant factor changes.", kind="none"))

for e in results["explanations"]:
    grounded = e["plain_english_reason"].strip() != NO_REASON
    status = badge("Cited", "cited") if grounded else badge("Not explained", "silent")

    impact = e.get("footprint_impact")
    share = e.get("footprint_impact_pct")
    rows = []
    if impact is not None:
        share_txt = f" ({share:+.1f}% of the total change)" if share is not None else ""
        rows.append(("Impact on your footprint", f"{kg(impact)}{share_txt}."))
    rows += [
        ("Why it changed", f"{status} {esc(e['plain_english_reason'])}"),
        ("Methodology note", esc(e["methodology_note"])),
        ("Target impact", esc(e["target_impact_flag"])),
        ("Retrieval relevance", esc(e["retrieval_score"])),
    ]

    impact_txt = f", {kg(impact)} impact" if impact is not None else ""
    write(disclosure(
        f"{e['activity']} ({e['scope']}): "
        f"{sig_figs(e['kg_co2e_old'])} to {sig_figs(e['kg_co2e_new'])}, "
        f"{signed_pct(e['pct_change'])}{impact_txt}",
        definitions(rows),
    ))


# --- 5. Export --------------------------------------------------------------
write(section("Export", caption=(
    "The report as a file you can keep, attach to a client folder, or diff "
    "against next year's run."
)))

report_md = build_markdown_report(results)
st.download_button(
    "Download report (Markdown)",
    data=report_md,
    file_name="ef_version_report.md",
    mime="text/markdown",
)
