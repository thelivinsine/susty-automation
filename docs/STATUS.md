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

**Access on the live deploy (D18):** it runs OPEN. `GEMINI_API_KEY` is set with no
`[auth]` section, so anonymous visitors get AI explanations on the owner's key.
The Google Cloud budget cap is set (the D17 backstop) and the owner deliberately
deferred the sign-in gate. Turn it on when the link goes public, when the budget
alert fires, or when anyone relies on the tool. Secrets edit, no code change.

**Interface:** the app now renders through an owned design layer (`src/ui/`)
rather than Streamlit defaults, on the GOV.UK palette the owner chose (D19). The
page reads Result, Confidence, Movers, Explanations, Export, with the trust gate
second rather than near the bottom. Hue carries epistemic status only; direction
of travel is a glyph, a sign and a word, so a falling footprint is never painted
as an alarm. Tables are real tables (caption, column scopes, printable), the Run
control sits in the main canvas so it survives the sidebar collapsing below
768px, and one run exports four artifacts sharing a run id, each carrying its
unresolved items in the front matter (D20).

Gates: `pytest` green (144 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite (detection + family grouping), the
material-relabel explanation path, the retrieval-quality gold set, loader/diff
golden vectors, the real-data ingest suite, and the access-gating suite (free
tier never calls the model, approval rules), the design-system suite (contrast in
both themes, escaping, table semantics, colour independence) and the export-pack
suite (four artifacts, one run id, unresolved items in the front matter)). Three CI gates are live: the microcopy linter (no-em-dash house
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
- Hosting + access layer (DECISIONS D17, D18): open tool for everyone on the free
  offline explainer; paid AI (Claude/Gemini) behind Streamlit's built-in Google
  sign-in plus an approved-list in secrets. One `use_ai` flag threads the tier
  from `app.py` through `pipeline.run_pipeline` to `explain.explain_change`
  (`force_offline`), so the free tier can never spend the key. With no `[auth]`
  secret configured there is no gate at all: the app runs open, and the API key,
  if one is set, drives explanations for everyone (offline for everyone if not).
  Local run / demo / tests are therefore unchanged. Owner guide `docs/DEPLOY_GUIDE.md`,
  secrets template `.streamlit/secrets.toml.example`.
- **Design system and export pack (DECISIONS D20), shipped:** `src/ui/` holds the
  token layer (`tokens.css`, both themes, every pair carrying a machine-checked
  `@contrast` annotation), the component CSS, the HTML builders
  (`components.py`) and the number formatting (`format.py`). `.streamlit/config.toml`
  themes Streamlit's own chrome so the primary action never flashes red.
  `src/export.py` turns one run into four artifacts (xlsx, json, md, print-ready
  html memo) sharing a run id, with a completeness checklist whose open items are
  written into every artifact's front matter. 11 of the audit's 12 defects closed;
  A-07 needs a Streamlit-level fix.
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
Backlog now lives in `REFERENCE.md` (kept out of this snapshot). Short version:
**A-07, the one audit defect still open** (Streamlit's file input has no
programmatic accessible name and neither CSS nor Python can give it one), the
best-candidate name on a below-threshold match, turning on the sign-in gate when
the live link goes public (deferred, D18), header-row tolerance in ingest,
semantic relabels, and lockfile pinning. The design-system build is DONE
(`docs/PLAN_design_system.md`, D20), so "GOV.UK theming" leaves the backlog.

## Resume here
Most recent handoffs (older ones rotate into `docs/archive/`):

- H18 (2026-07-31): Front-end audit received, branding decided, design-system
  work planned. Saved the external UI/UX/accessibility audit verbatim
  (`docs/audit/`), which measured **12 defects** in the live app (5 critical) by
  reading the real DOM: a footprint *decrease* painted red beside a green panel
  saying the same thing positively, the primary CTA at 3.30:1, every caption at
  3.69:1 (including the no-guess sentence), tables rendered to `<canvas>` so they
  cannot be read by assistive tech or printed, and the sidebar auto-collapsing
  below 768px taking every input and the only submit button with it. Independently
  recomputed every contrast ratio the audit reported for its own palette: all
  reproduce exactly. The audit proposed replacing the visual identity; the owner
  reviewed both directions as working mockups on the same real figures and **kept
  GOV.UK** (D19), so the two "Ledger" mockups are committed as the rejected
  alternative rather than deleted. The owner separately approved implementing the
  audit's fix for the three defects that sit underneath the look: a yellow
  needs-review tint (GOV.UK's four tints leave no colour for "held for review"),
  hue-encodes-epistemic-status with direction carried by glyph and word, and a
  `--border-control` split because `#b1b4b6` is 2.08:1 and fails 1.4.11. Two
  findings the audit could not have made, both now in the plan: that same
  `--border` failure lives in our own approved mockup, and a table wider than its
  `overflow-x:auto` container still gives the *page* a phantom horizontal scroll
  (480px of blank space at 375px) unless the container carries `contain:paint`.
  **Docs and mockups only, no pipeline or app code touched**; 44 tests green.
  Next: implement `docs/PLAN_design_system.md`, starting with the token layer.
- H19 (2026-07-31): Implemented `docs/PLAN_design_system.md` end to end, in four
  commits: the token layer, the component builders, the app view-layer rewrite,
  and the export pack. The app had injected no CSS at all and had no
  `.streamlit/config.toml`, so every visual decision was a Streamlit default;
  that is what the audit's 12 defects were measured against. **11 of the 12 are
  now closed** (A-07 is not, see below). The load-bearing change is that hue now
  encodes epistemic status only (cited, not explained, needs review, error) and
  direction of travel is carried by a glyph, an explicit sign and a word, which
  kills A-01 at the root rather than swapping two colours. Two claims from the
  plan were verified by measurement rather than assertion: all 26 declared token
  pairs clear their WCAG floor in both themes (the figures the plan predicted,
  including the 7.77:1 yellow tint and the 19.59:1 border, reproduce exactly),
  and in headless Chromium at a true 375px viewport the memo shows zero phantom
  horizontal scroll, while removing `contain: paint` reproduces the defect at
  248px. Tests went 44 to 144. Nothing in the pipeline, matching, diff or
  explanation layer was touched.
- H18 (2026-07-31): Front-end audit received, branding decided, design-system
  work planned. Saved the external UI/UX/accessibility audit verbatim
  (`docs/audit/`), which measured **12 defects** in the live app (5 critical) by
  reading the real DOM. Independently recomputed every contrast ratio it reported
  for its own palette: all reproduce exactly. The audit proposed replacing the
  visual identity; the owner reviewed both directions as working mockups on the
  same real figures and **kept GOV.UK** (D19), so the two "Ledger" mockups are
  committed as the rejected alternative rather than deleted. Docs and mockups
  only, no pipeline or app code touched.

Next likely task: **A-07, the one defect left open.** Streamlit's file uploader
renders an `<input type="file">` with no programmatic accessible name, and that
cannot be fixed from CSS or from Python. It needs either a Streamlit upgrade that
labels it, or a small custom component. Then: header-row tolerance in ingest, and
surfacing the best-candidate name on a below-threshold match (the coverage control
shows the score and a sentence, but `src/matching.py` discards the losing
candidate's name, so "here is what it nearly matched" needs a one-line change
there and was left rather than smuggled into a view-layer pass). Deferred by owner
decision, not forgotten: the sign-in gate on the live deploy (D18). Lower
priority: a finer within-family relabel pairing, lockfile pinning, semantic
relabels.
