"""
app.py - the EF Version Explainer dashboard.

Run:  streamlit run app.py

The page is an app shell, not a document: a masthead that says what this is and
which two DEFRA releases it is comparing, a setup flow, and then the report
behind a sticky section nav.

THE LANDING SURFACE IS THE COMPARISON, NOT A FORM.

Section 1 is an interactive, filterable table of every factor that changed
between the two releases. It needs no upload, no sign-in and no API key,
because loading two workbooks and joining them is arithmetic on local files
(pipeline.compare_versions). Before this, the diff was computed on every run
and then almost entirely thrown away: the page showed only the handful of rows
that touched a bill of materials, so the single most reusable thing the tool
produces was invisible unless you had already uploaded a product. A visitor also
arrived to a spinner, because the script ran the whole pipeline on a sample
product unasked. It no longer does. Nothing heavier than the diff happens until
someone presses a button.

Setup lives in the MAIN canvas, in three numbered steps. Two reasons. Below
768px Streamlit collapses the sidebar and takes every input with it, which left
the app looking read-only (defect A-09). And a first-time visitor was previously
handed a blank page and the instruction "upload a file, confirm your columns in
the sidebar, then click Run analysis", which is a set of directions rather than
a flow. The sidebar now carries account and settings only.

The page reads in the order a reader actually needs it:

    Compare releases -> Result -> Confidence -> Movers -> Explanations -> Export

Confidence comes second on purpose. The trust gate has to arrive before the
conclusion is acted on, not two sections after it: a footprint computed over 85%
of a bill of materials is a different claim from one computed over all of it, and
the reader deserves to know that while they are still looking at the number.

All visual decisions come from src/ui/ (tokens, components, formatting). This
file calls run_pipeline exactly as it always did: no pipeline, matching, diff or
explanation logic changes here.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as st_components

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load a local .env (git-ignored) so GEMINI_API_KEY / ANTHROPIC_API_KEY are
# picked up automatically. Optional - no-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

from paths import resolve_paths          # noqa: E402
from pipeline import (                     # noqa: E402
    cited_reasons,
    compare_versions,
    load_snapshot,
    run_pipeline,
)
from diff import STATUS_LABELS, filter_changes, with_status_label  # noqa: E402
from explain import active_backend, NO_REASON  # noqa: E402
from export import (                       # noqa: E402
    completeness_checklist,
    export_pack,
    run_identity,
    to_zip,
    unresolved,
)
from ingest import read_table, guess_mapping, build_inventory  # noqa: E402
from auth import sign_in_available, current_user, approval  # noqa: E402
from matching import DEFAULT_THRESHOLD    # noqa: E402
from ui import inject_styles              # noqa: E402
from ui.components import (               # noqa: E402
    SEMANTIC_TABLE_MAX_ROWS,
    alert,
    badge,
    checklist as checklist_block,
    definitions,
    disclosure,
    esc,
    explanation_head,
    fact_bar,
    file_chip,
    masthead,
    meter,
    movement,
    section,
    source_quote,
    scrollspy,
    stat_row,
    step,
    subnav,
    table,
    verdict_card,
    write,
)
from ui.format import direction, human_column, kg, plural, sig_figs, signed_pct  # noqa: E402

st.set_page_config(page_title="EF Version Explainer", layout="wide")

# The owned design layer (src/ui/). Streamlit's own chrome is themed by
# .streamlit/config.toml; this adds the tokens and the accessibility fixes the
# front-end audit measured. Must come before anything is rendered.
inject_styles()

# Coverage below this is reported as an incomplete answer rather than a clean
# one. Stating the bar is the point: an unqualified total over 85% of a bill of
# materials is the kind of quiet overclaim this tool exists to avoid.
COVERAGE_BAR = 95.0

# How many "why it changed" cards the front door renders before asking the
# reader to narrow the filters. All 67 real flagged factors would be a wall of
# disclosures on a cold visit; the biggest movers (the table is already sorted
# by them) are what a reader actually wants first.
REASONS_MAX = 25

# Section 1 exists on every visit. The rest exist once a report has been run,
# so the nav never offers a link to a section that is not on the page.
COMPARE_SECTION = [("s-compare", "Compare releases")]
REPORT_SECTIONS = [
    ("s-result", "Result"),
    ("s-confidence", "Confidence"),
    ("s-movers", "Movers"),
    ("s-explanations", "Explanations"),
    ("s-export", "Export"),
]


@st.cache_data(show_spinner=False)
def _read_raw(file_bytes, file_name):
    """Read an uploaded .csv/.xlsx into a raw DataFrame (cached on its bytes)."""
    import io

    bio = io.BytesIO(file_bytes)
    bio.name = file_name  # read_table picks the reader from the extension
    return read_table(bio)


def show_table(df, caption, columns=None, numeric_cols=(), direction_cols=(),
               labels=None, **kwargs):
    """Render a table, semantic by default.

    Below SEMANTIC_TABLE_MAX_ROWS rows a real <table> wins on every count: it can
    be read aloud, selected, searched and printed. Above it, Streamlit's
    virtualised grid is genuinely the better tool, so it stays the default. But
    it used to hand that grid the raw internal names (kg_co2e_old, pct_change)
    with no formatting, which is not what a reader typed into the filters above
    it. It now gets the same words and number formats as the semantic table:
    ui.format.human_column for the headings, sig_figs' "%.4g" for the numeric
    columns, signed_pct's "%+.1f%%" for the direction columns (every one this
    function is asked to render today is a percent change; a future non-percent
    direction column would need its own format rather than inheriting this one).

    `labels` overrides human_column for specific internal names, so a caller
    whose column is literally "old value" / "new value" can show "Factor
    (2025)" / "Factor (2026)" instead of a fixed, versionless heading.
    """
    if len(df) <= SEMANTIC_TABLE_MAX_ROWS:
        write(table(df, caption, columns=columns, numeric_cols=numeric_cols,
                    direction_cols=direction_cols, **kwargs))
        return

    st.caption(caption)
    if st.toggle("Accessible, printable version", key=f"semantic:{caption}"):
        write(table(df, caption, columns=columns, numeric_cols=numeric_cols,
                    direction_cols=direction_cols, **kwargs))
        return

    cols = list(columns) if columns else list(df.columns)
    overrides = labels or {}

    def _label(c):
        return overrides.get(c, human_column(c))

    shown_df = df[cols].rename(columns={c: _label(c) for c in cols})

    config = {}
    for c in numeric_cols:
        config[_label(c)] = st.column_config.NumberColumn(_label(c), format="%.4g")
    for c in direction_cols:
        config[_label(c)] = st.column_config.NumberColumn(_label(c), format="%+.1f%%")

    st.dataframe(shown_df, width="stretch", hide_index=True, column_config=config)


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
# Sidebar: account and settings only
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

    st.header("Settings")
    old_label = st.text_input("Older version label", defaults["old_label"])
    new_label = st.text_input("Newer version label", defaults["new_label"])
    st.caption(
        "The names that appear on the report and in every exported file. The "
        "workbooks themselves are read from the data folder."
    )

    st.divider()
    backend = active_backend(force_offline=not use_ai)
    if backend["live"]:
        st.caption(f"Explanations: {backend['provider']} ({backend['model']}), full AI")
    elif signin_on and not user:
        st.caption("Explanations: free offline mode. Sign in to unlock AI explanations.")
    elif signin_on and user and not appr["allowed"]:
        st.caption("Explanations: free offline mode. Account not approved for AI yet.")
    else:
        st.caption(
            "Explanations: offline mode. Set GEMINI_API_KEY (Gemini) or "
            "ANTHROPIC_API_KEY (Claude) to use a live model."
        )


# ===========================================================================
# The shell
# ===========================================================================

has_results = "results" in st.session_state

# The masthead is painted into a slot rather than written straight out, because
# on a first visit the run happens further down this same script: without the
# slot the status tag would still read "Not run yet" beside a finished report.
mast_slot = st.empty()


def paint_masthead(status):
    mast_slot.markdown(
        masthead(
            "EF Version Explainer",
            "DEFRA GHG conversion factors",
            fact_label=f"{old_label} to {new_label}",
            fact_value="Full set, UK",
            status=status,
        ),
        unsafe_allow_html=True,
    )


paint_masthead(("Report ready", "done") if has_results else ("Not run yet", "neutral"))

# The masthead already carries the product name, so the H1 is the JOB, not the
# brand: it is the sentence that tells a first-time visitor what this does.
write(
    '<div class="page-head">'
    "<h1>Compare two DEFRA releases against your product</h1>"
    '<p class="caption">Recompute your footprint under each annual release and '
    "explain what changed, grounded in the official DEFRA changes notes.</p>"
    "</div>"
)

# The nav is painted into a slot for the same reason as the masthead: a visitor
# who presses Run gains five sections further down this same script run, and a
# nav written before that would be missing every one of them.
nav_slot = st.empty()


def paint_nav(with_report):
    nav_slot.markdown(
        subnav(COMPARE_SECTION + (REPORT_SECTIONS if with_report else [])),
        unsafe_allow_html=True,
    )


paint_nav(has_results)


# ===========================================================================
# 1. Compare releases: the landing surface
# ===========================================================================
# No upload, no sign-in, no API key. This is the whole factor register, diffed,
# and it is the first thing on the page because it is the first thing a DEFRA
# practitioner actually wants to look at.

write(section(
    "Compare releases",
    eyebrow="Section 1",
    anchor="s-compare",
    caption=(
        f"Every conversion factor in the {old_label} and {new_label} full sets, "
        "joined on activity and unit. Filter it, sort it, take it away. Renames "
        "are paired, so DEFRA's relabels do not read as new factors."
    ),
))


# persist="disk" so a live parse (the fallback below) is only ever paid once
# PER CONTAINER, not once per session: without it, every visitor after a
# redeploy or a Streamlit Cloud sleep pays the ~15s parse again.
@st.cache_data(show_spinner=False, persist="disk")
def _compare_full(old_p, new_p, old_l, new_l):
    return compare_versions(old_p, new_p, old_l, new_l)


def _register(old_p, new_p, old_l, new_l):
    """Section 1's fast path: the committed snapshot first (well under a
    second), a disk-cached full parse if it is missing or no longer matches
    the workbooks on disk.

    Returns `diff_df` / `diff_stats` either way. Also returns `full`: the
    complete compare_versions() dict when the fallback ran, so a later Run
    click can reuse it instead of parsing both workbooks a second time, or
    None when the snapshot answered, since a snapshot carries only what
    section 1 needs, not df_old / relabels / relabel_groups.
    """
    snap = load_snapshot(old_p, new_p)
    if snap is not None:
        return {"diff_df": snap["diff_df"], "diff_stats": snap["diff_stats"], "full": None}
    full = _compare_full(old_p, new_p, old_l, new_l)
    return {"diff_df": full["diff_df"], "diff_stats": full["diff_stats"], "full": full}


with st.spinner("Reading both DEFRA workbooks and diffing them..."):
    register = _register(
        defaults["defra_old"], defaults["defra_new"], old_label, new_label
    )

all_changes = register["diff_df"]
cstats = register["diff_stats"]

write(fact_bar([
    (f"Factors in {old_label}", f"{cstats['factors_old']:,}"),
    (f"Factors in {new_label}", f"{cstats['factors_new']:,}"),
    ("Past DEFRA thresholds", f"{cstats['flagged']:,}"),
    ("Genuinely new", f"{cstats['added_net']:,}"),
    ("Retired", f"{cstats['removed_net']:,}"),
    ("Renamed", f"{cstats['relabels']:,}"),
]))

# --- The filters ---
# Deliberately five plain controls rather than a query language. Every one of
# them answers a question a consultant actually asks out loud: "what moved in
# scope 3", "did anything to do with steel change", "show me only what breaks
# DEFRA's own materiality bar".
write('<div class="subhead">Filter the comparison</div>')

f1, f2 = st.columns([2, 1], gap="medium")
query = f1.text_input(
    "Search activity or unit",
    placeholder="For example: electricity, steel, HGV, tonne.km",
)
scope_options = sorted(str(s) for s in all_changes["scope"].dropna().unique())
scopes = f2.multiselect("Scope", scope_options, placeholder="All scopes")

f3, f4 = st.columns([1, 1], gap="medium")
status_keys = list(STATUS_LABELS)
statuses = f3.multiselect(
    "What happened to the factor",
    status_keys,
    format_func=lambda key: STATUS_LABELS[key],
    placeholder="Everything",
)
min_pct = f4.slider(
    "Minimum change, either direction (%)", 0.0, 100.0, 0.0, step=0.5,
    help=(
        "Above zero this also hides new and retired factors, which have no "
        "percent change to measure."
    ),
)

material_only = st.toggle(
    "Only factors past DEFRA's own materiality thresholds "
    "(over 5% for scope 1 and 2, over 10% for scope 3)"
)

shown = filter_changes(
    all_changes,
    query=query,
    scopes=scopes,
    statuses=statuses,
    min_pct=min_pct,
    material_only=material_only,
)
# What happened to each factor, in words. Without this, filtering to "New" or
# "Retired" returned rows with n/a in the old/new factor column and nothing on
# screen saying why: a filter you can set but cannot see the result of.
shown = with_status_label(shown)

filtered = len(shown) != len(all_changes)
st.caption(
    f"Showing {len(shown):,} of {len(all_changes):,} factors."
    + (" Clear the filters to see all of them." if filtered else "")
)

if len(shown) == 0:
    write(alert(
        "No factor matches those filters. Widen the search, or clear a filter.",
        kind="none",
    ))
else:
    show_table(
        shown,
        f"DEFRA conversion factors, {old_label} against {new_label}, "
        "largest movement first",
        columns=["activity", "unit", "scope", "status_label", "kg_co2e_old",
                 "kg_co2e_new", "pct_change"],
        numeric_cols=["kg_co2e_old", "kg_co2e_new"],
        direction_cols=["pct_change"],
        labels={
            "kg_co2e_old": f"Factor ({old_label})",
            "kg_co2e_new": f"Factor ({new_label})",
        },
    )
    # The filtered view IS the work product for a lot of visits ("give me every
    # scope 3 factor that moved more than 10%"), so it leaves as a file rather
    # than as something to copy off the screen.
    st.download_button(
        f"Download this view ({len(shown):,} factors, .csv)",
        data=shown.to_csv(index=False).encode("utf-8"),
        file_name="ef_comparison_view.csv",
        mime="text/csv",
    )

    # --- Why these changed, in DEFRA's own words ----------------------------
    # The wedge, on the front door, before any upload. Every flagged factor in
    # the CURRENT filtered view (so the five filters drive this too), quoted
    # from the DEFRA changes notes with no model call: retrieve_citation only,
    # so it costs nothing and reads identically for every visitor. This is
    # VISION.md's "demote the AI to a labelled quoter of DEFRA's verbatim
    # words". The AI-written prose stays in the product report below, behind
    # the existing sign-in tier.
    write("<div class=\"subhead\">Why these changed, in DEFRA's own words</div>"
          "<p class=\"caption\">For every factor above that crossed DEFRA's own "
          "materiality threshold: the DEFRA changes note it is grounded in, "
          "quoted verbatim, or a plain statement that the notes do not cover "
          "it. Nothing here is written by a model.</p>")

    @st.cache_data(show_spinner=False)
    def _reasons(_diff_df, pdf_p, new_p):
        return cited_reasons(_diff_df, pdf_p, new_p)

    reasons_by_key = {
        (r["activity"], r["unit"]): r
        for r in _reasons(all_changes, defaults["changes_pdf"], defaults["defra_new"])
    }

    flagged_shown = shown[shown["flagged"].fillna(False).astype(bool)]
    if len(flagged_shown) == 0:
        write(alert(
            "No factor in this view crossed DEFRA's own materiality threshold.",
            kind="none",
        ))
    else:
        if len(flagged_shown) > REASONS_MAX:
            st.caption(
                f"Showing the {REASONS_MAX} largest of {len(flagged_shown):,}. "
                "Narrow the filters above to reach the others."
            )
        for _, frow in flagged_shown.head(REASONS_MAX).iterrows():
            r = reasons_by_key.get((frow["activity"], frow["unit"]))
            if r is None:
                continue
            status = (
                badge("Cited", "cited") if r["explained"]
                else badge("Not explained", "silent")
            )
            if r["explained"]:
                body = source_quote(
                    r["quote"],
                    f"{r['source']}, {r['heading']}. Retrieval relevance {r['score']}",
                )
            else:
                body = f"<p>{esc(NO_REASON)}</p>"
            write(disclosure(
                f"{r['activity']} ({r['scope']})",
                body,
                summary_html=explanation_head(
                    status,
                    r["activity"],
                    f"{r['scope']} · {sig_figs(r['kg_co2e_old'])} to "
                    f"{sig_figs(r['kg_co2e_new'])} · {signed_pct(r['pct_change'])}",
                ),
            ))


# ===========================================================================
# Setup: three numbered steps, in the canvas
# ===========================================================================

# A transition, not a section: it carries no anchor and is not in the nav, so it
# is a subhead rather than an <h2>. The <h2> ladder on this page means exactly
# "a numbered section the nav can reach", and test_design_system asserts it.
write('<div class="subhead">Now check it against your product</div>'
      '<p class="caption">The comparison above is the whole register. Upload an '
      "inventory and the tool recomputes your own footprint under both releases, "
      "ranks the changes by what they did to your number, and explains them.</p>")

# Once a report exists the setup collapses out of the way, because the answer
# is what the reader came back for. Before that it is the whole page.
setup = st.expander("Set up this run", expanded=not has_results)

with setup:
    # --- Step 1: which two releases ---
    write(step(1, "Versions to compare",
               "Read from your data folder, so there is nothing to upload.",
               state="done"))
    if defaults["using_real_data"]:
        write(alert(
            "Using the real DEFRA full-set workbooks found in your data folder.",
            kind="ok", title="Real data",
        ))
    else:
        write(alert(
            "Using SYNTHETIC demo data. Drop real DEFRA full-set workbooks into "
            "the data folder (for example ghg-conversion-factors-2025-full-set.xlsx "
            "and the 2026 file) to use genuine figures.",
            title="Demo data",
        ))
    st.caption(f"Comparing {old_label} against {new_label}. Rename either in the sidebar.")

    # --- Step 2: the inventory ---
    # clean_bom_df stays None when nothing is uploaded, in which case the sample
    # BOM is used.
    clean_bom_df = None
    set_aside: list = []
    ingest_ready = True  # the built-in sample path is always ready
    raw_df = None

    write(step(2, "Your product inventory",
               "A .csv or .xlsx. Column names do not need to match anything.",
               state="now"))
    uploaded = st.file_uploader(
        "Inventory file (.csv or .xlsx)",
        type=["csv", "xlsx"],
        help="Your bill of materials. Column names do not need to match anything.",
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.caption(
            "No file yet. You can run the built-in sample product to see the whole "
            "report first, then upload your own."
        )
    else:
        try:
            raw_df = _read_raw(uploaded.getvalue(), uploaded.name)
        except Exception as exc:
            write(alert(f"Could not read that file: {exc}", kind="error", title="Unreadable file"))
            raw_df = None
            ingest_ready = False

        if raw_df is not None:
            write(file_chip(
                uploaded.name,
                f"{len(raw_df)} rows, {len(raw_df.columns)} columns",
            ))

    # --- Step 3: confirm the mapping ---
    # A real client file rarely has the exact columns the pipeline needs, so we
    # guess the mapping and let the user confirm or fix it (the no-guess rule,
    # applied at the column level).
    if raw_df is not None and len(raw_df.columns) > 0:
        write(step(3, "Confirm your columns",
                   "We guessed from your headers. Change anything we got wrong.",
                   state="now"))

        cols = [str(c) for c in raw_df.columns]
        guessed, confidence = guess_mapping(cols)

        placeholder = "(select a column)"
        options = [placeholder] + cols

        def _default_index(field):
            g = guessed.get(field)
            return (cols.index(g) + 1) if g in cols else 0

        pick_1, pick_2, pick_3 = st.columns(3)
        sel_item = pick_1.selectbox("Item or material", options, index=_default_index("line_item"))
        sel_qty = pick_2.selectbox("Quantity", options, index=_default_index("quantity"))
        sel_unit = pick_3.selectbox("Unit", options, index=_default_index("unit"))

        mapping = {
            "line_item": None if sel_item == placeholder else sel_item,
            "quantity": None if sel_qty == placeholder else sel_qty,
            "unit": None if sel_unit == placeholder else sel_unit,
        }
        picked = [c for c in mapping.values() if c]
        if len(picked) < 3:
            write(alert("Pick the item, quantity, and unit columns to continue.",
                        kind="review", title="Three columns needed"))
            ingest_ready = False
        elif len(set(picked)) < 3:
            write(alert("Each column can be used once. Pick three different columns.",
                        kind="review", title="Columns repeat"))
            ingest_ready = False
        else:
            clean_bom_df, set_aside = build_inventory(raw_df, mapping)
            if clean_bom_df.empty:
                write(alert("No usable rows after applying that mapping. Check the columns.",
                            kind="error", title="Nothing to read"))
                ingest_ready = False
            else:
                write(alert(
                    f"{len(clean_bom_df)} of {len(raw_df)} rows ready."
                    + (f" {plural(len(set_aside), 'row')} set aside and listed "
                       "in the report." if set_aside else ""),
                    kind="ok", title="Inventory read",
                ))
                write(table(
                    clean_bom_df.head(5),
                    "Preview of the first rows, read with your mapping",
                    columns=["line_item", "quantity", "unit"],
                    numeric_cols=["quantity"],
                ))
    elif raw_df is not None:
        write(alert("That file has no columns to read.", kind="error", title="Empty file"))
        ingest_ready = False


# --- The action bar (A-09) --------------------------------------------------
# The one commit control, in the canvas, so it survives the sidebar collapsing.
# Deliberately NOT in columns: a fixed column ratio that looks tidy at 1440px
# crushes the button into a quarter of a 375px screen, which is the same class
# of mistake as hiding it in the sidebar.
run = st.button(
    "Run analysis" if not has_results else "Run analysis again",
    type="primary",
    disabled=not ingest_ready,
)
st.caption(
    "Runs the whole pipeline: load both workbooks, diff them, match your "
    "inventory, recompute, and explain what moved."
    if ingest_ready
    else "Finish the setup above to run."
)


@st.cache_data(show_spinner=False)
def _run(old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai, _comparison):
    return run_pipeline(
        old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai=use_ai, comparison=_comparison
    )


# Recompute when the user clicks Run, or when the explainer tier changed under
# an existing report (e.g. they just signed in and now qualify for AI). Both
# tiers are cached, so toggling back and forth is instant and never re-spends
# the key.
#
# Deliberately NOT on first load. This used to run the whole pipeline on a
# sample product before the visitor had asked for anything, which meant the
# first thing the app did was make someone wait for an answer about a product
# that is not theirs. The comparison above is what a cold visit lands on now.
tier_changed = "results" in st.session_state and (
    st.session_state.get("results_use_ai") != use_ai
)
if (run or tier_changed) and ingest_ready:
    bom_df = clean_bom_df if clean_bom_df is not None else pd.read_csv(defaults["bom"])
    # Reuse section 1's parse of the two workbooks when it already did the full
    # one (df_old, relabels, relabel_groups; a snapshot alone does not carry
    # those). Otherwise this is the first full parse this session needed, same
    # as before. The leading underscore on _comparison in _run's signature
    # tells Streamlit to skip hashing it: old_p/new_p/old_l/new_l already
    # identify it completely, so trusting the cache key here is not a guess.
    run_comparison = register["full"] or _compare_full(
        defaults["defra_old"], defaults["defra_new"], old_label, new_label
    )
    with st.spinner("Loading, diffing, matching, recomputing, explaining..."):
        results = _run(
            defaults["defra_old"],
            defaults["defra_new"],
            defaults["changes_pdf"],
            bom_df,
            old_label,
            new_label,
            use_ai,
            run_comparison,
        )
        st.session_state["results"] = results
        st.session_state["set_aside"] = set_aside
        st.session_state["results_use_ai"] = use_ai
    paint_masthead(("Report ready", "done"))
    paint_nav(True)

if "results" not in st.session_state:
    write(alert(
        "Run the analysis above to add your own footprint, the coverage check, "
        "and the written explanations. The comparison stays either way. Nothing "
        "is matched or assumed until you run it.",
        title="No product report yet",
    ))
    st.stop()

results = st.session_state["results"]
s = results["summary"]
labels = results["labels"]


# --- 2. Result --------------------------------------------------------------
# One card, one answer. Green is the rail and the tag ("the run completed and
# this is the answer"), never the fill, so the figure stays ink on ground and no
# reader mistakes the panel colour for good news.
write(section(
    "Result",
    eyebrow="Section 2",
    anchor="s-result",
    caption=(
        f"Your product's footprint under {labels['old']} and under {labels['new']}, "
        "recomputed from the same bill of materials."
    ),
))

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
        f"{sig_figs(abs(absolute), 3)} kg {heavier} under {labels['new']}."
        if absolute
        else "No change between the two versions."
    )

review = results["matched_df"][results["matched_df"]["needs_review"]]
aside = st.session_state.get("set_aside") or []
matched_lines = len(results["matched_df"]) - len(review)
flagged_n = int(results["diff_df"]["flagged"].sum())
breaches = bool(results["context"].get("breaches_baseline"))

write(verdict_card(
    "Product footprint",
    f"{sig_figs(s['total_old'])} to {sig_figs(s['total_new'])}",
    movement(absolute, way["glyph"], way["word"],
             figure=signed_pct(pct, 2) if pct is not None else ""),
    note=change_words,
    partial=partial,
    pair=((labels["old"], sig_figs(s["total_old"])),
          (labels["new"], sig_figs(s["total_new"]))),
    status=("Partial answer", "review") if partial else ("Complete", "done"),
    facts=[
        ("Coverage", f"{coverage}%"),
        ("Lines", f"{matched_lines} of {len(results['matched_df'])} matched"),
        ("Factors moved", f"{flagged_n} past threshold"),
        ("Baseline", "Breached" if breaches else "Within a flat baseline"),
    ],
))

# The baseline judgement is a SEPARATE assessment, not the colour of the panel.
coverage_words = (
    f" Coverage is {coverage}%, below the {COVERAGE_BAR:.0f}% bar, so read this "
    "total as a partial answer."
    if partial
    else f" Coverage is {coverage}%, at or above the {COVERAGE_BAR:.0f}% bar."
)
if breaches:
    write(alert(
        "The footprint increased, so it would breach a flat baseline. Flag for "
        "review against any active target (for example SBTi)." + coverage_words,
        kind="review",
        title="Assessment",
    ))
else:
    write(alert(
        "The footprint did not increase, so it stays within a flat baseline."
        + coverage_words,
        title="Assessment",
    ))


# --- 3. Confidence ----------------------------------------------------------
# The trust gate, before the conclusion gets acted on.
write(section(
    "Confidence",
    eyebrow="Section 3",
    anchor="s-confidence",
    caption=(
        "What matched, what did not, and what was deliberately left for a human. "
        "Nothing below the confidence threshold is ever assumed."
    ),
))

coverage_note = (
    "Below the bar, so this total is incomplete. Lines were held back rather "
    "than guessed, which is the rule working, not a failure."
    if partial
    else "At or above the bar, so the total covers the inventory as read."
)
write(
    '<div class="card">'
    '<div class="eyebrow">Coverage of your inventory</div>'
    + meter(
        coverage,
        COVERAGE_BAR,
        f"{coverage}%",
        beside=f"{matched_lines} of {len(results['matched_df'])} lines",
    )
    + f'<p class="caption">{esc(coverage_note)}</p>'
    "</div>"
)

write(stat_row([
    (f"{flagged_n}", "Factors past DEFRA thresholds"),
    (f"{len(review)}", "Held for review, never guessed"),
    (f"{len(aside)}", "Rows set aside from your file"),
    (f"{results.get('diff_stats', {}).get('joined', 0)}", "Factors present in both years"),
]))

if review.empty:
    write(alert("Every line in your inventory matched with confidence.", kind="ok",
                title="Nothing held back"))
else:
    held = review.copy()
    held["reason"] = held.apply(review_sentence, axis=1)
    write(disclosure(
        "Lines held for review",
        # The yellow tint exists precisely for this state. Holding a line back is
        # the no-guess rule working, not a failure, so it must not borrow red
        # (which means error here) or grey (which also means inactive).
        "<p class=\"caption\">Nothing below the confidence threshold was assumed. "
        "Each line needs a human to confirm the right DEFRA activity, or to say "
        "there isn't one.</p>"
        + table(
            held,
            caption="Inventory lines that did not match a DEFRA activity with confidence",
            columns=["line_item", "unit", "match_score", "reason"],
            numeric_cols=["match_score"],
        ),
        count=len(held),
        open_by_default=True,
        summary_html=(
            badge("Held for review", "review")
            + f'<span class="disc-title">{plural(len(held), "inventory line")} '
            + ("needs" if len(held) == 1 else "need")
            + " a human</span>"
        ),
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


# --- 4. Movers --------------------------------------------------------------
write(section(
    "Movers",
    eyebrow="Section 4",
    anchor="s-movers",
    caption=(
        "Which factors moved, and which of your own lines those movements actually "
        "shifted. Renames are paired separately so they do not read as real movement."
    ),
))

ds = results.get("diff_stats")
if ds:
    relabels_n = ds.get("relabels", 0)
    write(fact_bar([
        ("In both years", ds["joined"]),
        ("Past threshold", ds["flagged"]),
        ("Genuinely new", ds.get("added_net", ds["added"])),
        ("Paired as renames", relabels_n),
    ]))

write('<div class="subhead">Biggest contributors to the change</div>')
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
        summary_html=(
            badge("Renames", "silent")
            + f'<span class="disc-title">{n_pairs} renamed factors, grouped into '
            f"{len(groups)} families</span>"
            '<span class="disc-meta">not counted as movement</span>'
        ),
    ))


# --- 5. Explanations --------------------------------------------------------
write(section(
    "Explanations",
    eyebrow="Section 5",
    anchor="s-explanations",
    caption=(
        "Ordered by how much each change moved this product's footprint, largest "
        "first. Grounded strictly in the DEFRA changes notes (a Major Changes PDF if "
        "provided, otherwise the workbook's 'What's new' sheet). Where the notes are "
        "silent, the tool says so instead of inventing a reason."
    ),
))

# Tell the reader which tier they're looking at, and offer the unlock if free.
showing_ai = bool(st.session_state.get("results_use_ai")) and active_backend()["live"]
if showing_ai:
    write(alert("Showing full AI-written explanations.", kind="ok",
                title="AI explanations"))
elif signin_on and not user:
    write(alert(
        "These are the free offline explanations (official DEFRA extracts, not "
        "model-written). Sign in with Google in the sidebar to unlock AI-written, "
        "client-ready explanations.",
        title="Free tier",
    ))
elif signin_on and user and not appr["allowed"]:
    write(alert(
        "These are the free offline explanations. Your account isn't approved for "
        "AI explanations yet, ask the owner to add your email.",
        title="Free tier",
    ))

if not results["explanations"]:
    write(alert("No flagged, footprint-relevant factor changes.", kind="none"))

for e in results["explanations"]:
    grounded = e["plain_english_reason"].strip() != NO_REASON
    status = badge("Cited", "cited") if grounded else badge("Not explained", "silent")

    impact = e.get("footprint_impact")
    share = e.get("footprint_impact_pct")

    reason = f"<p>{esc(e['plain_english_reason'])}</p>"
    # The DEFRA passage the explanation stands on, set as a source rather than
    # as our own prose. Absent when nothing cleared the retrieval bar, in which
    # case the reason above already says so (DECISIONS D2).
    note = (e.get("citation") or {}).get("note") or {}
    quote = (note.get("quote") or "").strip()
    if grounded and quote:
        where = note.get("source") or "DEFRA changes notes"
        if note.get("heading"):
            where = f"{where}, {note['heading']}"
        reason += source_quote(quote, f"{where}. Retrieval relevance {e['retrieval_score']}")

    rows = [("Why it changed", reason)]
    rows += [
        ("Methodology note", esc(e["methodology_note"])),
        ("Target impact", esc(e["target_impact_flag"])),
    ]

    # abs() on purpose: the sign is already carried by the kg figure beside it,
    # and "-99.3% of the total change" reads as if the line worked against the
    # movement when it IS the movement.
    share_txt = f"{abs(share):.1f}% of the total change" if share is not None else None
    write(disclosure(
        f"{e['activity']} ({e['scope']})",
        definitions(rows),
        summary_html=explanation_head(
            status,
            e["activity"],
            f"{e['scope']} · {sig_figs(e['kg_co2e_old'])} to "
            f"{sig_figs(e['kg_co2e_new'])} · {signed_pct(e['pct_change'])}",
            impact=kg(impact) if impact is not None else None,
            impact_note=share_txt,
        ),
    ))


# --- 6. Export --------------------------------------------------------------
write(section(
    "Export",
    eyebrow="Section 6",
    anchor="s-export",
    caption=(
        "Four files from one run, all stamped with the same run id: a workbook, the "
        "raw JSON, the Markdown report, and a print-ready memo you can print to PDF "
        "from your browser. Anything still unresolved is written into the front "
        "matter of every one of them."
    ),
))

who, before = st.columns([1, 1], gap="medium")

with who:
    write('<div class="eyebrow">Who this is for</div>')
    client = st.text_input("Client", placeholder="Acme Ltd")
    product = st.text_input("Product", placeholder="Widget")
    operator = st.text_input("Prepared by", placeholder="Your name")

identity = run_identity(
    results, client=client or None, product=product or None, operator=operator or None
)
checklist = completeness_checklist(results, set_aside=aside)
open_items = unresolved(checklist)

with before:
    write('<div class="eyebrow">Before you send it</div>')
    write(checklist_block([
        (badge("Resolved", "done") if item["resolved"] else badge("Open", "review"),
         item["label"], item["detail"])
        for item in checklist
    ]))
    if open_items:
        write(alert(
            f"{plural(len(open_items), 'item')} still open. You can send this now, and "
            "every file will say on its first page exactly what was unresolved.",
            kind="review",
            title="Nothing ships silently",
        ))
    else:
        write(alert("Nothing was left unresolved on this run.", kind="ok",
                    title="All clear"))

pack = export_pack(results, identity, checklist)
names = {suffix: next(n for n in pack if n.endswith(suffix))
         for suffix in (".xlsx", ".json", ".md", ".html")}

st.download_button(
    f"Download the pack ({identity['run_id']}.zip)",
    data=to_zip(pack),
    file_name=f"{identity['run_id'].lower().replace('-', '_')}.zip",
    mime="application/zip",
    type="primary",
)
st.caption(f"Run {identity['run_id']}, generated {identity['generated_utc']}.")

one, two, three, four = st.columns(4)
one.download_button(
    "Workbook (.xlsx)", data=pack[names[".xlsx"]], file_name=names[".xlsx"],
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="stretch",
)
two.download_button(
    "Memo to print (.html)", data=pack[names[".html"]], file_name=names[".html"],
    mime="text/html", width="stretch",
)
three.download_button(
    "Report (.md)", data=pack[names[".md"]], file_name=names[".md"],
    mime="text/markdown", width="stretch",
)
four.download_button(
    "Data (.json)", data=pack[names[".json"]], file_name=names[".json"],
    mime="application/json", width="stretch",
)


# --- The nav's active-section highlight -------------------------------------
# Last, because it reads the sections it highlights: they have to exist first.
# Streamlit does not execute scripts inside markdown, so this rides in a
# zero-height components iframe. It is best-effort by design (see
# components.scrollspy): if it cannot run, the nav keeps working without a
# highlight.
st_components.html(scrollspy(COMPARE_SECTION + REPORT_SECTIONS), height=0)
