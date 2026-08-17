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


def is_material(pct, scope) -> bool:
    """True when |pct_change| exceeds DEFRA's materiality threshold for the scope.

    Single source of truth for "is this change material": used both here for the
    `flagged` column and by the pipeline when deciding whether a renamed factor
    (a relabel) also moved enough to deserve a grounded explanation. A missing
    percent (added/removed, or a change from zero) is never material.
    """
    if pct is None or pd.isna(pct):
        return False
    return abs(pct) > _threshold_for_scope(scope)


def diff_versions(df_old: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """Join two normalized tables on (activity, unit) and flag material movers."""
    key = ["activity", "unit"]
    # Provenance rides along so a citation can name the workbook, sheet and row a
    # factor was read from. Carried, never reconstructed downstream (DECISIONS D2).
    src = ["source_file", "source_sheet", "source_row"]
    have_src = all(c in df_old.columns for c in src) and all(c in df_new.columns for c in src)
    cols = ["scope", "kg_co2e"] + (src if have_src else [])

    old = df_old[key + cols].rename(columns={"kg_co2e": "kg_co2e_old"})
    new = df_new[key + cols].rename(columns={"kg_co2e": "kg_co2e_new"})

    merged = old.merge(new, on=key, how="outer", suffixes=("_old", "_new"))

    # Prefer whichever scope is present (they should agree across versions).
    merged["scope"] = merged["scope_new"].fillna(merged["scope_old"])
    merged = merged.drop(columns=["scope_old", "scope_new"])

    # Cite the NEW workbook where the factor still exists, since that is the
    # version the reader is moving to. A removed factor only exists in the old
    # one, so it cites that instead.
    for c in src:
        if have_src:
            merged[c] = merged[f"{c}_new"].fillna(merged[f"{c}_old"])
            merged = merged.drop(columns=[f"{c}_new", f"{c}_old"])
        else:
            merged[c] = None

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
        flagged = bool(has_old and has_new and is_material(pct, r["scope"]))

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
                "source_file": r.get("source_file"),
                "source_sheet": r.get("source_sheet"),
                "source_row": r.get("source_row"),
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


# Every status a browsable row can carry, in the order a reader wants them, with
# the words a reader actually uses. "renamed" is not a status diff_versions
# produces: it is the relabel pairing laid over the top (see pipeline.compare_
# versions), which is why a renamed row is excluded from "new" and "retired"
# below. Without that, DEFRA's ~500 renames read as 500 new factors.
STATUS_LABELS = {
    "changed": "Changed",
    "unchanged": "Unchanged",
    "added": "New",
    "removed": "Retired",
    "renamed": "Renamed",
}


def with_status_label(diff_df):
    """A copy of diff_df with a `status_label` column: what a reader sees when
    they filter by "What happened to the factor".

    Filtering to "New" or "Retired" and then finding no column that says so is
    the exact gap this closes. `renamed` beats `status`, same rule
    `filter_changes` already applies: a paired DEFRA rename is reported as a
    rename, never also as new or retired (that double-count is the noise the
    relabel pairing exists to remove). Display-only: nothing downstream that
    reads `status` itself changes.
    """
    out = diff_df.copy()
    renamed = (
        out["renamed"].fillna(False).astype(bool)
        if "renamed" in out.columns
        else pd.Series(False, index=out.index)
    )
    out["status_label"] = out["status"].map(STATUS_LABELS)
    out.loc[renamed, "status_label"] = STATUS_LABELS["renamed"]
    return out


def filter_changes(diff_df, query="", scopes=None, statuses=None,
                   min_pct=0.0, material_only=False):
    """Narrow a diff table to the rows a reader asked for. Pure, no UI.

    Every filter is a plain AND, and an empty filter means "do not narrow on
    this", so the resting state is the whole table rather than an empty one.

    `min_pct` drops rows with no percent change at all (added, retired, or a
    change from zero) as soon as it is above zero, because asking for "moved by
    at least 10%" is asking about movement, and a row with no computable
    movement cannot answer it. At zero, nothing is dropped.

    Lives here rather than in app.py so the rule that decides what a reader is
    shown is testable without booting Streamlit.
    """
    out = diff_df
    if out is None or len(out) == 0:
        return out

    if query:
        needle = str(query).strip().lower()
        if needle:
            hay = (
                out["activity"].astype(str).str.lower()
                + " "
                + out["unit"].astype(str).str.lower()
            )
            out = out[hay.str.contains(needle, regex=False, na=False)]

    if scopes:
        out = out[out["scope"].isin(list(scopes))]

    if statuses:
        wanted = set(statuses)
        renamed = (
            out["renamed"].fillna(False).astype(bool)
            if "renamed" in out.columns
            else pd.Series(False, index=out.index)
        )
        keep = pd.Series(False, index=out.index)
        if "renamed" in wanted:
            keep |= renamed
        for name in ("changed", "unchanged", "added", "removed"):
            if name in wanted:
                # A paired rename is reported as a rename, never also as a new
                # or retired factor. Counting it twice is the exact noise the
                # relabel pairing exists to remove.
                keep |= (out["status"] == name) & ~renamed
        out = out[keep]

    if min_pct and min_pct > 0:
        out = out[out["pct_change"].abs() >= float(min_pct)]

    if material_only:
        out = out[out["flagged"].fillna(False).astype(bool)]

    return out
