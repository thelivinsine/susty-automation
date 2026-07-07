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

Gates: `pytest` green (19 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite, and the material-relabel explanation
path). First CI gate is live: a microcopy linter that enforces the no-em-dash
house rule, wired into pytest and a GitHub Actions workflow. Streamlit app boots
clean. Demo footprint on the sample product: 2.344 to 2.305 kg CO2e, with the UK
electricity change explained from the real DEFRA text. On real data, relabel
pairing collapses ~500/500 added/removed to 76 genuinely new and 54 genuinely
removed.

## What shipped
- Pipeline: loader, diff, matching, recompute, changes retrieval, explain,
  report, app, run_demo (`src/`, `app.py`, `run_demo.py`).
- Real DEFRA full-set support and "What's new" grounding.
- Provider-agnostic explanation backend (Gemini / Claude / offline) with `.env`
  auto-load.
- Synthetic real-format demo data generator.
- First CI quality gate: microcopy linter (`scripts/lint_microcopy.py`) run by
  pytest and by `.github/workflows/ci.yml` on every PR into `main`.
- Relabel matching (`src/relabel.py`): pairs DEFRA renames across years with a
  leaf-substitution guard, surfaced as a review-only section (DECISIONS D9).
- Renamed-and-moved explanations: material relabels routed through the grounded
  explainer, with one shared `diff.is_material` rule; surfaced in report, app,
  and run_demo (DECISIONS D10).
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
- Retrieval quality: `changes_pdf.retrieve_passage` grounds explanations but is
  thinly tested (one hit, one miss). A precision/recall harness would guard the
  wedge directly.
- Semantic relabels with low string overlap (Incineration -> Combustion) still
  read as added/removed; would need DEFRA's own relabel notes.
- More CI gates: golden-vector tests for the loader and diff, a dependency-audit
  gate. Not done.
- Package manager pin + lockfile for supply-chain hygiene. Not done (pip +
  requirements.txt only so far).
- Live Gemini runs only on the owner's machine (endpoint blocked in the web
  sandbox).

## Resume here
Two most recent handoffs:

- H5 (2026-07-07): Explained renamed-and-moved factors (the D9 follow-up, now
  DECISIONS D10). Added one shared materiality rule (`diff.is_material`) and used
  it to route every material relabel pair through the grounded explainer;
  retrieval tries both the old and new name and keeps the stronger hit. Surfaced
  in the report (⚠ marker + "Why the renamed factors also moved" section), the
  app, and run_demo. Made the synthetic Fuel-oil relabel material and grounded so
  the path runs offline; added an `is_material` unit test and a pipeline test.
  19 tests green, linter clean, demo runs end-to-end on real DEFRA data.
- H4 (2026-07-07): Built relabel matching (`src/relabel.py`), chosen over another
  CI gate after the owner challenged the priority (reasoning in DECISIONS D9).
  Pairs DEFRA renames under unit+scope gates, name similarity, and a leaf guard
  that blocks fuel-swap false positives (petrol->diesel, cng->lpg) while keeping
  genuine synonym renames (propylene->propene). Wired into pipeline, report, app;
  added a synthetic relabel pair and a 7-case test suite. 17 tests green.

Next likely task: a retrieval-quality harness for `changes_pdf.retrieve_passage`
(guards the wedge directly), or loader/diff golden-vector tests as the next CI
gate.
