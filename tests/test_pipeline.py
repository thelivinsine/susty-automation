"""
Tests that mirror the MVP acceptance criteria from the build playbook.

These run against the committed SYNTHETIC data, whose expected movements are
known, so each stage can be checked deterministically.
"""

import os
import pandas as pd
import pytest

from loader import load_defra
from diff import diff_versions
from matching import match_bom, coverage_summary
from recompute import recompute
from changes_pdf import extract_changes_text, chunk_changes, retrieve_passage
from explain import explain_change, NO_REASON
from pipeline import compare_versions, run_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH = os.path.join(ROOT, "data", "synthetic")


@pytest.fixture(scope="module")
def factors():
    old = load_defra(os.path.join(SYNTH, "defra_2025.xlsx"), "2025")
    new = load_defra(os.path.join(SYNTH, "defra_2026.xlsx"), "2026")
    return old, new


# ---- Loader ----------------------------------------------------------------
def test_loader_normalizes(factors):
    old, _ = factors
    assert set(["activity", "unit", "kg_co2e", "scope", "category", "version"]).issubset(
        old.columns
    )
    assert old["kg_co2e"].map(lambda x: isinstance(x, float)).all()
    assert (old["activity"].str.strip() != "").all()
    assert old["scope"].str.contains("Scope").any()


# ---- Diff ------------------------------------------------------------------
def test_diff_flags_by_threshold(factors):
    old, new = factors
    d = diff_versions(old, new)

    # Board rises 9.76% on Scope 3 -> below the 10% Scope-3 threshold -> NOT flagged.
    board = d[d["activity"].str.contains("Board")].iloc[0]
    assert not board["flagged"]

    # Diesel rises ~6% on Scope 1 -> above the 5% Scope-1/2 threshold -> flagged.
    diesel = d[d["activity"].str.contains("Diesel")].iloc[0]
    assert diesel["flagged"]

    # A known mover appears with a sane percentage (manual-check friendliness).
    elec = d[d["activity"].str.contains("Electricity generated")].iloc[0]
    assert 8.0 < elec["pct_change"] < 9.5


def test_diff_handles_added_removed():
    old = pd.DataFrame(
        [{"activity": "A", "unit": "kg", "kg_co2e": 1.0, "scope": "Scope 1",
          "category": "c", "version": "2025"}]
    )
    new = pd.DataFrame(
        [{"activity": "B", "unit": "kg", "kg_co2e": 2.0, "scope": "Scope 1",
          "category": "c", "version": "2026"}]
    )
    d = diff_versions(old, new)
    statuses = set(d["status"])
    assert "added" in statuses and "removed" in statuses  # no crash on disjoint sets


# ---- Matching (the no-guess rule) ------------------------------------------
def test_matching_meets_coverage_and_never_guesses(factors):
    old, _ = factors
    bom = pd.read_csv(os.path.join(SYNTH, "sample_bom.csv"))
    m = match_bom(bom, old)
    cov = coverage_summary(m)

    # Acceptance criterion: >=80% auto-matched.
    assert cov["auto_match_pct"] >= 80

    # The deliberately-novel line must be flagged, not guessed.
    novel = m[m["line_item"].str.contains("sealant")].iloc[0]
    assert novel["needs_review"]
    assert pd.isna(novel["matched_activity"]) or novel["matched_activity"] is None

    # Every matched line has a score at/above threshold.
    matched = m[~m["needs_review"]]
    assert (matched["match_score"] >= 82).all()


# ---- Recompute (coverage honesty) ------------------------------------------
def test_recompute_reports_coverage(factors):
    old, new = factors
    d = diff_versions(old, new)
    bom = pd.read_csv(os.path.join(SYNTH, "sample_bom.csv"))
    m = match_bom(bom, old)
    line_table, summary = recompute(m, d)

    assert summary["total_new"] > summary["total_old"]  # footprint rose
    assert 0 < summary["coverage_pct"] < 100            # 1 line excluded
    # Excluded lines never contribute to the totals.
    excluded = line_table[~line_table["included"]]
    assert excluded["co2e_new"].isna().all()


# ---- Explanation grounding (the trap test) ---------------------------------
def test_explanation_is_grounded_and_wont_invent():
    chunks = chunk_changes(
        extract_changes_text(os.path.join(SYNTH, "changes_2026.pdf"))
    )

    # Grounded case: aluminium IS explained -> a real reason comes back.
    mat = "Metal - Aluminium - Primary material production"
    passage, score = retrieve_passage(chunks, mat)
    assert passage != ""
    grounded = explain_change(mat, 12500, 14200, 13.6, passage, {"breaches_baseline": True})
    assert grounded["plain_english_reason"] != NO_REASON

    # Trap case: plastics is NOT explained -> must refuse to invent a reason.
    trap = "Plastic - Average plastics - Primary material production"
    passage2, _ = retrieve_passage(chunks, trap)
    assert passage2 == ""
    out = explain_change(trap, 3120, 3450, 10.58, passage2, {"breaches_baseline": True})
    assert out["plain_english_reason"] == NO_REASON


# ---- comparison= reuse (P1-C: don't parse the workbooks twice) -------------
# app.py's section 1 parses both workbooks before a visitor ever presses Run.
# run_pipeline() must reuse that work when it is handed in, and must never
# TRUST a comparison whose labels do not match what this call was asked for,
# since that would be the one way a stale or wrong-version comparison could
# silently produce a wrong-looking answer.

def _run_pipeline(bom="sample_bom.csv", old_label="2025", new_label="2026", **kwargs):
    return run_pipeline(
        os.path.join(SYNTH, "defra_2025.xlsx"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
        os.path.join(SYNTH, "changes_2026.pdf"),
        pd.read_csv(os.path.join(SYNTH, bom)),
        old_label,
        new_label,
        use_ai=False,
        **kwargs,
    )


def test_a_matching_comparison_is_reused_not_reparsed():
    comparison = compare_versions(
        os.path.join(SYNTH, "defra_2025.xlsx"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
        "2025",
        "2026",
    )
    # A sentinel column a fresh compare_versions() call would never produce.
    # If it survives into the result, run_pipeline reused THIS object.
    comparison["diff_df"] = comparison["diff_df"].copy()
    comparison["diff_df"]["_sentinel"] = "reused"

    results = _run_pipeline(comparison=comparison)
    assert "_sentinel" in results["diff_df"].columns
    assert (results["diff_df"]["_sentinel"] == "reused").all()


def test_a_mismatched_comparison_is_ignored_not_trusted():
    comparison = compare_versions(
        os.path.join(SYNTH, "defra_2025.xlsx"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
        "2025",
        "2026",
    )
    comparison["diff_df"] = comparison["diff_df"].copy()
    comparison["diff_df"]["_sentinel"] = "reused"

    # This call asks for "2025" -> "2027", so the "2025" -> "2026" comparison
    # above must be ignored and recomputed fresh, sentinel and all.
    results = _run_pipeline(comparison=comparison, new_label="2027")
    assert "_sentinel" not in results["diff_df"].columns
    assert results["labels"] == {"old": "2025", "new": "2027"}


# ---- Real DEFRA full-set workbook (skips if the big files aren't present) ----
REAL_OLD = os.path.join(ROOT, "data", "ghg-conversion-factors-2025-full-set.xlsx")
REAL_NEW = os.path.join(ROOT, "data", "ghg-conversion-factors-2026-full-set.xlsx")


@pytest.mark.skipif(
    not (os.path.exists(REAL_OLD) and os.path.exists(REAL_NEW)),
    reason="real DEFRA full-set workbooks not present in data/",
)
def test_real_workbook_loads_and_diffs():
    from changes_pdf import load_change_chunks, retrieve_passage as rp

    old = load_defra(REAL_OLD, "2025")
    new = load_defra(REAL_NEW, "2026")
    # Sanity: the real full set has well over a thousand factors across scopes.
    assert len(old) > 1500 and len(new) > 1500
    assert {"Scope 1", "Scope 2", "Scope 3"}.issubset(set(old["scope"]))

    d = diff_versions(old, new)
    # The headline UK electricity factor exists in both years and falls sharply.
    elec = d[d["activity"] == "Electricity generated - Electricity: UK"]
    assert not elec.empty
    assert elec.iloc[0]["pct_change"] < -10  # 2026 methodology cut it ~26%

    # The workbook's own "What's new" sheet grounds the electricity explanation.
    chunks = load_change_chunks(None, REAL_NEW)
    passage, score = rp(chunks, "Electricity generated - Electricity: UK")
    assert passage != "" and "electricity" in passage.lower()
