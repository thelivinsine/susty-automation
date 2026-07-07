"""
run_demo.py — run the WHOLE EF Version Explainer pipeline end-to-end with one
command, printing each stage's summary and writing a Markdown report.

    python run_demo.py

Uses real DEFRA files if you dropped them into data/ (defra_2025.xlsx,
defra_2026.xlsx, defra_changes_2026.pdf, sample_bom.csv); otherwise it uses the
committed SYNTHETIC demo data (run scripts/make_synthetic_data.py first).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from paths import resolve_paths          # noqa: E402
from pipeline import run_pipeline         # noqa: E402
from report import build_markdown_report  # noqa: E402


def _line(char="─", n=70):
    print(char * n)


def main() -> None:
    p = resolve_paths()
    _line("=")
    print("EF VERSION EXPLAINER — END-TO-END DEMO")
    _line("=")
    kind = "REAL DEFRA data" if p["using_real_data"] else "SYNTHETIC demo data"
    print(f"Data source: {kind}")
    print(f"  old workbook : {p['defra_old']}")
    print(f"  new workbook : {p['defra_new']}")
    print(f"  changes PDF  : {p['changes_pdf']}")
    print(f"  product BOM  : {p['bom']}")
    api = "yes (real Claude call)" if os.getenv("ANTHROPIC_API_KEY") else "no (offline explainer)"
    print(f"  ANTHROPIC_API_KEY set: {api}")
    print()

    results = run_pipeline(
        defra_old_path=p["defra_old"],
        defra_new_path=p["defra_new"],
        changes_pdf_path=p["changes_pdf"],
        bom_path_or_df=p["bom"],
        old_label=p["old_label"],
        new_label=p["new_label"],
    )

    s = results["summary"]
    ds = results["diff_stats"]
    _line()
    print("STAGE 1-2  Loaded both workbooks and diffed them")
    print(f"  factors: {ds['factors_old']} ({p['old_label']}) vs {ds['factors_new']} ({p['new_label']}), "
          f"{ds['joined']} matched across both years")
    print(f"  material movers (past DEFRA thresholds): {ds['flagged']}")
    print(f"  structural: {ds['added']} added, {ds['removed']} removed "
          f"(includes DEFRA relabels, not counted as movers)")
    _line()
    print("STAGE 3    Matched product BOM to factors")
    mc = results["match_coverage"]
    print(f"  auto-matched {mc['auto_matched']}/{mc['total_lines']} ({mc['auto_match_pct']}%), "
          f"needs review: {mc['needs_review']}")
    _line()
    print("STAGE 4    Recomputed footprint under both versions")
    print(f"  {s['total_old']} → {s['total_new']} kg CO2e "
          f"({'+' if (s['pct_delta'] or 0) >= 0 else ''}{s['pct_delta']}%), "
          f"coverage {s['coverage_pct']}%")
    _line()
    print("STAGE 5    Explained flagged changes (grounded in changes PDF)")
    for e in results["explanations"]:
        print(f"  • {e['activity']} ({e['pct_change']:+.1f}%)")
        print(f"      {e['plain_english_reason'][:100]}"
              + ("..." if len(e['plain_english_reason']) > 100 else ""))
    _line()

    report_md = build_markdown_report(results)
    os.makedirs("reports", exist_ok=True)
    out_path = os.path.join("reports", "demo_report.md")
    with open(out_path, "w") as f:
        f.write(report_md)
    print(f"STAGE 6    Wrote report -> {out_path}")
    _line("=")
    print("DEMO OK — open the report above, or run:  streamlit run app.py")


if __name__ == "__main__":
    main()
