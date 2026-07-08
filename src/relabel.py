"""
relabel.py - pair DEFRA renames across two versions so they stop showing up as
added + removed noise.

Across 2025 to 2026 the full set shows roughly 500 "added" and 500 "removed"
activities. Most are not new or retired factors: they are the SAME factor with a
renamed label (e.g. "HGV (all diesel)" to "HGV (non-refrigerated, all diesel)").
Reported as added + removed they bury the handful of real movers. Pairing them
makes the diff readable.

THE NO-GUESS RULE APPLIES HERE TOO. A wrong pairing would misrepresent a change,
so a pair is only asserted when it is defensible:

  - same unit (a rename keeps the unit),
  - same scope (DEFRA relabels stay in scope),
  - high name similarity above `name_threshold` (rapidfuzz), AND
  - if the two names SUBSTITUTE a substantive word rather than just ADD a
    qualifier, a much higher bar (`substitution_threshold`).

That last gate matters, and it is applied to the LEAF of the activity name (the
last " - " segment: the fuel or specific variant, which carries the identity).
`token_set_ratio` rewards shared boilerplate, so "HGV (all diesel) ... Petrol"
scores ~100 against "HGV (non-refrigerated, all diesel) ... Diesel" even though
the fuel flipped, and because "diesel" appears in both names as a category label
a whole-string check misses the swap. Comparing the LEAF ("Petrol" vs "Diesel")
catches it. A leaf ADDITION ("Fuel oil" -> "Fuel oil (mineral)") is a low-risk
relabel; a leaf SUBSTITUTION (Petrol -> Diesel) is high-risk and only trusted
when nearly identical (e.g. the genuine synonym rename "propylene" -> "propene",
whose leaf is unchanged).

Pairs below the bar are NOT invented; the two activities stay added / removed.
This deliberately catches the common case (a qualifier added to the name) and
deliberately does NOT catch a semantic rename with a low string overlap
(e.g. "Incineration with energy recovery" to "Combustion"). Those need DEFRA's
own relabel notes and are out of scope for this pass (see DECISIONS D9).

Public functions:
    detect_relabels(diff_df, name_threshold=90.0) -> pandas.DataFrame with columns
        old_activity | new_activity | unit | scope |
        kg_co2e_old | kg_co2e_new | pct_change | name_score
    group_relabels(relabels_df) -> one row per rename FAMILY (same head rename and
        scope across many variants), so ~460 near-identical rows read as ~10.
    relabel_head(activity) -> the family label (first " - " segment).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

# Reuse the exact normalization the matcher uses, so "same string" means the
# same thing everywhere in the tool.
from matching import _norm, _units_compatible
# One shared materiality rule for the whole tool (see DECISIONS D10).
from diff import is_material

DEFAULT_NAME_THRESHOLD = 90.0  # 0-100 rapidfuzz similarity; deliberately high
# A token substitution (one word swapped for another) must be near-identical to
# trust, so a genuine synonym rename passes but a fuel/qualifier flip does not.
DEFAULT_SUBSTITUTION_THRESHOLD = 97.0

RELABEL_COLUMNS = [
    "old_activity",
    "new_activity",
    "unit",
    "scope",
    "kg_co2e_old",
    "kg_co2e_new",
    "pct_change",
    "name_score",
]


def _scope_key(scope) -> str:
    return str(scope).strip().lower()


def _leaf(activity: str) -> str:
    """The most-specific segment of an activity name (last ' - ' part), normalized.
    This is the fuel / variant that identifies the factor within its group."""
    parts = [p for p in str(activity).split(" - ") if p.strip()]
    return _norm(parts[-1]) if parts else _norm(activity)


def _is_leaf_substitution(old_leaf: str, new_leaf: str) -> bool:
    """True when each leaf has a word the other lacks (a swap, not a pure
    addition). A safe relabel only ADDS words to the leaf (one token set is a
    subset of the other): 'fuel oil' -> 'fuel oil mineral'. A two-way divergence
    is a substitution ('petrol' vs 'diesel', 'cng' vs 'lpg') and is only trusted
    when nearly identical. Note: no length filter, so short but decisive fuel
    codes (cng / lpg) are not waved through."""
    old_tokens, new_tokens = set(old_leaf.split()), set(new_leaf.split())
    only_old = old_tokens - new_tokens
    only_new = new_tokens - old_tokens
    return bool(only_old) and bool(only_new)


def _pct_change(old, new):
    """Percent change old->new for a paired factor, safe against zero / missing."""
    if old is None or new is None or pd.isna(old) or pd.isna(new) or old == 0:
        return np.nan
    return (new - old) / abs(old) * 100.0


def detect_relabels(
    diff_df: pd.DataFrame,
    name_threshold: float = DEFAULT_NAME_THRESHOLD,
    substitution_threshold: float = DEFAULT_SUBSTITUTION_THRESHOLD,
) -> pd.DataFrame:
    """Pair 'removed' old activities with 'added' new activities that are renames.

    Greedy one-to-one assignment: the highest-scoring defensible pair is taken
    first, and each old / new activity is used at most once. Anything left over
    stays added / removed and is never guessed into a pair.
    """
    removed = diff_df[diff_df["status"] == "removed"]
    added = diff_df[diff_df["status"] == "added"]

    # Build only the candidate pairs that clear the hard gates (unit + scope)
    # before spending a fuzzy comparison on them.
    candidates = []  # (score, old_index, new_index)
    for oi, o in removed.iterrows():
        o_norm = _norm(o["activity"])
        o_scope = _scope_key(o["scope"])
        for ni, a in added.iterrows():
            if not _units_compatible(o["unit"], a["unit"]):
                continue
            if o_scope != _scope_key(a["scope"]):
                continue
            a_norm = _norm(a["activity"])
            score = fuzz.token_set_ratio(o_norm, a_norm)
            if score < name_threshold:
                continue
            # If the identifying LEAF was swapped (petrol -> diesel), demand a
            # near-exact leaf match; a leaf addition only needs the base bar.
            o_leaf, a_leaf = _leaf(o["activity"]), _leaf(a["activity"])
            if _is_leaf_substitution(o_leaf, a_leaf):
                if fuzz.token_set_ratio(o_leaf, a_leaf) < substitution_threshold:
                    continue
            candidates.append((score, oi, ni))

    candidates.sort(key=lambda t: t[0], reverse=True)

    used_old, used_new, pairs = set(), set(), []
    for score, oi, ni in candidates:
        if oi in used_old or ni in used_new:
            continue
        used_old.add(oi)
        used_new.add(ni)
        o, a = diff_df.loc[oi], diff_df.loc[ni]
        old_v, new_v = o["kg_co2e_old"], a["kg_co2e_new"]
        pairs.append(
            {
                "old_activity": o["activity"],
                "new_activity": a["activity"],
                "unit": a["unit"],
                "scope": a["scope"],
                "kg_co2e_old": old_v,
                "kg_co2e_new": new_v,
                "pct_change": _pct_change(old_v, new_v),
                "name_score": round(float(score), 1),
            }
        )

    out = pd.DataFrame(pairs, columns=RELABEL_COLUMNS)
    # Strongest matches first for easy eyeballing.
    if not out.empty:
        out = out.sort_values("name_score", ascending=False).reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Grouping: collapse a rename FAMILY into one readable row.
#
# On the owner's real 2025->2026 data a single DEFRA rename (e.g. "HGV (all
# diesel)" -> "HGV (non-refrigerated, all diesel)") is applied across ~80
# weight-class / fuel / unit variants. Listed one per row that is ~460 near-
# identical lines, and (once the renamed-and-moved explainer is on) ~420
# near-identical explanation blocks. Grouping by the rename FAMILY turns that
# into ~10 rows without hiding anything: value movement is reported as a range,
# never a single invented delta, so honesty is preserved (D2 still holds).
# ---------------------------------------------------------------------------

RELABEL_GROUP_COLUMNS = [
    "old_name",
    "new_name",
    "scope",
    "units",
    "n_variants",
    "n_material",
    "pct_min",
    "pct_max",
    "movement",
]


def relabel_head(activity: str) -> str:
    """The family label of an activity: its first ' - ' segment. The same DEFRA
    rename is applied across dozens of variants that all share this head, so
    grouping on (old head, new head, scope) collapses that repetition into one
    family."""
    parts = [p for p in str(activity).split(" - ") if p.strip()]
    return parts[0].strip() if parts else str(activity).strip()


def _movement_label(pct_series, n_material: int) -> str:
    """Honest one-line summary of how a rename family's values moved. Never a
    single made-up delta for the group: a spread is shown as a range."""
    vals = [p for p in pct_series if pd.notna(p)]
    if not vals or (abs(min(vals)) < 0.05 and abs(max(vals)) < 0.05):
        return "rename only (value unchanged)"
    lo, hi = min(vals), max(vals)
    body = (
        f"value moved {lo:+.1f}%"
        if abs(lo - hi) < 0.05
        else f"values shifted {lo:+.1f}% to {hi:+.1f}%"
    )
    if n_material:
        body += f"; {n_material} past DEFRA threshold"
    return body


def group_relabels(relabels_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-variant relabel pairs into one row per rename FAMILY.

    A family is the same rename (same old head -> new head, same scope) applied
    across many weight-class / fuel / unit variants. A one-variant family keeps
    its full names; a real family shows the shared heads and a count. Sorted with
    the families that carry material movement first.
    """
    if relabels_df is None or relabels_df.empty:
        return pd.DataFrame(columns=RELABEL_GROUP_COLUMNS)

    df = relabels_df.copy()
    df["_oh"] = df["old_activity"].map(relabel_head)
    df["_nh"] = df["new_activity"].map(relabel_head)
    df["_material"] = [is_material(p, s) for p, s in zip(df["pct_change"], df["scope"])]

    rows = []
    for (oh, nh, scope), g in df.groupby(["_oh", "_nh", "scope"], sort=False):
        n = len(g)
        n_mat = int(g["_material"].sum())
        vals = [p for p in g["pct_change"] if pd.notna(p)]
        if n == 1:
            old_name, new_name = g.iloc[0]["old_activity"], g.iloc[0]["new_activity"]
        else:
            old_name, new_name = oh, nh
        rows.append(
            {
                "old_name": old_name,
                "new_name": new_name,
                "scope": scope,
                "units": ", ".join(sorted(g["unit"].astype(str).unique())),
                "n_variants": n,
                "n_material": n_mat,
                "pct_min": min(vals) if vals else np.nan,
                "pct_max": max(vals) if vals else np.nan,
                "movement": _movement_label(g["pct_change"], n_mat),
            }
        )

    out = pd.DataFrame(rows, columns=RELABEL_GROUP_COLUMNS)
    out = out.sort_values(
        ["n_material", "n_variants"], ascending=False
    ).reset_index(drop=True)
    return out
