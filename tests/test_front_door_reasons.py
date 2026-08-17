"""
test_front_door_reasons.py - the front door's half of "explain the delta".

`pipeline.cited_reasons` is what lets a cold visitor see WHY a factor moved
before uploading anything: DEFRA's own words, quoted, for every flagged factor,
with no model call. Three things matter here, in order of how badly they can go
wrong:

  - it must NEVER ground a factor in the wrong note (DECISIONS D11's guard has
    to protect this surface exactly as it protects the memo, since both call
    `retrieve_citation`),
  - a factor the notes are silent on must come back `explained=False`, never a
    guessed reason,
  - a row that did not cross DEFRA's materiality threshold must never appear,
    because "flagged" is the whole point of this list.

Uses the same synthetic data and the same labelled gold set as
tests/test_retrieval_quality.py (SYNTHETIC_GOLD), so the front door is judged
against the identical cases the grounding gate already trusts, rather than a
second fixture that could quietly drift from it.

Run it on its own to SEE the numbers:

    python tests/test_front_door_reasons.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from pipeline import cited_reasons            # noqa: E402
from ui.components import source_quote        # noqa: E402
from eval_retrieval import SYNTHETIC_GOLD      # noqa: E402

SYNTH = os.path.join(ROOT, "data", "synthetic")
PDF = os.path.join(SYNTH, "changes_2026.pdf")
XLSX = os.path.join(SYNTH, "defra_2026.xlsx")


def _diff_df_from_gold(extra_unflagged=0):
    """A diff_df covering every gold-set query, all flagged, plus optionally a
    few genuinely unflagged rows to prove they get excluded."""
    rows = []
    for i, case in enumerate(SYNTHETIC_GOLD):
        rows.append({
            "activity": case["query"],
            "unit": "kg",
            "scope": "Scope 1",
            "kg_co2e_old": 1.0,
            "kg_co2e_new": 1.2,
            "pct_change": 20.0,
            "flagged": True,
        })
    for i in range(extra_unflagged):
        rows.append({
            "activity": f"Unflagged filler activity {i}",
            "unit": "kg",
            "scope": "Scope 1",
            "kg_co2e_old": 1.0,
            "kg_co2e_new": 1.01,
            "pct_change": 1.0,
            "flagged": False,
        })
    return pd.DataFrame(rows)


def _reasons():
    return cited_reasons(_diff_df_from_gold(extra_unflagged=2), PDF, XLSX)


def test_a_matched_factor_is_cited_with_the_right_note():
    by_activity = {r["activity"]: r for r in _reasons()}
    row = by_activity["Electricity generated - Electricity: UK"]
    assert row["explained"] is True
    assert "Electricity generated" in row["quote"] + row["heading"]
    assert row["quote"]  # a real quote, not an empty string standing in for one


def test_an_unexplained_factor_comes_back_honest_not_guessed():
    by_activity = {r["activity"]: r for r in _reasons()}
    row = by_activity["Water supply"]
    assert row["explained"] is False
    assert row["quote"] == ""
    assert row["heading"] == ""


def test_the_d11_lookalike_is_refused_not_grounded_in_diesel():
    # "Petrol (average biofuel blend)" shares wording with the Diesel note but
    # has no note of its own. This is the exact trap D11 exists to catch, and
    # cited_reasons must fail it the same way retrieve_passage does.
    by_activity = {r["activity"]: r for r in _reasons()}
    row = by_activity["Liquid fuels - Petrol (average biofuel blend)"]
    assert row["explained"] is False
    assert "diesel" not in row["quote"].lower()
    assert "diesel" not in row["heading"].lower()


def test_only_flagged_rows_are_returned():
    reasons = _reasons()
    activities = {r["activity"] for r in reasons}
    assert len(reasons) == len(SYNTHETIC_GOLD)
    assert not any(a.startswith("Unflagged filler activity") for a in activities)


def test_no_flagged_rows_returns_an_empty_list_not_an_error():
    empty = _diff_df_from_gold(extra_unflagged=3)
    empty["flagged"] = False
    assert cited_reasons(empty, PDF, XLSX) == []


def test_a_quote_with_markup_renders_escaped():
    hostile = "<script>alert(1)</script> the actual DEFRA words"
    html = source_quote(hostile, "Major Changes report, Some heading. Retrieval relevance 0.9")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


if __name__ == "__main__":
    reasons = _reasons()
    explained = [r for r in reasons if r["explained"]]
    print(f"{len(reasons)} flagged rows from the gold set, {len(explained)} cited")
    for r in reasons:
        tag = "CITED" if r["explained"] else "SILENT"
        print(f"  [{tag}] {r['activity']}")
    test_a_matched_factor_is_cited_with_the_right_note()
    test_an_unexplained_factor_comes_back_honest_not_guessed()
    test_the_d11_lookalike_is_refused_not_grounded_in_diesel()
    test_only_flagged_rows_are_returned()
    test_no_flagged_rows_returns_an_empty_list_not_an_error()
    test_a_quote_with_markup_renders_escaped()
    print("all checks passed")
