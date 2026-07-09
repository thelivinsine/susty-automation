# Status

Living snapshot. Keep it short. Older handoffs get archived at the bottom.

## Current state
EF Version Explainer MVP is complete and running on the owner's real DEFRA
full-set workbooks (2025 and 2026). Loads 2111/2133 factors across 27 sheets,
diffs them, pairs DEFRA relabels so renames stop reading as added+removed noise,
matches a product BOM (no-guess rule), recomputes the footprint under both years
with coverage, and explains flagged changes grounded in the DEFRA "What's new"
sheet. Renamed-and-moved factors are explained too: a relabel whose value also
crossed the materiality threshold is routed through the same grounded explainer.
Those relabels are now GROUPED into rename families (same head rename and scope),
so the real-data HGV rename that spanned ~420 near-identical variants reads as ~10
explained families instead of 420 blocks (and ~10 API calls, not 420), with value
movement shown as an honest range and a "mixed direction" flag where sub-factors
move both ways. Explanation backend is Gemini (or Claude, or offline), selected by
API key loaded from a git-ignored `.env`.

Gates: `pytest` green (38 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite (detection + family grouping), the
material-relabel explanation path, the retrieval-quality gold set, loader/diff
golden vectors, and the access-gating suite (free tier never calls the model,
approval rules)). Three CI gates are live: the microcopy linter (no-em-dash house
rule), a retrieval-quality gate that fails the build on any WRONG grounding note,
and a dependency-audit gate (`pip-audit` on requirements); the loader/diff golden
vectors run in the same pytest step. Streamlit app boots clean. Demo footprint on
the sample product: 2.344 to 2.305 kg CO2e, with the UK electricity change
explained from the real DEFRA text. On real data, relabel pairing collapses
~500/500 added/removed to 76 genuinely new and 54 genuinely removed, and the 460
paired renames group into 11 readable families.

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
  leaf-substitution guard, surfaced as a review-only section (DECISIONS D9), and
  grouped into rename families for readable output (`group_relabels`, DECISIONS
  D14).
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
- Hosting + access layer (DECISIONS D15): open tool for everyone on the free
  offline explainer; paid AI (Claude/Gemini) behind Streamlit's built-in Google
  sign-in plus an approved-list in secrets. One `use_ai` flag threads the tier
  from `app.py` through `pipeline.run_pipeline` to `explain.explain_change`
  (`force_offline`), so the free tier can never spend the key. Auth helpers in
  `src/auth.py` degrade to "open, offline for all" when no `[auth]` secret is set,
  so local run / demo / tests are unchanged. Owner guide `docs/DEPLOY_GUIDE.md`,
  secrets template `.streamlit/secrets.toml.example`.
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
Backlog now lives in `REFERENCE.md` (kept out of this snapshot). Short version:
dedupe the ~420 renamed-and-moved entries, theme the Streamlit app to the
GOV.UK-familiar mockup, semantic relabels, lockfile pinning, and Gemini being
reachable only on the owner's machine.

## Resume here
Two most recent handoffs (older ones rotate into `docs/archive/`):

- H13 (2026-07-09): Owner asked how to make the tool accessible to non-technical
  users, and whether it lives on GitHub Pages (it can't: Streamlit needs a server).
  Built the hosting/access layer (D15): open to everyone on the free offline
  explainer, paid AI behind Streamlit's built-in Google sign-in + an approved list
  in secrets, spending cap as backstop. New `src/auth.py`; `use_ai`/`force_offline`
  flag threaded app -> pipeline -> explain; `app.py` sign-in UI and free-vs-AI
  banners; `.streamlit/secrets.toml.example`; owner-facing `docs/DEPLOY_GUIDE.md`;
  requirements bumped (streamlit>=1.42, Authlib). +6 tests (38 green), lint clean.
  No sign-in configured => behaves exactly as before. Deploy to Streamlit Cloud is
  the owner's click-through (guide provided); no repo settings changed here.
- H12 (2026-07-08): Grouped the renamed-and-moved output into rename families
  (D10 follow-up, D14). On real data the HGV rename spanned 420 material variants
  (DEFRA also reordered the sub-tables, so the greedy matcher scattered +-100%
  deltas); those now collapse to ~10 grounded family explanations with an honest
  value-movement range and a "mixed direction" flag, not 420 fabricated single-
  direction blocks (and ~10 API calls, not 420). New `relabel.group_relabels`;
  report/app/run_demo render families; +6 tests (32 green). Footprint math
  untouched (relabels stay review-only, D9).
- H11 (2026-07-08): Owner asked to commit the two source docs shared at project
  start and to make `main` the default branch (P17). Added the build playbook and
  the MVP spec PDF under `docs/reference/`, shipped via PR #10. Default-branch
  switch is a manual owner step (no repo-settings tool / no direct GitHub API here):
  GitHub repo Settings, Branches, set default to `main`. Docs/reference only, no
  code touched.

Next likely task: theme the Streamlit app to the GOV.UK-familiar look using the
saved mockup (`docs/mockups/govuk_report_view.html`). Lower-priority: a finer
within-family relabel pairing to make per-variant deltas trustworthy (or DEFRA's
own row map), lockfile pinning, or semantic relabels (needs DEFRA's relabel notes).
