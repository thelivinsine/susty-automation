"""
report.py — assemble the one-page Markdown report from pipeline results.

build_markdown_report(results) -> str
"""

from __future__ import annotations

import pandas as pd


def _fmt(x, nd=3):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:,.{nd}f}"
    return str(x)


def build_markdown_report(results: dict) -> str:
    s = results["summary"]
    labels = results["labels"]
    old_l, new_l = labels["old"], labels["new"]

    pct = s["pct_delta"]
    direction = "up" if (pct or 0) >= 0 else "down"
    arrow = "▲" if (pct or 0) >= 0 else "▼"

    lines = []
    lines.append("# EF Version Explainer report")
    lines.append("")
    lines.append(
        f"**Comparing DEFRA {old_l} → {new_l}.** "
        "Carbon (kg CO₂e) only. Figures reflect the product's bill-of-materials "
        "recomputed under each factor version."
    )
    lines.append("")

    # Headline
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"Footprint moved from **{_fmt(s['total_old'])} → {_fmt(s['total_new'])} "
        f"kg CO₂e** ({arrow} {_fmt(abs(pct) if pct is not None else None,2)}% {direction})."
    )
    lines.append("")
    lines.append(
        f"- Coverage: **{s['coverage_pct']}%** of the bill-of-materials could be "
        f"computed ({s['lines_included']}/{s['lines_total']} lines). "
        f"{s['lines_excluded']} line(s) excluded. See *Needs review* below."
    )
    if results["context"].get("breaches_baseline"):
        lines.append(
            "- ⚠️ **Target flag:** the footprint increased, which would **breach a "
            "flat baseline**. Flag for review against active targets (e.g. SBTi)."
        )
    else:
        lines.append("- ✅ Footprint did not increase against a flat baseline.")

    ds = results.get("diff_stats")
    if ds:
        relabels_n = ds.get("relabels", 0)
        added_net = ds.get("added_net", ds["added"])
        removed_net = ds.get("removed_net", ds["removed"])
        relabel_note = (
            f" {relabels_n} of the added/removed were paired as DEFRA relabels "
            f"(same factor, renamed), leaving {added_net} genuinely new and "
            f"{removed_net} genuinely removed."
            if relabels_n
            else ""
        )
        lines.append(
            f"- Version scan: **{ds['flagged']}** factors moved past DEFRA's "
            f"materiality thresholds across {ds['joined']} factors present in both "
            f"years; {ds['added']} added and {ds['removed']} removed "
            f"(not counted as movers).{relabel_note}"
        )
    lines.append("")

    # Relabels (renamed factors, paired)
    relabels = results.get("relabels")
    if relabels is not None and not relabels.empty:
        rel_expl = results.get("relabel_explanations") or []
        # Pairs whose value also crossed threshold get a ⚠ marker and an
        # explanation block below the table.
        material_pairs = {(e["old_activity"], e["new_activity"]) for e in rel_expl}

        lines.append("## Relabels (renamed factors, paired)")
        lines.append("")
        lines.append(
            "These appeared as one activity removed and another added, but are the "
            "same factor renamed. They are paired here so they do not read as real "
            "movement. Only high-confidence name matches (same unit and scope) are "
            "paired; anything unclear is left as added/removed rather than guessed."
        )
        lines.append("")
        lines.append("| Old name → new name | Unit | Scope | kg CO₂e (old → new) | Δ |")
        lines.append("|---|---|---|---|---|")
        for _, r in relabels.iterrows():
            pct = r["pct_change"]
            delta = "same" if (pd.notna(pct) and abs(pct) < 0.05) else f"{_fmt(pct,1)}%"
            if (r["old_activity"], r["new_activity"]) in material_pairs:
                delta += " ⚠ material"
            lines.append(
                f"| {r['old_activity']} → {r['new_activity']} | {r['unit']} "
                f"| {r['scope']} | {_fmt(r['kg_co2e_old'])} → {_fmt(r['kg_co2e_new'])} "
                f"| {delta} |"
            )
        lines.append("")

        # Renamed AND moved: explain the ones that also crossed the threshold.
        if rel_expl:
            lines.append("### Why the renamed factors also moved")
            lines.append("")
            lines.append(
                "These relabels are not just renames: the factor value also crossed "
                "DEFRA's materiality threshold, so each is explained below, grounded "
                "in the changes notes (or reported as unexplained when the notes are "
                "silent)."
            )
            lines.append("")
            for e in rel_expl:
                lines.append(
                    f"**{e['old_activity']} → {e['new_activity']}**  ·  {e['scope']}"
                    f"  ·  {_fmt(e['kg_co2e_old'])} → {_fmt(e['kg_co2e_new'])} "
                    f"({_fmt(e['pct_change'],1)}%)"
                )
                lines.append("")
                lines.append(f"**Why it changed.** {e['plain_english_reason']}")
                lines.append("")
                lines.append(f"**Methodology note.** {e['methodology_note']}")
                lines.append("")
                lines.append(f"**Target impact.** {e['target_impact_flag']}")
                lines.append("")

    # Biggest movers in the footprint
    lines.append("## Biggest contributors to the change")
    lines.append("")
    top = results["top_delta"]
    if top is None or top.empty:
        lines.append("_No computable movers._")
    else:
        lines.append("| Line item | Factor (old → new) | kg CO₂e (old → new) | Δ |")
        lines.append("|---|---|---|---|")
        for _, r in top.iterrows():
            lines.append(
                f"| {r['line_item']} | {_fmt(r['factor_old'])} → {_fmt(r['factor_new'])} "
                f"| {_fmt(r['co2e_old'])} → {_fmt(r['co2e_new'])} | {_fmt(r['line_delta'])} |"
            )
    lines.append("")

    # Explanations (the moat)
    lines.append("## What changed and why (grounded in the DEFRA changes notes)")
    lines.append("")
    if not results["explanations"]:
        lines.append("_No flagged, footprint-relevant factor changes._")
    for e in results["explanations"]:
        lines.append(
            f"### {e['activity']}  ·  {e['scope']}  ·  "
            f"{_fmt(e['kg_co2e_old'])} → {_fmt(e['kg_co2e_new'])} "
            f"({_fmt(e['pct_change'],1)}%)"
        )
        lines.append("")
        lines.append(f"**Why it changed.** {e['plain_english_reason']}")
        lines.append("")
        lines.append(f"**Methodology note.** {e['methodology_note']}")
        lines.append("")
        lines.append(f"**Target impact.** {e['target_impact_flag']}")
        lines.append("")

    # Needs review
    lines.append("## Needs review (not auto-matched, never guessed)")
    lines.append("")
    mc = results["match_coverage"]
    lines.append(
        f"{mc['auto_matched']}/{mc['total_lines']} lines matched automatically "
        f"({mc['auto_match_pct']}%). The following were left for a human:"
    )
    lines.append("")
    review = results["matched_df"][results["matched_df"]["needs_review"]]
    if review.empty:
        lines.append("_None. Every line matched with confidence._")
    else:
        lines.append("| Line item | Unit | Best score | Reason |")
        lines.append("|---|---|---|---|")
        for _, r in review.iterrows():
            lines.append(
                f"| {r['line_item']} | {r['unit']} | {_fmt(r['match_score'],1)} "
                f"| below confidence threshold |"
            )
    lines.append("")
    lines.append("---")
    lines.append(
        "_Generated by EF Version Explainer. Explanations are grounded strictly in "
        "the official DEFRA changes report; where the report is silent, the tool "
        "says so rather than inventing a reason._"
    )
    lines.append("")
    return "\n".join(lines)
