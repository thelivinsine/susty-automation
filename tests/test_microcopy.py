"""
The microcopy gate as a test, so `pytest` fails locally on a stray em dash
(not only in CI). See scripts/lint_microcopy.py for the rule and its boundary.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lint_microcopy import lint  # noqa: E402


def test_no_em_dashes_in_visible_copy():
    violations = lint()
    assert violations == [], (
        "Em dashes found in visible copy. Rewrite with a comma, colon, period, "
        "or parentheses (en dash is fine):\n"
        + "\n".join(f"  {rel}:{line}: {msg}" for rel, line, msg in violations)
    )
