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

**Live:** the app is deployed on Streamlit Community Cloud at
<https://efdiff.streamlit.app/> (owner-run, first deploy 2026-07-31). The GitHub
default branch is now `main`, so Streamlit redeploys from `main` on every merge.
The sandbox cannot reach `*.streamlit.app` (proxy denies CONNECT), so live
verification is the owner's.

Gates: `pytest` green (44 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite (detection + family grouping), the
material-relabel explanation path, the retrieval-quality gold set, loader/diff
golden vectors, the real-data ingest suite, and the access-gating suite (free
tier never calls the model, approval rules)). Three CI gates are live: the microcopy linter (no-em-dash house
rule), a retrieval-quality gate that fails the build on any WRONG grounding note,
and a dependency-audit gate (`pip-audit` on requirements); the loader/diff golden
vectors run in the same pytest step. Streamlit app boots clean. Demo footprint on
the sample product: 2.344 to 2.305 kg CO2e, with the UK electricity change
explained from the real DEFRA text. On real data, relabel pairing collapses
~500/500 added/removed to 76 genuinely new and 54 genuinely removed, and the 460
paired renames group into 11 readable families.

## What shipped
- **Goal reframed around genuine usefulness** (`docs/VISION.md`): a six-persona
  panel + critique set the primary audience as the UK solo/boutique DEFRA
  consultant, with getting-hired as an explicit side effect. Honest verdict:
  "partly useful" until the tool eats a real inventory. Plan in
  `docs/PLAN_real_data_ingest.md`.
- **Real-data ingest (VISION move #2), shipped:** `src/ingest.py` reads a real
  messy `.csv`/`.xlsx`, guesses the item/quantity/unit columns from awkward
  headers, and sets aside bad rows instead of guessing (no-guess rule at the
  column level). `app.py` has a confirm-your-columns step and lists set-aside
  rows. Explanations are now ranked by impact on the user's OWN footprint (kg +
  share shown). `scripts/check_ingest.py` + `tests/test_ingest.py` (suite 38).
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
locking down the API key on the live deploy, header-row tolerance in ingest,
VISION move #3 (the cited memo), GOV.UK theming, semantic relabels, and lockfile
pinning.

## Resume here
Most recent handoffs (older ones rotate into `docs/archive/`):

- H16 (2026-07-31): Owner-facing session, no pipeline code changed. Walked the
  owner through the two manual steps the sandbox cannot do: the GitHub default
  branch is now `main` (verified via the API: `default_branch: "main"`), and the
  app is deployed on Streamlit Community Cloud at <https://efdiff.streamlit.app/>
  with a Gemini key created in Google AI Studio. Could not verify the live app:
  the sandbox proxy denies CONNECT to `*.streamlit.app`, so the owner checks the
  provider banner and the 2.344 to 2.305 demo figure. **Open risk flagged, not
  yet fixed:** the deploy has `GEMINI_API_KEY` set with no `[auth]` section, and
  `app.py:66` sets `use_ai = True` when sign-in is not configured, so the public
  URL currently spends the owner's key for every anonymous visitor. Fix is either
  the `[auth]` + `[access]` secrets from `docs/DEPLOY_GUIDE.md` or removing the
  key. README refreshed with the live link, a Vision section, and a correction
  (it still claimed "no login, no cloud" after D17 shipped both).
- H15 (2026-07-09): Merged the hosting/access layer to `main` (PR #15, `31da74b`).
  It collided with the real-data ingest work (PR #14) that landed first, so the
  branch was rebased onto the new `main` and the overlap resolved by keeping BOTH
  features: `app.py` runs ingest (upload + confirm-your-columns) AND the sign-in
  gate in one path; `pipeline.py` keeps impact-ranking AND `force_offline` on both
  explain calls; docs renumbered (hosting decision is D17, its handoff H14). 44
  tests green after the merge, lint clean, app boots. Dev branch realigned to the
  merged `main`. Next open items unchanged: header-row tolerance in ingest, then
  VISION move #3 (a dated, cited, printable memo as the first-class output).

Next likely task: close the open-wallet risk on the live deploy (configure
`[auth]` + `[access]`, or drop the key so the public app runs offline-only).
After that: header-row tolerance in ingest, then VISION move #3 (a dated, cited,
printable memo). Lower-priority: GOV.UK theming from the saved mockup
(`docs/mockups/govuk_report_view.html`), a finer within-family relabel pairing to
make per-variant deltas trustworthy, lockfile pinning, or semantic relabels.
