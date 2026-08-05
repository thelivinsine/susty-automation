"""
app.py - the EF Version Explainer dashboard.

Run:  streamlit run app.py

The page is an app shell, not a document: a masthead that says what this is and
which two DEFRA releases it is comparing, a setup flow, and then the report
behind a sticky section nav.

Setup lives in the MAIN canvas, in three numbered steps. Two reasons. Below
768px Streamlit collapses the sidebar and takes every input with it, which left
the app looking read-only (defect A-09). And a first-time visitor was previously
handed a blank page and the instruction "upload a file, confirm your columns in
the sidebar, then click Run analysis", which is a set of directions rather than
a flow. The sidebar now carries account and settings only.

The report reads in the order a reader actually needs it:

    Result -> Confidence -> Movers -> Explanations -> Export

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
from pipeline import run_pipeline         # noqa: E402
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
from ui.format import direction, kg, plural, sig_figs, signed_pct  # noqa: E402

st.set_page_config(page_title="EF Version Explainer", layout="wide")

# The owned design layer (src/ui/). Streamlit's own chrome is themed by
# .streamlit/config.toml; this adds the tokens and the accessibility fixes the
# front-end audit measured. Must come before anything is rendered.
inject_styles()

# Coverage below this is reported as an incomplete answer rather than a clean
# one. Stating the bar is the point: an unqualified total over 85% of a bill of
# materials is the kind of quiet overclaim this tool exists to avoid.
COVERAGE_BAR = 95.0

SECTIONS = [
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


# ===========================================================================
# Setup: three numbered steps, in the canvas
# ===========================================================================

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
def _run(old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai):
    return run_pipeline(old_p, new_p, pdf_p, bom_df, old_l, new_l, use_ai=use_ai)


# Recompute when the user clicks Run, on first load, OR when the explainer tier
# changed (e.g. they just signed in and now qualify for AI). Both tiers are
# cached, so toggling back and forth is instant and never re-spends the key.
tier_changed = st.session_state.get("results_use_ai") != use_ai
if (run or "results" not in st.session_state or tier_changed) and ingest_ready:
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
    paint_masthead(("Report ready", "done"))

if "results" not in st.session_state:
    write(alert(
        "Upload your inventory and confirm the columns above, then run the "
        "analysis. Nothing is matched or assumed until you do.",
        title="Nothing to show yet",
    ))
    st.stop()

results = st.session_state["results"]
s = results["summary"]
labels = results["labels"]

write(subnav(SECTIONS))


# --- 1. Result --------------------------------------------------------------
# One card, one answer. Green is the rail and the tag ("the run completed and
# this is the answer"), never the fill, so the figure stays ink on ground and no
# reader mistakes the panel colour for good news.
write(section(
    "Result",
    eyebrow="Section 1",
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


# --- 2. Confidence ----------------------------------------------------------
# The trust gate, before the conclusion gets acted on.
write(section(
    "Confidence",
    eyebrow="Section 2",
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


# --- 3. Movers --------------------------------------------------------------
write(section(
    "Movers",
    eyebrow="Section 3",
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


# --- 4. Explanations --------------------------------------------------------
write(section(
    "Explanations",
    eyebrow="Section 4",
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


# --- 5. Export --------------------------------------------------------------
write(section(
    "Export",
    eyebrow="Section 5",
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
st_components.html(scrollspy(SECTIONS), height=0)
