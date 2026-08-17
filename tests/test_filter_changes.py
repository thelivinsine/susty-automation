"""
test_filter_changes.py - the rule that decides what a reader is shown.

`diff.filter_changes` is the whole interactive comparison. It sits in src/diff.py
rather than in app.py precisely so it can be checked without booting Streamlit,
and the cases below are the ones where a filter can quietly lie:

  - an empty filter must mean "do not narrow", never "show nothing",
  - a paired DEFRA rename must not also be counted as a new factor, which is the
    exact noise the relabel pairing exists to remove,
  - a minimum-change filter must drop rows with no computable change, because a
    factor that only exists in one release cannot answer "did it move by 10%".

Run it on its own to SEE the numbers:

    python tests/test_filter_changes.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from diff import STATUS_LABELS, filter_changes, with_status_label  # noqa: E402


def sample():
    """A small diff table covering every status a row can carry."""
    return pd.DataFrame([
        # activity, unit, scope, old, new, pct, status, flagged, renamed
        ("UK electricity", "kWh", "Scope 2", 0.207, 0.153, -26.0, "changed", True, False),
        ("Natural gas", "kWh", "Scope 1", 0.183, 0.182, -0.5, "changed", False, False),
        ("Steel closed loop", "tonnes", "Scope 3", 1.20, 1.42, 18.3, "changed", True, False),
        ("Paper", "tonnes", "Scope 3", 0.90, 0.90, 0.0, "unchanged", False, False),
        ("HGV (all diesel)", "km", "Scope 3", 0.80, None, None, "removed", False, True),
        ("HGV (non-refrigerated, all diesel)", "km", "Scope 3", None, 0.81, None,
         "added", False, True),
        ("Hydrogen, green", "kg", "Scope 3", None, 2.50, None, "added", False, False),
    ], columns=["activity", "unit", "scope", "kg_co2e_old", "kg_co2e_new",
                "pct_change", "status", "flagged", "renamed"])


def names(df):
    return sorted(df["activity"])


# --------------------------------------------------------------------------
# The resting state
# --------------------------------------------------------------------------

def test_no_filters_narrows_nothing():
    """An empty filter set means the whole table, not an empty one."""
    assert len(filter_changes(sample())) == 7


def test_an_empty_frame_survives_every_filter():
    empty = sample().iloc[0:0]
    out = filter_changes(empty, query="anything", scopes=["Scope 1"],
                         statuses=["changed"], min_pct=50.0, material_only=True)
    assert len(out) == 0


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------

def test_search_is_case_insensitive_and_matches_part_of_a_name():
    assert names(filter_changes(sample(), query="ELECTRIC")) == ["UK electricity"]


def test_search_also_looks_at_the_unit():
    """"everything in tonnes" is a real question, and the unit is where it lives."""
    assert names(filter_changes(sample(), query="tonnes")) == ["Paper", "Steel closed loop"]


def test_search_treats_its_input_as_text_not_as_a_pattern():
    """A stray bracket from a DEFRA activity name must not blow up as a regex."""
    assert names(filter_changes(sample(), query="(all diesel)")) == ["HGV (all diesel)"]


def test_a_blank_search_is_not_a_filter():
    assert len(filter_changes(sample(), query="   ")) == 7


# --------------------------------------------------------------------------
# Scope and status
# --------------------------------------------------------------------------

def test_scope_filter_keeps_only_that_scope():
    assert names(filter_changes(sample(), scopes=["Scope 2"])) == ["UK electricity"]


def test_new_excludes_a_paired_rename():
    """The load-bearing case.

    "HGV (non-refrigerated, all diesel)" is an `added` row, but the relabel
    pairing matched it to the old name, so it is a rename and not a new factor.
    Counting it as new is how ~500 DEFRA relabels used to read as 500 arrivals.
    """
    assert names(filter_changes(sample(), statuses=["added"])) == ["Hydrogen, green"]


def test_retired_excludes_a_paired_rename():
    assert names(filter_changes(sample(), statuses=["removed"])) == []


def test_renamed_returns_both_halves_of_the_pair():
    out = filter_changes(sample(), statuses=["renamed"])
    assert names(out) == ["HGV (all diesel)", "HGV (non-refrigerated, all diesel)"]


def test_statuses_combine_as_or():
    out = filter_changes(sample(), statuses=["added", "renamed"])
    assert len(out) == 3


def test_every_offered_status_is_a_status_the_filter_understands():
    """The labels the app shows and the keys the filter accepts cannot drift."""
    for key in STATUS_LABELS:
        filter_changes(sample(), statuses=[key])  # must not raise


def test_status_filter_works_without_a_renamed_column():
    """diff_versions alone does not produce `renamed`; the filter must not need it."""
    bare = sample().drop(columns=["renamed"])
    assert len(filter_changes(bare, statuses=["added"])) == 2


# --------------------------------------------------------------------------
# with_status_label: what a reader sees for "What happened to the factor"
# --------------------------------------------------------------------------

def test_every_status_label_key_maps_to_its_word():
    """The filter's own keys and the column's own words must not drift apart."""
    out = with_status_label(sample())
    seen = dict(zip(out["activity"], out["status_label"]))
    assert seen["UK electricity"] == "Changed"
    assert seen["Paper"] == "Unchanged"
    assert seen["Hydrogen, green"] == "New"


def test_a_paired_rename_reads_as_renamed_not_added_or_removed():
    """Renamed beats status: the same rule filter_changes already applies, so
    the column a reader sees agrees with the filter they just set."""
    out = with_status_label(sample())
    seen = dict(zip(out["activity"], out["status_label"]))
    assert seen["HGV (all diesel)"] == "Renamed"
    assert seen["HGV (non-refrigerated, all diesel)"] == "Renamed"


def test_works_without_a_renamed_column():
    bare = sample().drop(columns=["renamed"])
    out = with_status_label(bare)
    assert (out["status_label"] == out["status"].map(STATUS_LABELS)).all()


def test_the_original_frame_is_not_mutated():
    original = sample()
    before = original.columns.tolist()
    with_status_label(original)
    assert original.columns.tolist() == before


# --------------------------------------------------------------------------
# Magnitude and materiality
# --------------------------------------------------------------------------

def test_minimum_change_keeps_only_bigger_movements():
    assert names(filter_changes(sample(), min_pct=20.0)) == ["UK electricity"]


def test_minimum_change_drops_rows_with_no_computable_change():
    """Added and retired factors have no percent change, so they cannot qualify."""
    out = filter_changes(sample(), min_pct=0.1)
    assert "Hydrogen, green" not in names(out)
    assert "Paper" not in names(out)


def test_a_zero_minimum_drops_nothing():
    assert len(filter_changes(sample(), min_pct=0.0)) == 7


def test_material_only_uses_the_flag_the_pipeline_already_set():
    """Materiality is diff.is_material's decision. The filter must not re-derive it."""
    assert names(filter_changes(sample(), material_only=True)) == [
        "Steel closed loop", "UK electricity",
    ]


def test_filters_combine_as_and():
    out = filter_changes(sample(), scopes=["Scope 3"], material_only=True)
    assert names(out) == ["Steel closed loop"]


def test_filtering_never_mutates_the_table_it_was_given():
    """The app hands it a cached frame. Mutating that would poison every rerun."""
    df = sample()
    before = df.copy()
    filter_changes(df, query="steel", scopes=["Scope 3"], min_pct=1.0,
                   material_only=True)
    pd.testing.assert_frame_equal(df, before)


# --------------------------------------------------------------------------
# Seeing it work
# --------------------------------------------------------------------------

if __name__ == "__main__":
    df = sample()
    print(f"{len(df)} factors in the sample table\n")
    for label, kwargs in [
        ("no filters", {}),
        ("search 'tonnes'", {"query": "tonnes"}),
        ("scope 3 only", {"scopes": ["Scope 3"]}),
        ("new factors (renames excluded)", {"statuses": ["added"]}),
        ("renames", {"statuses": ["renamed"]}),
        ("moved 20% or more", {"min_pct": 20.0}),
        ("past DEFRA thresholds", {"material_only": True}),
    ]:
        out = filter_changes(df, **kwargs)
        print(f"{label:32} {len(out)}  {', '.join(sorted(out['activity']))}")
