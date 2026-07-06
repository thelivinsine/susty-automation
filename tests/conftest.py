"""Shared test setup: make src importable and ensure synthetic data exists."""

import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

SYNTH = os.path.join(ROOT, "data", "synthetic")


def _ensure_synthetic_data():
    needed = ["defra_2025.xlsx", "defra_2026.xlsx", "changes_2026.pdf", "sample_bom.csv"]
    if all(os.path.exists(os.path.join(SYNTH, n)) for n in needed):
        return
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "make_synthetic_data.py")],
        check=True,
    )


_ensure_synthetic_data()
