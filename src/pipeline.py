"""
pipeline.py — glue that runs the whole thing so app.py and run_demo.py stay thin.

run_pipeline(...) -> dict with every artifact the UI / report needs.
"""

from __future__ import annotations

import pandas as pd

from loader import load_defra
from diff import diff_versions, is_material
from relabel import detect_relabels, group_relabels, relabel_head
from matching import match_bom, coverage_summary
from recompute import recompute, top_delta_lines
from changes_pdf import load_change_chunks, retrieve_passage
from explain import explain_change


def _family_movement(pcts, n_rose: int, n_fell: int) -> str:
    """Honest sentence about how a rename family's material values moved. Reports
    the range and the up/down split, never a single made-up delta."""
    lo, hi = min(pcts), max(pcts)
    span = f"by {lo:+.1f}%" if abs(lo - hi) < 0.05 else f"from {lo:+.1f}% to {hi:+.1f}%"
    n = len(pcts)
    noun = "sub-factor" if n == 1 else "sub-factors"
    return (
        f"{n} {noun} in this rename crossed DEFRA's materiality threshold; "
        f"their values moved {span} ({n_rose} rose, {n_fell} fell)."
    )


def _family_target_flag(group, context) -> str:
    """Family-level target wording. A family can move in both directions, so a
    single 'this factor rose' claim would be dishonest: say so when it is mixed."""
    rose = int((group["pct_change"] > 0).sum())
    fell = int((group["pct_change"] < 0).sum())
    breaches = (context or {}).get("breaches_baseline")
    if rose and fell:
        return (
            "Mixed direction within the family: some sub-factors rose and some "
            "fell. Review each against active targets."
        )
    if rose and breaches:
        return (
            "These factors increased, adding to a product footprint rise that "
            "would breach a flat baseline. Flag for target review."
        )
    if rose:
        return "These factors increased; product footprint stays within a flat baseline."
    if fell:
        return "These factors decreased, easing the product footprint."
    return "Immaterial at the product level."


def run_pipeline(
    defra_old_path: str,
    defra_new_path: str,
    changes_pdf_path: str | None,
    bom_path_or_df,
    old_label: str = "old",
    new_label: str = "new",
    explain_flagged_only: bool = True,
) -> dict:
    """Run loader -> diff -> match -> recompute -> explain and return everything."""
    df_old = load_defra(defra_old_path, old_label)
    df_new = load_defra(defra_new_path, new_label)
    diff_df = diff_versions(df_old, df_new)

    # Pair DEFRA renames so they stop reading as spurious added + removed factors.
    relabels_df = detect_relabels(diff_df)

    bom_df = (
        bom_path_or_df
        if isinstance(bom_path_or_df, pd.DataFrame)
        else pd.read_csv(bom_path_or_df)
    )
    matched_df = match_bom(bom_df, df_old)
    match_cov = coverage_summary(matched_df)

    line_table, summary = recompute(matched_df, diff_df)

    # A flat baseline = last year's total. A footprint rise breaches it.
    breaches_baseline = summary["total_new"] > summary["total_old"]
    context = {
        "breaches_baseline": breaches_baseline,
        "product_pct_delta": summary["pct_delta"],
    }

    # Explain only the flagged factors that actually appear in THIS product's
    # footprint (that's what the client cares about). Grounding source: a real
    # Major Changes PDF if provided, else the new workbook's "What's new" sheet.
    chunks = load_change_chunks(changes_pdf_path, defra_new_path)

    included = line_table[line_table["included"]]
    included_activities = set(included["matched_activity"].dropna())

    # How much each flagged factor moved THIS product's footprint (kg CO2e),
    # summed across every BOM line that matched it. This is what makes the report
    # about the user's own number: a 3% move on the factor that is 60% of their
    # footprint matters more than a 40% move on a 0.1% line. We rank the
    # explanations by it and show it next to each.
    impact_by_activity = (
        included.groupby("matched_activity")["line_delta"].sum().to_dict()
        if not included.empty
        else {}
    )
    total_move = abs(summary.get("absolute_delta") or 0.0)

    explanations = []
    for _, row in diff_df.iterrows():
        if not row["flagged"]:
            continue
        if explain_flagged_only and row["activity"] not in included_activities:
            continue
        passage, score = retrieve_passage(chunks, row["activity"]) if chunks else ("", 0.0)
        result = explain_change(
            material=row["activity"],
            old=row["kg_co2e_old"],
            new=row["kg_co2e_new"],
            pct=row["pct_change"],
            retrieved_text=passage,
            context=context,
        )
        impact = float(impact_by_activity.get(row["activity"], 0.0))
        explanations.append(
            {
                "activity": row["activity"],
                "scope": row["scope"],
                "kg_co2e_old": row["kg_co2e_old"],
                "kg_co2e_new": row["kg_co2e_new"],
                "pct_change": row["pct_change"],
                "footprint_impact": round(impact, 4),
                "footprint_impact_pct": (
                    round(impact / total_move * 100, 1) if total_move else None
                ),
                "retrieval_score": score,
                **result,
            }
        )

    # Lead with the changes that moved the user's OWN footprint the most.
    explanations.sort(key=lambda e: abs(e["footprint_impact"]), reverse=True)

    # A relabel is a SAME factor, renamed. Most renames barely move the value, but
    # some cross DEFRA's materiality threshold too (renamed AND moved). Those were
    # shown in the relabels table with their delta but never explained. Explain
    # them here, grounded the same way as the flagged factors, so no material
    # change escapes the "explain the delta" promise just because it was renamed.
    #
    # But on real data ONE rename spans dozens of near-identical variants (the HGV
    # relabel across weight class / fuel / unit), which produced ~420 all-but-
    # identical blocks and ~420 API calls per run. So we group by rename FAMILY
    # (D10 refined): one grounded explanation per family, with value movement
    # reported as an honest range and up/down split rather than a single made-up
    # delta. Grounding (D2) is still enforced per call.
    material = (
        relabels_df[
            [is_material(p, s) for p, s in zip(relabels_df["pct_change"], relabels_df["scope"])]
        ]
        if not relabels_df.empty
        else relabels_df
    )
    relabel_explanations = []
    if not material.empty:
        fam = material.copy()
        fam["_oh"] = fam["old_activity"].map(relabel_head)
        fam["_nh"] = fam["new_activity"].map(relabel_head)
        for (oh, nh, scope), g in fam.groupby(["_oh", "_nh", "scope"], sort=False):
            n_var = len(g)
            pcts = [p for p in g["pct_change"] if pd.notna(p)]
            # The change note may sit under either the old or the new head name;
            # retrieve on both and keep the stronger hit. All variants share the
            # head, so one retrieval covers the family. Empty -> honest "no reason".
            passage, score = "", 0.0
            if chunks:
                for name in (nh, oh):
                    p, s = retrieve_passage(chunks, name)
                    if s > score:
                        passage, score = p, s
            # A representative member (biggest move) gives explain_change real
            # numbers; the reason is grounded in the shared rename note, so it is
            # valid for the whole family. Family-level target flag overrides the
            # per-factor one (a family can move both ways).
            rep = g.loc[g["pct_change"].abs().idxmax()]
            multi = n_var > 1
            result = explain_change(
                material=f"{oh} → {nh}" if multi else f"{rep['old_activity']} → {rep['new_activity']}",
                old=rep["kg_co2e_old"],
                new=rep["kg_co2e_new"],
                pct=rep["pct_change"],
                retrieved_text=passage,
                context=context,
            )
            n_rose = int((g["pct_change"] > 0).sum())
            n_fell = int((g["pct_change"] < 0).sum())
            relabel_explanations.append(
                {
                    "old_name": oh if multi else rep["old_activity"],
                    "new_name": nh if multi else rep["new_activity"],
                    "scope": scope,
                    "units": ", ".join(sorted(g["unit"].astype(str).unique())),
                    "n_variants": n_var,
                    "n_rose": n_rose,
                    "n_fell": n_fell,
                    "pct_min": min(pcts),
                    "pct_max": max(pcts),
                    "value_movement": _family_movement(pcts, n_rose, n_fell),
                    "retrieval_score": score,
                    "plain_english_reason": result["plain_english_reason"],
                    "methodology_note": result["methodology_note"],
                    "target_impact_flag": _family_target_flag(g, context),
                }
            )

    # Collapse the per-variant relabel pairs into readable rename families.
    relabel_groups = group_relabels(relabels_df)

    added_raw = int((diff_df["status"] == "added").sum())
    removed_raw = int((diff_df["status"] == "removed").sum())
    n_relabels = len(relabels_df)
    diff_stats = {
        "factors_old": len(df_old),
        "factors_new": len(df_new),
        "joined": int((diff_df["status"].isin(["changed", "unchanged"])).sum()),
        "flagged": int(diff_df["flagged"].sum()),
        "added": added_raw,
        "removed": removed_raw,
        "relabels": n_relabels,
        # How many rename FAMILIES those pairs collapse into (what the reader sees).
        "relabel_families": len(relabel_groups),
        "material_relabel_families": len(relabel_explanations),
        # Net of paired renames: what is genuinely new / retired.
        "added_net": added_raw - n_relabels,
        "removed_net": removed_raw - n_relabels,
    }

    return {
        "diff_df": diff_df,
        "relabels": relabels_df,
        "relabel_groups": relabel_groups,
        "diff_stats": diff_stats,
        "matched_df": matched_df,
        "match_coverage": match_cov,
        "line_table": line_table,
        "summary": summary,
        "top_delta": top_delta_lines(line_table),
        "explanations": explanations,
        "relabel_explanations": relabel_explanations,
        "context": context,
        "labels": {"old": old_label, "new": new_label},
    }
