"""
Tests for relabel detection (src/relabel.py). Covers the happy path (a renamed
factor gets paired) and the no-guess guarantees (dissimilar names, mismatched
unit or scope are NOT paired, and pairing is one-to-one).
"""

import os
import numpy as np
import pandas as pd

from loader import load_defra
from diff import diff_versions
from relabel import detect_relabels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH = os.path.join(ROOT, "data", "synthetic")


def _row(activity, status, old=np.nan, new=np.nan, unit="litre", scope="Scope 1"):
    """Build one diff_df-shaped row (removed carries old, added carries new)."""
    return {
        "activity": activity,
        "unit": unit,
        "scope": scope,
        "kg_co2e_old": old,
        "kg_co2e_new": new,
        "pct_change": np.nan,
        "status": status,
        "flagged": False,
    }


def test_pairs_a_clear_rename():
    diff = pd.DataFrame([
        _row("HGV (all diesel)", "removed", old=1.20),
        _row("HGV (non-refrigerated, all diesel)", "added", new=1.25),
    ])
    rel = detect_relabels(diff)
    assert len(rel) == 1
    pair = rel.iloc[0]
    assert pair["old_activity"] == "HGV (all diesel)"
    assert pair["new_activity"] == "HGV (non-refrigerated, all diesel)"
    assert pair["name_score"] >= 90
    # pct_change is computed from the paired values (1.20 -> 1.25 = +4.17%).
    assert 4.0 < pair["pct_change"] < 4.3


def test_does_not_pair_dissimilar_names():
    # A true semantic rename with low string overlap is intentionally NOT paired
    # (we don't guess); it stays added + removed.
    diff = pd.DataFrame([
        _row("Incineration with energy recovery", "removed", old=0.50),
        _row("Combustion", "added", new=0.52),
    ])
    assert detect_relabels(diff).empty


def test_does_not_pair_a_fuel_substitution():
    # Heavy shared boilerplate scores high, but the leaf fuel flipped
    # (Petrol -> Diesel), so it is a different factor and must NOT be paired.
    diff = pd.DataFrame([
        _row("HGV (all diesel) - All HGVs - Petrol", "removed", old=1.20, unit="km"),
        _row("HGV (non-refrigerated, all diesel) - Average HGVs - Diesel", "added",
             new=1.25, unit="km"),
    ])
    assert detect_relabels(diff).empty


def test_does_not_pair_short_fuel_codes():
    # 'cng' -> 'lpg' is a swap of decisive short codes; the leaf guard must not
    # wave it through just because the codes are short.
    diff = pd.DataFrame([
        _row("HGV - All HGVs - CNG", "removed", old=1.0, unit="km"),
        _row("HGV - All HGVs - LPG", "added", new=1.1, unit="km"),
    ])
    assert detect_relabels(diff).empty


def test_pairs_a_synonym_rename_with_unchanged_leaf():
    # A genuine synonym rename in a middle segment (propylene -> propene) with an
    # identical leaf should still pair.
    diff = pd.DataFrame([
        _row("Other products - R1270 = propylene - Total emissions", "removed",
             old=1.80, unit="kg", scope="Scope 3"),
        _row("Other products - R1270 = propene - Total emissions", "added",
             new=1.82, unit="kg", scope="Scope 3"),
    ])
    rel = detect_relabels(diff)
    assert len(rel) == 1
    assert rel.iloc[0]["name_score"] >= 90


def test_does_not_pair_across_unit_or_scope():
    diff = pd.DataFrame([
        # identical names but different unit -> not the same factor
        _row("Fuel oil", "removed", old=3.1, unit="litre"),
        _row("Fuel oil", "added", new=3.2, unit="kg"),
        # identical names but different scope -> not paired
        _row("Widget", "removed", old=1.0, scope="Scope 1"),
        _row("Widget", "added", new=1.1, scope="Scope 3"),
    ])
    assert detect_relabels(diff).empty


def test_pairing_is_one_to_one():
    # Two similar removed names and one added name: only the best pair is taken,
    # and the added activity is not reused.
    diff = pd.DataFrame([
        _row("Fuel oil", "removed", old=3.10),
        _row("Fuel oil heavy", "removed", old=3.30),
        _row("Fuel oil (mineral)", "added", new=3.20),
    ])
    rel = detect_relabels(diff)
    assert len(rel) == 1
    assert rel.iloc[0]["new_activity"] == "Fuel oil (mineral)"
    # The added factor was consumed once, so one removed remains unpaired.


def test_empty_when_no_added_or_removed():
    diff = pd.DataFrame([_row("Diesel", "changed", old=2.5, new=2.6)])
    rel = detect_relabels(diff)
    assert rel.empty
    # Still returns the declared columns so callers can rely on the shape.
    assert list(rel.columns) == [
        "old_activity", "new_activity", "unit", "scope",
        "kg_co2e_old", "kg_co2e_new", "pct_change", "name_score",
    ]


def test_detects_the_synthetic_relabel_end_to_end():
    old = load_defra(os.path.join(SYNTH, "defra_2025.xlsx"), "2025")
    new = load_defra(os.path.join(SYNTH, "defra_2026.xlsx"), "2026")
    rel = detect_relabels(diff_versions(old, new))
    assert len(rel) == 1
    pair = rel.iloc[0]
    assert pair["old_activity"] == "Liquid fuels - Fuel oil"
    assert pair["new_activity"] == "Liquid fuels - Fuel oil (mineral)"


# ---- is_material: the single materiality rule shared with the relabel path ----
def test_is_material_uses_scope_thresholds():
    from diff import is_material

    # Scope 1/2 threshold is 5%; Scope 3 is 10%.
    assert is_material(6.0, "Scope 1") is True
    assert is_material(4.0, "Scope 2") is False
    assert is_material(6.0, "Scope 3") is False   # under the 10% Scope-3 bar
    assert is_material(-12.0, "Scope 3") is True  # direction-agnostic
    # A missing percent (added/removed, or change-from-zero) is never material.
    assert is_material(np.nan, "Scope 1") is False
    assert is_material(None, "Scope 1") is False


# ---- Renamed AND moved: the material relabel is routed through the explainer --
def test_pipeline_explains_a_material_relabel():
    from pipeline import run_pipeline

    results = run_pipeline(
        defra_old_path=os.path.join(SYNTH, "defra_2025.xlsx"),
        defra_new_path=os.path.join(SYNTH, "defra_2026.xlsx"),
        changes_pdf_path=os.path.join(SYNTH, "changes_2026.pdf"),
        bom_path_or_df=os.path.join(SYNTH, "sample_bom.csv"),
        old_label="2025",
        new_label="2026",
    )
    rel_expl = results["relabel_explanations"]
    # The fuel-oil relabel crossed the Scope-1 threshold, so exactly it is
    # explained; a non-material rename would not appear here.
    assert len(rel_expl) == 1
    e = rel_expl[0]
    assert e["old_activity"] == "Liquid fuels - Fuel oil"
    assert e["new_activity"] == "Liquid fuels - Fuel oil (mineral)"
    assert e["pct_change"] > 5.0

    # The changes note explains this one, so the reason is grounded (not the
    # "no reason" refusal) and carries the deterministic target flag.
    from explain import NO_REASON

    assert e["plain_english_reason"] != NO_REASON
    assert e["retrieval_score"] >= 0.5
    assert e["target_impact_flag"]
