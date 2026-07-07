# Status

Living snapshot. Keep it short. Older handoffs get archived at the bottom.

## Current state
EF Version Explainer MVP is complete and running on the owner's real DEFRA
full-set workbooks (2025 and 2026). Loads 2111/2133 factors across 27 sheets,
diffs them, matches a product BOM (no-guess rule), recomputes the footprint under
both years with coverage, and explains flagged changes grounded in the DEFRA
"What's new" sheet. Explanation backend is Gemini (or Claude, or offline),
selected by API key loaded from a git-ignored `.env`.

Gates: `pytest` green (8 tests, including the grounding trap, a real-workbook
test, and the microcopy gate). First CI gate is live: a microcopy linter that
enforces the no-em-dash house rule, wired into pytest and a GitHub Actions
workflow. Streamlit app boots clean. Demo footprint on the sample product: 2.344
to 2.305 kg CO2e, with the UK electricity change explained from the real DEFRA
text.

## What shipped
- Pipeline: loader, diff, matching, recompute, changes retrieval, explain,
  report, app, run_demo (`src/`, `app.py`, `run_demo.py`).
- Real DEFRA full-set support and "What's new" grounding.
- Provider-agnostic explanation backend (Gemini / Claude / offline) with `.env`
  auto-load.
- Synthetic real-format demo data generator.
- First CI quality gate: microcopy linter (`scripts/lint_microcopy.py`) run by
  pytest and by `.github/workflows/ci.yml` on every PR into `main`.
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
- Relabel matching: pair DEFRA renames across years so they stop showing as
  added+removed (see DECISIONS D4).
- More CI gates: golden-vector tests for the loader and diff, a dependency-audit
  gate. Microcopy gate is done; these are not.
- Package manager pin + lockfile for supply-chain hygiene. Not done (pip +
  requirements.txt only so far).
- Live Gemini runs only on the owner's machine (endpoint blocked in the web
  sandbox).

## Resume here
Two most recent handoffs:

- H3 (2026-07-07): Shipped the first CI quality gate. Built the microcopy linter
  (`scripts/lint_microcopy.py`), wired it into pytest and a GitHub Actions
  workflow, fixed two user-facing em-dash violations it caught in
  `src/recompute.py`, and scrubbed README.md and CLAUDE.md.
- H2 (2026-07-07): Adopted the owner's standing working preferences. Added the
  docs set, scrubbed em dashes from user-facing output, established `main` as
  production, and switched to the auto-ship + post-merge-housekeeping workflow.

Next likely task: the next CI gate (loader/diff golden-vectors or a
dependency-audit gate), or build relabel matching (DECISIONS D4).
