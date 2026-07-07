"""
pipeline.py — glue that runs the whole thing so app.py and run_demo.py stay thin.

run_pipeline(...) -> dict with every artifact the UI / report needs.
"""

from __future__ import annotations

import pandas as pd

from loader import load_defra
from diff import diff_versions, is_material
from relabel import detect_relabels
from matching import match_bom, coverage_summary
from recompute import recompute, top_delta_lines
from changes_pdf import load_change_chunks, retrieve_passage
from explain import explain_change


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

    included_activities = set(
        line_table.loc[line_table["included"], "matched_activity"].dropna()
    )
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
        explanations.append(
            {
                "activity": row["activity"],
                "scope": row["scope"],
                "kg_co2e_old": row["kg_co2e_old"],
                "kg_co2e_new": row["kg_co2e_new"],
                "pct_change": row["pct_change"],
                "retrieval_score": score,
                **result,
            }
        )

    # A relabel is a SAME factor, renamed. Most renames barely move the value, but
    # some cross DEFRA's materiality threshold too (renamed AND moved). Those were
    # shown in the relabels table with their delta but never explained. Explain
    # them here, grounded the same way as the flagged factors, so no material
    # change escapes the "explain the delta" promise just because it was renamed.
    relabel_explanations = []
    for _, rel in relabels_df.iterrows():
        if not is_material(rel["pct_change"], rel["scope"]):
            continue
        # The change note may sit under either the old or the new name; retrieve
        # on both and keep the stronger hit. Empty passage -> honest "no reason".
        passage, score = "", 0.0
        if chunks:
            for name in (rel["new_activity"], rel["old_activity"]):
                p, s = retrieve_passage(chunks, name)
                if s > score:
                    passage, score = p, s
        result = explain_change(
            material=f"{rel['old_activity']} → {rel['new_activity']}",
            old=rel["kg_co2e_old"],
            new=rel["kg_co2e_new"],
            pct=rel["pct_change"],
            retrieved_text=passage,
            context=context,
        )
        relabel_explanations.append(
            {
                "old_activity": rel["old_activity"],
                "new_activity": rel["new_activity"],
                "scope": rel["scope"],
                "kg_co2e_old": rel["kg_co2e_old"],
                "kg_co2e_new": rel["kg_co2e_new"],
                "pct_change": rel["pct_change"],
                "retrieval_score": score,
                **result,
            }
        )

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
        # Net of paired renames: what is genuinely new / retired.
        "added_net": added_raw - n_relabels,
        "removed_net": removed_raw - n_relabels,
    }

    return {
        "diff_df": diff_df,
        "relabels": relabels_df,
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
