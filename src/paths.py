"""
paths.py — decide whether to use real DEFRA files (if the user dropped them into
data/) or the committed synthetic demo files. Real files always win.
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SYNTH = os.path.join(DATA, "synthetic")


def _pick(real_name: str, synth_name: str) -> tuple[str, bool]:
    """Return (path, is_real). Prefer data/<real_name>, else data/synthetic/<synth_name>."""
    real = os.path.join(DATA, real_name)
    if os.path.exists(real):
        return real, True
    return os.path.join(SYNTH, synth_name), False


def resolve_paths() -> dict:
    """Resolve the four inputs, preferring real files over synthetic demo files."""
    old, old_real = _pick("defra_2025.xlsx", "defra_2025.xlsx")
    new, new_real = _pick("defra_2026.xlsx", "defra_2026.xlsx")
    pdf, pdf_real = _pick("defra_changes_2026.pdf", "changes_2026.pdf")
    bom, bom_real = _pick("sample_bom.csv", "sample_bom.csv")
    return {
        "defra_old": old,
        "defra_new": new,
        "changes_pdf": pdf,
        "bom": bom,
        "using_real_data": all([old_real, new_real]),
        "old_label": "2025",
        "new_label": "2026",
    }
