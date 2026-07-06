"""
pipeline.py — glue that runs the whole thing so app.py and run_demo.py stay thin.

run_pipeline(...) -> dict with every artifact the UI / report needs.
"""

from __future__ import annotations

import pandas as pd

from loader import load_defra
from diff import diff_versions
from matching import match_bom, coverage_summary
from recompute import recompute, top_delta_lines
from changes_pdf import extract_changes_text, chunk_changes, retrieve_passage
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
    # footprint (that's what the client cares about).
    chunks = []
    if changes_pdf_path:
        try:
            chunks = chunk_changes(extract_changes_text(changes_pdf_path))
        except Exception:
            chunks = []

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

    return {
        "diff_df": diff_df,
        "matched_df": matched_df,
        "match_coverage": match_cov,
        "line_table": line_table,
        "summary": summary,
        "top_delta": top_delta_lines(line_table),
        "explanations": explanations,
        "context": context,
        "labels": {"old": old_label, "new": new_label},
    }
