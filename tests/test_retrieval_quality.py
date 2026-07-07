"""
The retrieval-quality gate as a test, so a regression in the grounding step
(`changes_pdf.retrieve_passage`) fails the build. This guards the tool's wedge
directly: grounding a factor change in the WRONG official note is the one failure
the "never guess" rule (DECISIONS D2) must prevent, and a plain hit-count would
not catch it. See scripts/eval_retrieval.py for the harness and the gold set.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from changes_pdf import load_change_chunks  # noqa: E402
from eval_retrieval import SYNTHETIC_GOLD, evaluate  # noqa: E402

SYNTH = os.path.join(ROOT, "data", "synthetic")


def _synthetic_result():
    chunks = load_change_chunks(
        os.path.join(SYNTH, "changes_2026.pdf"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
    )
    return evaluate(chunks, SYNTHETIC_GOLD)


def test_no_wrong_hits_on_the_gold_set():
    # The unacceptable outcome: a change grounded in a different factor's note.
    result = _synthetic_result()
    wrong = [r for r in result["rows"] if r["outcome"] == "wrong_hit"]
    assert wrong == [], (
        "Retrieval grounded a change in the WRONG note:\n"
        + "\n".join(f"  {r['query']} -> {r['got']}" for r in wrong)
    )


def test_gold_set_precision_and_recall_are_perfect():
    m = _synthetic_result()["metrics"]
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["refusal_accuracy"] == 1.0


def test_lookalike_negative_is_refused_not_confused():
    # The sharp case the harness exists for: "Petrol (average biofuel blend)" is
    # NOT explained, but shares "(average biofuel blend)" with the Diesel note.
    # It must be refused rather than grounded in the Diesel text.
    rows = {r["query"]: r for r in _synthetic_result()["rows"]}
    petrol = rows["Liquid fuels - Petrol (average biofuel blend)"]
    assert petrol["outcome"] == "correct_refuse"
    assert "diesel" not in petrol["got"].lower()
