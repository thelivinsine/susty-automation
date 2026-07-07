"""
paths.py — decide whether to use real DEFRA files (if present in data/) or the
committed synthetic demo files. Real files always win.

Real full-set workbooks are recognized by common gov.uk names, e.g.
    data/ghg-conversion-factors-2025-full-set.xlsx
    data/ghg-conversion-factors-2026-full-set.xlsx
or the simple aliases data/defra_2025.xlsx / data/defra_2026.xlsx.
"""

from __future__ import annotations

import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SYNTH = os.path.join(DATA, "synthetic")


def _find_real_workbook(year: str) -> str | None:
    """Find a real DEFRA workbook for a given year by common naming patterns."""
    candidates = [
        os.path.join(DATA, f"defra_{year}.xlsx"),
        os.path.join(DATA, f"ghg-conversion-factors-{year}-full-set.xlsx"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Fallback: any xlsx in data/ whose name contains the year (but not synthetic).
    for path in sorted(glob.glob(os.path.join(DATA, f"*{year}*.xlsx"))):
        return path
    return None


def _find_real_changes_pdf() -> str | None:
    for name in ["defra_changes_2026.pdf", "major-changes-2026.pdf"]:
        p = os.path.join(DATA, name)
        if os.path.exists(p):
            return p
    hits = sorted(glob.glob(os.path.join(DATA, "*change*.pdf")))
    return hits[0] if hits else None


def resolve_paths(old_year: str = "2025", new_year: str = "2026") -> dict:
    """Resolve inputs, preferring real files in data/ over the synthetic demo set."""
    real_old = _find_real_workbook(old_year)
    real_new = _find_real_workbook(new_year)
    using_real = bool(real_old and real_new)

    if using_real:
        old = real_old
        new = real_new
    else:
        old = os.path.join(SYNTH, "defra_2025.xlsx")
        new = os.path.join(SYNTH, "defra_2026.xlsx")

    # Grounding: a real Major Changes PDF if present; otherwise the pipeline uses
    # the new workbook's own "What's new" sheet (handled downstream).
    pdf = _find_real_changes_pdf()
    if pdf is None and not using_real:
        pdf = os.path.join(SYNTH, "changes_2026.pdf")

    # BOM: prefer a real one in data/, else the matching sample for the dataset.
    real_bom = os.path.join(DATA, "sample_bom.csv")
    if os.path.exists(real_bom):
        bom = real_bom
    elif using_real:
        bom = os.path.join(DATA, "sample_bom_real.csv")
        if not os.path.exists(bom):
            bom = os.path.join(SYNTH, "sample_bom.csv")
    else:
        bom = os.path.join(SYNTH, "sample_bom.csv")

    return {
        "defra_old": old,
        "defra_new": new,
        "changes_pdf": pdf,          # may be None -> use What's new sheet
        "bom": bom,
        "using_real_data": using_real,
        "old_label": old_year,
        "new_label": new_year,
    }
