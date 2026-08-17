"""
pipeline.py — glue that runs the whole thing so app.py and run_demo.py stay thin.

run_pipeline(...) -> dict with every artifact the UI / report needs.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd

from loader import load_defra
from diff import diff_versions, is_material
from relabel import detect_relabels, group_relabels, relabel_head
from matching import match_bom, coverage_summary
from recompute import recompute, top_delta_lines
from changes_pdf import load_change_chunks, retrieve_citation, retrieve_passage
from explain import explain_change
from paths import DATA


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


def _cite_for(citation, source_file, source_sheet, source_row):
    """Assemble what the memo needs to show its work for one factor change.

    Two independent things are being cited and they can fail independently:
      - the FACTOR's own source (which workbook, sheet and row it was read from),
        which we always have once the loader recorded it, and
      - the DEFRA NOTE the explanation was grounded in, which exists only when a
        passage actually cleared the retrieval bar.

    A missing piece is reported as missing (DECISIONS D2). Nothing here is
    reconstructed, inferred or filled in from a filename.
    """
    def _row(value):
        try:
            return int(value) if value is not None and not pd.isna(value) else None
        except (TypeError, ValueError):
            return None

    return {
        "factor_source_file": source_file or "",
        "factor_source_sheet": source_sheet or "",
        "factor_source_row": _row(source_row),
        "note": citation,
    }


def compare_versions(
    defra_old_path: str,
    defra_new_path: str,
    old_label: str = "old",
    new_label: str = "new",
) -> dict:
    """Load both releases and diff them. No inventory, no model, no API key.

    This is the half of run_pipeline that does not need the user's product, and
    it is split out because it is the half a first-time visitor should be able
    to use immediately. Loading two workbooks and joining them is arithmetic on
    local files: there is no reason to make someone upload a bill of materials
    before they are allowed to look at what DEFRA changed.

    Adds one column diff_versions does not produce: `renamed`, true where the
    relabel pairing matched this row to its counterpart in the other release.
    It is laid on top rather than folded into `status` on purpose. Downstream
    counts (diff_stats, added_net) read `status`, so overwriting it would move
    numbers that are correct, and a rename genuinely IS an added row and a
    removed row that turned out to be the same factor twice.
    """
    df_old = load_defra(defra_old_path, old_label)
    df_new = load_defra(defra_new_path, new_label)
    diff_df = diff_versions(df_old, df_new)

    # Pair DEFRA renames so they stop reading as spurious added + removed factors.
    relabels_df = detect_relabels(diff_df)
    relabel_groups = group_relabels(relabels_df)

    paired = set()
    if not relabels_df.empty:
        paired = set(relabels_df["old_activity"]) | set(relabels_df["new_activity"])
    diff_df = diff_df.copy()
    diff_df["renamed"] = diff_df["activity"].isin(paired) & diff_df["status"].isin(
        ["added", "removed"]
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
        # How many rename FAMILIES those pairs collapse into (what the reader sees).
        "relabel_families": len(relabel_groups),
        # Net of paired renames: what is genuinely new / retired.
        "added_net": added_raw - n_relabels,
        "removed_net": removed_raw - n_relabels,
    }

    return {
        "df_old": df_old,
        "df_new": df_new,
        "diff_df": diff_df,
        "relabels": relabels_df,
        "relabel_groups": relabel_groups,
        "diff_stats": diff_stats,
        "labels": {"old": old_label, "new": new_label},
    }


# ---------------------------------------------------------------------------
# The committed register snapshot: a fast path around parsing two full-set
# workbooks (about 15 seconds, measured) just to paint the front door.
# ---------------------------------------------------------------------------

SNAPSHOT_DIRNAME = "register_snapshot"


def snapshot_dir() -> str:
    """Where the committed register snapshot lives: data/register_snapshot/."""
    return os.path.join(DATA, SNAPSHOT_DIRNAME)


def _file_hash(path: str) -> str:
    """SHA256 of a file's actual bytes. Proves which exact workbook a snapshot
    was built from, rather than trusting a filename or a timestamp."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_snapshot(comparison: dict, old_path: str, new_path: str,
                    out_dir: str | None = None) -> str:
    """Write the joined diff, plus the provenance that proves it is current, to
    disk. Returns the directory written to.

    Only what the front door needs is stored (diff_df, diff_stats). The
    product-report path still parses the workbooks live: it needs df_old,
    relabels and relabel_groups too, and it sits behind a Run button where a
    wait is already the expectation, so there is nothing to fix there.
    """
    out_dir = out_dir or snapshot_dir()
    os.makedirs(out_dir, exist_ok=True)

    diff_df = comparison["diff_df"]
    diff_df.to_parquet(os.path.join(out_dir, "diff.parquet"), index=False)

    meta = {
        "old_file": os.path.basename(old_path),
        "old_sha256": _file_hash(old_path),
        "old_bytes": os.path.getsize(old_path),
        "new_file": os.path.basename(new_path),
        "new_sha256": _file_hash(new_path),
        "new_bytes": os.path.getsize(new_path),
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "diff_rows": len(diff_df),
        "diff_stats": comparison["diff_stats"],
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return out_dir


def load_snapshot(old_path: str, new_path: str,
                   snap_dir: str | None = None) -> dict | None:
    """Load the committed snapshot IF it still matches these exact workbooks.

    Returns {"diff_df", "diff_stats"} on a match. Returns None on anything
    else: a missing file, an unreadable one, or a hash mismatch. There is no
    partial trust and no repair here on purpose: a snapshot that might be stale
    must never be served as if it were current, so the only two outcomes are
    "the real thing" or "the caller falls back to parsing it live". The hash
    check costs about 20ms for the pair, which is what makes it safe to run on
    every cold visit rather than trusting a build timestamp.
    """
    snap_dir = snap_dir or snapshot_dir()
    meta_path = os.path.join(snap_dir, "meta.json")
    diff_path = os.path.join(snap_dir, "diff.parquet")
    if not (os.path.exists(meta_path) and os.path.exists(diff_path)):
        return None
    if not (os.path.exists(old_path) and os.path.exists(new_path)):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if _file_hash(old_path) != meta.get("old_sha256"):
            return None
        if _file_hash(new_path) != meta.get("new_sha256"):
            return None
        diff_df = pd.read_parquet(diff_path)
    except Exception:
        return None

    return {"diff_df": diff_df, "diff_stats": meta["diff_stats"]}


def cited_reasons(diff_df, changes_pdf_path, new_workbook_path) -> list[dict]:
    """DEFRA's own words for every flagged factor, no BOM and no model call.

    This is the front door's half of "explain the delta": the diff already says
    WHAT moved, this says WHY, quoted verbatim from the DEFRA notes. It shares
    the retrieval path the product report uses (`retrieve_citation`, which
    shares `_best_chunk` with `retrieve_passage`), so DECISIONS D11 (the
    wrong-note guard) protects this surface exactly as it protects the memo.
    `explain_change` is never imported here: nothing is model-written, nothing
    costs an API call, so every visitor sees the same thing.

    Returns one record per row where `flagged` is true, largest movement first
    (the order `diff_df` already carries). `explained=False` with an empty quote
    means the notes do not cover this one, which is `retrieve_citation`
    returning None, not a failure to look.
    """
    flagged = diff_df[diff_df["flagged"]]
    if flagged.empty:
        return []

    chunks = load_change_chunks(changes_pdf_path, new_workbook_path)

    out = []
    for _, row in flagged.iterrows():
        citation = retrieve_citation(chunks, row["activity"]) if chunks else None
        out.append({
            "activity": row["activity"],
            "scope": row["scope"],
            "unit": row["unit"],
            "kg_co2e_old": row["kg_co2e_old"],
            "kg_co2e_new": row["kg_co2e_new"],
            "pct_change": row["pct_change"],
            "explained": citation is not None,
            "heading": (citation or {}).get("heading", ""),
            "quote": (citation or {}).get("quote", ""),
            "source": (citation or {}).get("source", ""),
            "source_file": (citation or {}).get("source_file", ""),
            "score": (citation or {}).get("score", 0.0),
        })
    return out


def run_pipeline(
    defra_old_path: str,
    defra_new_path: str,
    changes_pdf_path: str | None,
    bom_path_or_df,
    old_label: str = "old",
    new_label: str = "new",
    explain_flagged_only: bool = True,
    use_ai: bool = True,
    comparison: dict | None = None,
) -> dict:
    """Run loader -> diff -> match -> recompute -> explain and return everything.

    `use_ai=False` forces the free offline explainer even when an API key is set.
    The app passes this for visitors who are not a signed-in, approved user, so the
    tool is open to everyone while the paid model stays behind sign-in.

    `comparison` lets a caller that already ran `compare_versions` (the app's
    section 1, which a visitor sees before ever pressing Run) hand that work
    straight in, rather than paying to parse both workbooks a second time.
    Trusted only when its own labels match the ones this call was asked for;
    anything else is treated as if nothing were passed, so a stale or
    mismatched comparison can never produce a silently wrong result.
    """
    force_offline = not use_ai
    # Loading, diffing and pairing the renames is the same work the standalone
    # comparison does. Reuse it when a matching one was handed in; otherwise do
    # it here, exactly as before.
    if comparison is None or comparison.get("labels") != {"old": old_label, "new": new_label}:
        comparison = compare_versions(defra_old_path, defra_new_path, old_label, new_label)
    df_old = comparison["df_old"]
    diff_df = comparison["diff_df"]
    relabels_df = comparison["relabels"]
    relabel_groups = comparison["relabel_groups"]

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
        # The same winning chunk, kept in pieces so the memo can show what the
        # explanation was grounded in. `retrieve_citation` shares `_best_chunk`
        # with `retrieve_passage`, so the quote a reader checks is always the
        # passage the model actually read.
        citation = retrieve_citation(chunks, row["activity"]) if chunks else None
        result = explain_change(
            material=row["activity"],
            old=row["kg_co2e_old"],
            new=row["kg_co2e_new"],
            pct=row["pct_change"],
            retrieved_text=passage,
            context=context,
            force_offline=force_offline,
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
                "citation": _cite_for(citation, row["source_file"], row["source_sheet"], row["source_row"]),
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
            passage, score, citation = "", 0.0, None
            if chunks:
                for name in (nh, oh):
                    p, s = retrieve_passage(chunks, name)
                    if s > score:
                        passage, score = p, s
                        citation = retrieve_citation(chunks, name)
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
                force_offline=force_offline,
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
                    # A rename family spans many rows across the workbook, so
                    # there is no single row to point at. The NOTE is still
                    # citable, and that is the claim being made.
                    "citation": _cite_for(citation, "", "", None),
                    "plain_english_reason": result["plain_english_reason"],
                    "methodology_note": result["methodology_note"],
                    "target_impact_flag": _family_target_flag(g, context),
                }
            )

    diff_stats = {
        **comparison["diff_stats"],
        "material_relabel_families": len(relabel_explanations),
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
