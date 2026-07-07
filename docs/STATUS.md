# Status

Living snapshot. Keep it short. Older handoffs get archived at the bottom.

## Current state
EF Version Explainer MVP is complete and running on the owner's real DEFRA
full-set workbooks (2025 and 2026). Loads 2111/2133 factors across 27 sheets,
diffs them, matches a product BOM (no-guess rule), recomputes the footprint under
both years with coverage, and explains flagged changes grounded in the DEFRA
"What's new" sheet. Explanation backend is Gemini (or Claude, or offline),
selected by API key loaded from a git-ignored `.env`.

Gates: `pytest` green (7 tests, including the grounding trap and a real-workbook
test). Streamlit app boots clean. Demo footprint on the sample product: 2.344 to
2.305 kg CO2e, with the UK electricity change explained from the real DEFRA text.

## What shipped
- Pipeline: loader, diff, matching, recompute, changes retrieval, explain,
  report, app, run_demo (`src/`, `app.py`, `run_demo.py`).
- Real DEFRA full-set support and "What's new" grounding.
- Provider-agnostic explanation backend (Gemini / Claude / offline) with `.env`
  auto-load.
- Synthetic real-format demo data generator.
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
- Relabel matching: pair DEFRA renames across years so they stop showing as
  added+removed (see DECISIONS D4).
- Quality gates in CI: no CI yet. Candidates the owner likes: an em-dash /
  microcopy linter for user-facing strings, golden-vector tests for the loader
  and diff, a dependency-audit gate. Not built yet.
- Package manager pin + lockfile for supply-chain hygiene. Not done (pip +
  requirements.txt only so far).
- Live Gemini runs only on the owner's machine (endpoint blocked in the web
  sandbox).

## Resume here
Two most recent handoffs:

- H2 (2026-07-07): Adopted the owner's standing working preferences. Added the
  docs set, scrubbed em dashes from user-facing output, established `main` as
  production, and switched to the auto-ship + post-merge-housekeeping workflow.
- H1 (2026-07-07): Added the Gemini backend and `.env` auto-load for API keys.

Next likely task: wire the first CI quality gate (em-dash/microcopy linter or
loader golden-vectors), or build relabel matching. Ask the owner which, or pick
the linter as the smallest high-value gate.
