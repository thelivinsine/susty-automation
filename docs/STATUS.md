# Status

Living snapshot. Keep it short. Older handoffs get archived at the bottom.

## Current state
EF Version Explainer MVP is complete and running on the owner's real DEFRA
full-set workbooks (2025 and 2026). Loads 2111/2133 factors across 27 sheets,
diffs them, pairs DEFRA relabels so renames stop reading as added+removed noise,
matches a product BOM (no-guess rule), recomputes the footprint under both years
with coverage, and explains flagged changes grounded in the DEFRA "What's new"
sheet. Renamed-and-moved factors are explained too: a relabel whose value also
crossed the materiality threshold is now routed through the same grounded
explainer, so no material change slips past just because DEFRA renamed it.
Explanation backend is Gemini (or Claude, or offline), selected by API key loaded
from a git-ignored `.env`.

Gates: `pytest` green (26 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite, the material-relabel explanation
path, the retrieval-quality gold set, and loader/diff golden vectors). Two CI
gates are live: the microcopy linter (no-em-dash house rule) and a
retrieval-quality gate that fails the build on any WRONG grounding note, both
wired into pytest and the GitHub Actions workflow; the loader/diff golden vectors
run in the same pytest step. Streamlit app boots clean. Demo footprint on the
sample product: 2.344 to 2.305 kg CO2e, with the UK electricity change explained
from the real DEFRA text. On real data, relabel pairing collapses ~500/500
added/removed to 76 genuinely new and 54 genuinely removed.

## What shipped
- Pipeline: loader, diff, matching, recompute, changes retrieval, explain,
  report, app, run_demo (`src/`, `app.py`, `run_demo.py`).
- Real DEFRA full-set support and "What's new" grounding.
- Provider-agnostic explanation backend (Gemini / Claude / offline) with `.env`
  auto-load.
- Synthetic real-format demo data generator.
- CI quality gates (`.github/workflows/ci.yml`, on every PR into `main`): the
  microcopy linter (`scripts/lint_microcopy.py`) and the retrieval-quality gate
  (`scripts/eval_retrieval.py`), both also run by pytest.
- Relabel matching (`src/relabel.py`): pairs DEFRA renames across years with a
  leaf-substitution guard, surfaced as a review-only section (DECISIONS D9).
- Renamed-and-moved explanations: material relabels routed through the grounded
  explainer, with one shared `diff.is_material` rule; surfaced in report, app,
  and run_demo (DECISIONS D10).
- Retrieval-quality harness (`scripts/eval_retrieval.py`): precision/recall over a
  labelled gold set; found and fixed a wrong-grounding defect where a fuzzy title
  match on shared boilerplate fired a hit on the wrong note (DECISIONS D11).
- Loader/diff golden vectors (`tests/test_golden_loader.py`): pin the exact
  normalized output for a frozen, code-built fixture that exercises every tricky
  parsing path (DECISIONS D12).
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
- Semantic relabels with low string overlap (Incineration -> Combustion) still
  read as added/removed; would need DEFRA's own relabel notes.
- More CI gates: a dependency-audit gate (loader/diff golden vectors now done).
- Package manager pin + lockfile for supply-chain hygiene. Not done (pip +
  requirements.txt only so far).
- Live Gemini runs only on the owner's machine (endpoint blocked in the web
  sandbox).

## Resume here
Two most recent handoffs:

- H7 (2026-07-07): Added loader/diff golden-vector tests (DECISIONS D12). A small,
  frozen, code-built fixture (an independent oracle, not the synthetic generator)
  pins the EXACT normalized loader output and diff results, exercising scope-from-
  metadata, messy-scope normalization, forward-fill, the ignored Year column, unit
  normalization, (activity, unit) dedup, and super-header block expansion. Runs in
  the existing pytest CI step, so it gates every PR without needing the big data
  files. 26 tests green.
- H6 (2026-07-07): Built the retrieval-quality harness (DECISIONS D11). Scores
  `retrieve_passage` against a labelled gold set for precision/recall/refusal, and
  gates on any WRONG grounding note. Found and fixed a real defect: a fuzzy TITLE
  match on shared boilerplate fired a hit on the wrong note (petrol -> diesel note;
  real "Plug-in Hybrid" -> a "Calculating emissions" heading). Made keyword overlap
  the gate; 7 real-data false positives became honest "no reason found". 22 tests.

Next likely task: a dependency-audit gate (e.g. pip-audit in CI), or tackle
semantic relabels (low string overlap, e.g. Incineration -> Combustion) using
DEFRA's own relabel notes.
