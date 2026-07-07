"""
diff.py — compare two normalized DEFRA tables and flag material changes.

Public function: diff_versions(df_old, df_new) -> pandas.DataFrame with columns
    activity | unit | scope | kg_co2e_old | kg_co2e_new | pct_change | status | flagged

DEFRA's own materiality thresholds decide `flagged`:
    Scope 1 or 2 : |pct_change| > 5%
    Scope 3      : |pct_change| > 10%

`status` is one of: "changed", "unchanged", "added" (new only), "removed"
(old only). Activities present in only one version never crash the join.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SCOPE12_THRESHOLD = 5.0   # percent
SCOPE3_THRESHOLD = 10.0   # percent


def _pct_change(old, new):
    """Percent change old->new, safe against divide-by-zero / missing values."""
    if old is None or new is None or pd.isna(old) or pd.isna(new):
        return np.nan
    if old == 0:
        return np.nan  # can't express a % change from zero; caller sees it as "added"-ish
    return (new - old) / abs(old) * 100.0


def _threshold_for_scope(scope) -> float:
    s = str(scope).lower()
    if "1" in s or "2" in s:
        return SCOPE12_THRESHOLD
    if "3" in s:
        return SCOPE3_THRESHOLD
    # Unknown scope: be conservative, use the tighter threshold.
    return SCOPE12_THRESHOLD


def diff_versions(df_old: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """Join two normalized tables on (activity, unit) and flag material movers."""
    key = ["activity", "unit"]
    old = df_old[key + ["scope", "kg_co2e"]].rename(columns={"kg_co2e": "kg_co2e_old"})
    new = df_new[key + ["scope", "kg_co2e"]].rename(columns={"kg_co2e": "kg_co2e_new"})

    merged = old.merge(new, on=key, how="outer", suffixes=("_old", "_new"))

    # Prefer whichever scope is present (they should agree across versions).
    merged["scope"] = merged["scope_new"].fillna(merged["scope_old"])
    merged = merged.drop(columns=["scope_old", "scope_new"])

    rows = []
    for _, r in merged.iterrows():
        old_v, new_v = r["kg_co2e_old"], r["kg_co2e_new"]
        has_old, has_new = pd.notna(old_v), pd.notna(new_v)

        if has_old and has_new:
            status = "changed"
        elif has_new and not has_old:
            status = "added"
        elif has_old and not has_new:
            status = "removed"
        else:
            status = "unchanged"

        pct = _pct_change(old_v, new_v) if (has_old and has_new) else np.nan

        # "flagged" means a MATERIAL % change on a factor present in BOTH years.
        # Added / removed factors are reported separately (many are DEFRA
        # relabels, e.g. "Incineration with energy recovery" -> "Combustion");
        # lumping them in here would wildly overstate the count of real movers.
        flagged = bool(
            has_old
            and has_new
            and not pd.isna(pct)
            and abs(pct) > _threshold_for_scope(r["scope"])
        )

        rows.append(
            {
                "activity": r["activity"],
                "unit": r["unit"],
                "scope": r["scope"],
                "kg_co2e_old": old_v,
                "kg_co2e_new": new_v,
                "pct_change": pct,
                "status": status,
                "flagged": flagged,
            }
        )

    out = pd.DataFrame(rows)
    # Mark truly-unchanged rows (equal factors) so they don't read as "changed".
    same = (out["status"] == "changed") & (out["kg_co2e_old"] == out["kg_co2e_new"])
    out.loc[same, "status"] = "unchanged"

    # Sort biggest absolute movers first for easy eyeballing.
    out["_abs"] = out["pct_change"].abs()
    out = out.sort_values("_abs", ascending=False, na_position="last").drop(
        columns="_abs"
    )
    return out.reset_index(drop=True)
