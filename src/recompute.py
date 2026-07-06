"""
recompute.py — recompute a product's carbon footprint under the OLD and NEW
DEFRA factor versions, using the matched BOM plus the diff table.

    footprint = sum(quantity * kg_co2e) across MATCHED line items

Unmatched lines are excluded from the total but REPORTED as a coverage gap, so
the number is never quietly wrong. (No-guess rule again: better to say "we could
only compute 85% of this footprint" than to fabricate the rest.)

Public function: recompute(matched_df, diff_df) -> (line_table, summary_dict)
"""

from __future__ import annotations

import pandas as pd


def _factor_lookup(diff_df: pd.DataFrame) -> dict:
    """Map (activity, unit) -> (kg_co2e_old, kg_co2e_new) from the diff table."""
    lookup = {}
    for _, r in diff_df.iterrows():
        lookup[(r["activity"], r["unit"])] = (r["kg_co2e_old"], r["kg_co2e_new"])
    return lookup


def recompute(matched_df: pd.DataFrame, diff_df: pd.DataFrame):
    """Return (per-line table, summary dict). Only matched lines contribute."""
    lookup = _factor_lookup(diff_df)

    line_rows = []
    total_old = 0.0
    total_new = 0.0

    for _, m in matched_df.iterrows():
        if m["needs_review"] or not m["matched_activity"]:
            line_rows.append(
                {
                    "line_item": m["line_item"],
                    "quantity": m["quantity"],
                    "unit": m["unit"],
                    "matched_activity": None,
                    "factor_old": None,
                    "factor_new": None,
                    "co2e_old": None,
                    "co2e_new": None,
                    "line_delta": None,
                    "included": False,
                    "note": "unmatched — excluded from totals (needs human match)",
                }
            )
            continue

        key = (m["matched_activity"], m["matched_unit"])
        factor_old, factor_new = lookup.get(key, (None, None))
        qty = float(m["quantity"])

        if factor_old is None or factor_new is None or pd.isna(factor_old) or pd.isna(factor_new):
            # Matched to an activity that only exists in one version (added/removed).
            line_rows.append(
                {
                    "line_item": m["line_item"],
                    "quantity": qty,
                    "unit": m["unit"],
                    "matched_activity": m["matched_activity"],
                    "factor_old": factor_old,
                    "factor_new": factor_new,
                    "co2e_old": None,
                    "co2e_new": None,
                    "line_delta": None,
                    "included": False,
                    "note": "factor missing in one version — excluded from totals",
                }
            )
            continue

        co2e_old = qty * float(factor_old)
        co2e_new = qty * float(factor_new)
        total_old += co2e_old
        total_new += co2e_new
        line_rows.append(
            {
                "line_item": m["line_item"],
                "quantity": qty,
                "unit": m["unit"],
                "matched_activity": m["matched_activity"],
                "factor_old": float(factor_old),
                "factor_new": float(factor_new),
                "co2e_old": co2e_old,
                "co2e_new": co2e_new,
                "line_delta": co2e_new - co2e_old,
                "included": True,
                "note": "",
            }
        )

    line_table = pd.DataFrame(line_rows)

    # Coverage: share of NEW-version footprint that we could actually compute.
    included = line_table[line_table["included"]]
    n_total = len(line_table)
    n_included = len(included)
    coverage_pct = round(n_included / n_total * 100, 1) if n_total else 0.0

    abs_delta = total_new - total_old
    pct_delta = round(abs_delta / total_old * 100, 2) if total_old else None

    summary = {
        "total_old": round(total_old, 4),
        "total_new": round(total_new, 4),
        "absolute_delta": round(abs_delta, 4),
        "pct_delta": pct_delta,
        "lines_total": n_total,
        "lines_included": n_included,
        "lines_excluded": n_total - n_included,
        "coverage_pct": coverage_pct,
    }
    return line_table, summary


def top_delta_lines(line_table: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """The n line items contributing most (by magnitude) to the delta."""
    included = line_table[line_table["included"]].copy()
    if included.empty:
        return included
    included["_abs"] = included["line_delta"].abs()
    return included.sort_values("_abs", ascending=False).drop(columns="_abs").head(n)
