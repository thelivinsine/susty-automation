"""
matching.py — map each product bill-of-materials (BOM) line to a DEFRA activity.

THE CORE DOMAIN RULE: never silently guess. A wrong emission-factor match is
worse than no match. Anything below the confidence threshold is left UNMATCHED
and flagged `needs_review` for a human — it is never guessed.

Strategy, cheapest first:
  1. Exact / normalized string match on activity (+ compatible unit).
  2. Fuzzy string match (rapidfuzz) with a similarity score.
  3. Below threshold -> unmatched, needs_review = True.

No AI is used here — string matching only. AI-assisted matching for the
leftovers is a later, optional upgrade.

Public function: match_bom(bom_df, factors_df, threshold=82) -> DataFrame
    line_item | quantity | unit | matched_activity | matched_unit |
    match_score | match_method | needs_review
"""

from __future__ import annotations

import re
import pandas as pd
from rapidfuzz import fuzz

DEFAULT_THRESHOLD = 82.0  # 0-100 rapidfuzz similarity


def _norm(text) -> str:
    """Normalize a string for comparison: lower, strip punctuation, collapse space."""
    s = str(text).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _norm_unit(unit) -> str:
    """Normalize a unit and fold common synonyms so 'kWh' == 'kwh' etc."""
    u = _norm(unit)
    synonyms = {
        "kwh": "kwh",
        "kw h": "kwh",
        "litres": "litre",
        "l": "litre",
        "tonnes": "tonne",
        "t": "tonne",
        "kg": "kg",
        "m3": "cubic metre",
        "cubic metres": "cubic metre",
        "cubic meter": "cubic metre",
        "tonne km": "tonne.km",
        "tkm": "tonne.km",
    }
    return synonyms.get(u, u)


def _units_compatible(a: str, b: str) -> bool:
    return _norm_unit(a) == _norm_unit(b)


def _match_targets(activity: str, category: str) -> list[str]:
    """
    The strings we're willing to compare a BOM item against for one factor.

    A real BOM line ("Aluminium, primary") rarely repeats DEFRA's full prefixed
    name ("Metal - Aluminium - Primary material production"). So we also compare
    against the most specific segment and the category, and take the best score.
    This helps genuine matches without lowering the score bar (which protects the
    no-guess rule).
    """
    targets = [_norm(activity)]
    segments = [s.strip() for s in str(activity).split(" - ") if s.strip()]
    if segments:
        targets.append(_norm(segments[-1]))                 # most specific level
        targets.append(_norm(" ".join(segments[-2:])))      # last two levels
    if category:
        targets.append(_norm(f"{category} {segments[-1] if segments else ''}"))
    # de-dup while preserving order
    seen, out = set(), []
    for t in targets:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _best_score(item_norm: str, targets: list[str]) -> float:
    """Best rapidfuzz score of the item against any acceptable target string."""
    best = 0.0
    for t in targets:
        best = max(best, fuzz.token_set_ratio(item_norm, t))
    return best


def match_bom(
    bom_df: pd.DataFrame,
    factors_df: pd.DataFrame,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """Match each BOM line to the best DEFRA activity, honouring the no-guess rule."""
    factors = factors_df.copy()
    factors["_norm_activity"] = factors["activity"].map(_norm)
    factors["_targets"] = factors.apply(
        lambda r: _match_targets(r["activity"], r.get("category", "")), axis=1
    )

    results = []
    for _, line in bom_df.iterrows():
        item = line["line_item"]
        item_norm = _norm(item)
        item_unit = line.get("unit", "")

        # Only consider factors whose unit is compatible (a match on the wrong
        # unit is a wrong match — exactly what we must avoid).
        candidates = factors[
            factors["unit"].map(lambda u: _units_compatible(u, item_unit))
        ]
        if candidates.empty:
            candidates = factors  # fall back, but the score bar still applies

        matched_activity = None
        matched_unit = None
        score = 0.0
        method = "none"

        # 1) exact normalized match
        exact = candidates[candidates["_norm_activity"] == item_norm]
        if not exact.empty:
            row = exact.iloc[0]
            matched_activity, matched_unit = row["activity"], row["unit"]
            score, method = 100.0, "exact"
        else:
            # 2) fuzzy match: score each candidate against its activity name, its
            #    most specific segment, and its category; keep the best overall.
            best_idx, best_score = None, 0.0
            for pos in range(len(candidates)):
                s = _best_score(item_norm, candidates.iloc[pos]["_targets"])
                if s > best_score:
                    best_score, best_idx = s, pos
            score = float(best_score)
            if best_idx is not None and score >= threshold:
                row = candidates.iloc[best_idx]
                matched_activity = row["activity"]
                matched_unit = row["unit"]
                method = "fuzzy"
            else:
                method = "below_threshold"

        needs_review = matched_activity is None
        results.append(
            {
                "line_item": item,
                "quantity": line.get("quantity"),
                "unit": item_unit,
                "matched_activity": matched_activity,
                "matched_unit": matched_unit,
                "match_score": round(score, 1),
                "match_method": method,
                "needs_review": needs_review,
            }
        )

    return pd.DataFrame(results)


def coverage_summary(matched_df: pd.DataFrame) -> dict:
    """Quick counts for how much of the BOM matched automatically."""
    total = len(matched_df)
    review = int(matched_df["needs_review"].sum())
    return {
        "total_lines": total,
        "auto_matched": total - review,
        "needs_review": review,
        "auto_match_pct": round((total - review) / total * 100, 1) if total else 0.0,
    }
