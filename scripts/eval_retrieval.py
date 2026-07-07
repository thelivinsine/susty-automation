"""
eval_retrieval.py - a precision/recall harness for the grounding step.

The tool's whole credibility rests on `changes_pdf.retrieve_passage`: it decides
which official DEFRA change note (if any) explains a given factor. Two failure
modes matter, and they are not equal:

  - A MISS (says "no reason found" when a note exists) is a lost explanation.
    Honest, but weaker output.
  - A WRONG HIT (returns a DIFFERENT factor's note) is far worse: the model then
    explains a change with the wrong official text. That is the one thing the
    "never guess" rule (DECISIONS D2) exists to prevent, and a plain hit-count
    cannot catch it because a wrong hit still counts as "a hit".

So this harness scores against a GOLD set that labels each query with the note
that SHOULD ground it (by a distinctive substring), or `None` for queries the
report deliberately does not explain. It then reports, per case:

  - correct hit   : fired, and the returned passage is the right note
  - wrong hit     : fired, but grounded in the WRONG note  (precision killer)
  - miss          : should have fired, returned nothing     (recall loss)
  - correct refuse: should not fire, returned nothing       (true negative)

and the aggregate precision / recall / refusal-accuracy. Run it directly
(`python scripts/eval_retrieval.py`) to see the table; `tests/test_retrieval_
quality.py` asserts the synthetic gold set stays perfect so a retrieval
regression fails the build.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from changes_pdf import load_change_chunks, retrieve_passage  # noqa: E402

SYNTH = os.path.join(ROOT, "data", "synthetic")


# Each case: the query (as the pipeline passes it, i.e. the full activity name)
# and `expect` = a distinctive substring the RIGHT note must contain, or None
# when the report does not explain this factor and retrieval must return nothing.
# The tricky negatives are deliberate: Petrol shares "(average biofuel blend)"
# with the Diesel note, and Board/Plastics/Water are simply unexplained.
SYNTHETIC_GOLD = [
    # Positives: an official note exists and must be the one retrieved.
    {"query": "Electricity generated - Electricity: UK", "expect": "Electricity generated"},
    {"query": "Liquid fuels - Diesel (average biofuel blend)", "expect": "Diesel"},
    {"query": "Liquid fuels - Fuel oil (mineral)", "expect": "Fuel oil (mineral)"},
    {"query": "Metal - Aluminium - Primary material production", "expect": "Aluminium"},
    # Negatives: no note for this factor -> must refuse, not grab a lookalike.
    {"query": "Liquid fuels - Petrol (average biofuel blend)", "expect": None},
    {"query": "Plastic - Average plastics - Primary material production", "expect": None},
    {"query": "Paper - Board - Primary material production", "expect": None},
    {"query": "Water supply", "expect": None},
]


def classify(expect, passage) -> str:
    """Bucket one retrieval result against its gold label."""
    fired = bool(passage)
    if expect is None:
        return "correct_refuse" if not fired else "wrong_hit"
    if not fired:
        return "miss"
    return "correct_hit" if expect.lower() in passage.lower() else "wrong_hit"


def evaluate(chunks, gold) -> dict:
    """Run every gold case through retrieval and return per-case rows + metrics."""
    rows = []
    for case in gold:
        passage, score = retrieve_passage(chunks, case["query"])
        outcome = classify(case["expect"], passage)
        rows.append(
            {
                "query": case["query"],
                "expect": case["expect"],
                "score": score,
                "got": (passage[:40] + "...") if passage else "(none)",
                "outcome": outcome,
            }
        )

    positives = [r for r in rows if r["expect"] is not None]
    negatives = [r for r in rows if r["expect"] is None]
    fired = [r for r in rows if r["outcome"] in ("correct_hit", "wrong_hit")]
    correct_hits = [r for r in rows if r["outcome"] == "correct_hit"]

    # Precision: of the times retrieval FIRED, how often was the note correct.
    # Recall: of the queries that SHOULD be grounded, how many were, correctly.
    # Refusal accuracy: of the unexplained queries, how many were refused.
    precision = len(correct_hits) / len(fired) if fired else 1.0
    recall = len(correct_hits) / len(positives) if positives else 1.0
    refusal = (
        sum(r["outcome"] == "correct_refuse" for r in negatives) / len(negatives)
        if negatives
        else 1.0
    )
    metrics = {
        "n": len(rows),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "refusal_accuracy": round(refusal, 3),
        "wrong_hits": sum(r["outcome"] == "wrong_hit" for r in rows),
        "misses": sum(r["outcome"] == "miss" for r in rows),
    }
    return {"rows": rows, "metrics": metrics}


def _print_report(title, result) -> None:
    print(title)
    print("-" * len(title))
    for r in result["rows"]:
        exp = r["expect"] if r["expect"] is not None else "(no note)"
        print(
            f"  [{r['outcome']:14}] score={r['score']:.2f}  "
            f"{r['query'][:46]:46}  expect={str(exp)[:22]:22}  got={r['got']}"
        )
    m = result["metrics"]
    print(
        f"  => precision={m['precision']}  recall={m['recall']}  "
        f"refusal_accuracy={m['refusal_accuracy']}  "
        f"wrong_hits={m['wrong_hits']}  misses={m['misses']}"
    )
    print()


def main() -> int:
    chunks = load_change_chunks(
        os.path.join(SYNTH, "changes_2026.pdf"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
    )
    result = evaluate(chunks, SYNTHETIC_GOLD)
    _print_report("Retrieval quality on the synthetic gold set", result)

    m = result["metrics"]
    # A wrong hit is the unacceptable outcome; fail loudly on any.
    if m["wrong_hits"] > 0:
        print(f"retrieval eval: FAIL ({m['wrong_hits']} wrong hit(s) ground a change "
              "in the wrong note).")
        return 1
    print("retrieval eval: clean (no wrong hits; precision and recall as reported).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
