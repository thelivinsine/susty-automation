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
path, the retrieval-quality gold set, and loader/diff golden vectors). Three CI
gates are live: the microcopy linter (no-em-dash house rule), a retrieval-quality
gate that fails the build on any WRONG grounding note, and a dependency-audit gate
(`pip-audit` on requirements); the loader/diff golden vectors run in the same
pytest step. Streamlit app boots clean. Demo footprint on the sample product:
2.344 to 2.305 kg CO2e, with the UK electricity change explained from the real
DEFRA text. On real data, relabel pairing collapses ~500/500 added/removed to 76
genuinely new and 54 genuinely removed.

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
- Dependency-audit gate (`scripts/audit_deps.py`): CI-only `pip-audit` over the
  requirements' transitive closure, fails on any known CVE (DECISIONS D13).
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
Backlog now lives in `REFERENCE.md` (kept out of this snapshot). Short version:
dedupe the ~420 renamed-and-moved entries, theme the Streamlit app to the
GOV.UK-familiar mockup, semantic relabels, lockfile pinning, and Gemini being
reachable only on the owner's machine.

## Resume here
Two most recent handoffs (older ones rotate into `docs/archive/`):

- H10 (2026-07-08): Adopted the "model selection & documentation practices" doc.
  Added `docs/REFERENCE.md` (per-session model-selection guidance + the backlog
  moved out of STATUS) and the `docs/archive/` ISO-week rotation convention with an
  index, rotating H8 into `STATUS_2026-W28.md`. Recorded the four-doc structure and
  the rotation rules in WORKING_PREFERENCES and CLAUDE.md. Docs-only; no code
  touched, 26 tests still green.
- H9 (2026-07-08): Owner asked how to view the product, then to style it in a
  DEFRA-familiar way (P15, P16). Rendered the live pipeline output as an HTML view
  and rebuilt it in the GOV.UK Design System idiom (evoked, not cloned; with an
  independence disclaimer), saved as `docs/mockups/govuk_report_view.html`. No
  pipeline code changed. Surfaced two follow-ups now in the backlog: dedupe the
  ~420 renamed-and-moved entries on real data, and (optionally) theme the Streamlit
  app to the same look. 26 tests still green.

Next likely task: dedupe the renamed-and-moved output (D10 follow-up, ~420
near-duplicates on real data) and/or theme the Streamlit app to the GOV.UK-familiar
look using the saved mockup. Lower-priority: lockfile pinning, or semantic relabels
(needs DEFRA's own relabel notes).
