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

**Front door (D23):** the app now OPENS on the comparison. Section 1 is an
interactive, filterable table of the whole factor register (2,647 joined rows on
the real 2025/2026 workbooks), with search, scope, status, a minimum-movement
slider and a past-DEFRA-thresholds toggle, plus a download of whatever view you
have narrowed to. It runs on a cold visit with no upload, no sign-in and no API
key, because `pipeline.compare_versions` is the BOM-free half of the pipeline and
`run_pipeline` now calls it rather than repeating it. The product report is
unchanged and sits behind the Run button, which a person now has to press: the
app no longer runs the whole pipeline on a sample product unasked.

**Interface:** the app renders through an owned design layer (`src/ui/`) rather
than Streamlit defaults, on the GOV.UK palette the owner chose (D19). As of D22
it is an app shell rather than a document: a masthead naming the two releases
being compared and the run status, a sticky numbered section nav, setup as three
steps in the main canvas (so nothing a first run needs lives in the sidebar that
collapses below 768px), the verdict as two figures and a delta over a strip of
qualifying facts, coverage as a meter against the 95% bar, magnitude bars beside
every delta, and the DEFRA quote shown as a source block in the app as well as
the memo. The palette is unchanged: every hex still comes from `tokens.css`.
The page reads Compare releases, Result, Confidence, Movers, Explanations,
Export, with the trust gate before the movers rather than near the bottom, and
every h2 on the page is a numbered section the nav can reach (a transition
heading is a subhead, and the IA test asserts it). Hue carries epistemic status only;
direction of travel is a glyph, a sign and a word, so a falling footprint is
never painted as an alarm. Tables are real tables (caption, column scopes,
printable), and one run exports four artifacts sharing a run id, each carrying
its unresolved items in the front matter (D20).

Gates: `pytest` green (177 tests, including the grounding trap, a real-workbook
test, the microcopy gate, the relabel suite (detection + family grouping), the
material-relabel explanation path, the retrieval-quality gold set, loader/diff
golden vectors, the real-data ingest suite, and the access-gating suite (free
tier never calls the model, approval rules), the design-system suite (contrast in
both themes, escaping, table semantics, colour independence) and the export-pack
suite (four artifacts, one run id, unresolved items in the front matter, and the
citation suite: evidence carried, evidence rendered, and no quote beside an
unexplained change)). Three CI gates are live: the microcopy linter (no-em-dash house
rule), a retrieval-quality gate that fails the build on any WRONG grounding note,
and a dependency-audit gate (`pip-audit` on requirements); the loader/diff golden
vectors run in the same pytest step. Streamlit app boots clean. Demo footprint on
the sample product: 2.344 to 2.305 kg CO2e, with the UK electricity change
explained from the real DEFRA text. On real data, relabel pairing collapses
~500/500 added/removed to 76 genuinely new and 54 genuinely removed, and the 460
paired renames group into 11 readable families.

## What shipped
- **The comparison as the front door (D23):** `pipeline.compare_versions` (the
  BOM-free half of the pipeline, reused by `run_pipeline` so the two can never
  disagree), `diff.filter_changes` (the pure, tested rule that decides what a
  reader is shown), a `renamed` column laid over the diff so a paired relabel is
  never also counted as a new factor, section 1 in `app.py` with five filters and
  a download of the narrowed view, and the removal of the unasked pipeline run on
  a cold visit. Plus the defect this uncovered: `inject_styles` emitted the design
  layer only on a session's FIRST run, so Streamlit dropped it on every rerun and
  the whole design system fell off the moment anyone touched a widget. Guard
  deleted, `test_the_stylesheet_survives_a_rerun` added.
- **Product-UI rework (D22), palette untouched:** app shell (masthead + sticky
  numbered section nav), setup as a three-step flow in the canvas, the verdict as
  two figures plus a delta chip and a fact strip, a coverage meter against the
  95% bar, magnitude bars on every delta column, explanation cards that lead with
  status and footprint impact, the DEFRA quote rendered in the app, a system font
  stack, and a surface system (cards, hairlines, one radius, two shadow levels)
  built only from alpha composites of the existing ink. Preview:
  `docs/mockups/v2_product_ui.html`. Verified in headless Chromium at 375, 768
  and 1440px: zero horizontal page scroll.
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
- **Citations in the memo (DECISIONS D21), shipped:** the "Cited" tag now has
  evidence under it. `loader.py` records `source_file`/`source_sheet`/`source_row`
  (240 of 240 sampled real rows verified against the workbook cells), `diff.py`
  carries them through the join, `changes_pdf` tags each chunk with its document
  and adds `retrieve_citation`, and `export.py` renders the verbatim quote, its
  section heading, the source document and the factor's row. `retrieve_passage`
  and `retrieve_citation` share one `_best_chunk`, so the quote shown is always
  the passage the explanation was built from. `scripts/check_citations.py` shows
  it working on real data.
- Docs: WORKING_PREFERENCES, DECISIONS, PROMPT_LOG, this file.

## Known gaps / next candidates
Backlog now lives in `REFERENCE.md` (kept out of this snapshot). Short version:
**A-07, the one audit defect still open** (Streamlit's file input has no
programmatic accessible name and neither CSS nor Python can give it one), the
best-candidate name on a below-threshold match, turning on the sign-in gate when
the live link goes public (deferred, D18), header-row tolerance in ingest,
semantic relabels, and lockfile pinning. The design-system build is DONE
(`docs/PLAN_design_system.md`, D20) and the product-UI rework on top of it is DONE
(D22), so neither is a backlog item. The nav's active-section highlight, left open
by D22, shipped after it. What the interface still leaves: the app stays
light-only, because Streamlit's own chrome is pinned light in `config.toml`.

## Resume here
Most recent handoffs (older ones rotate into `docs/archive/`):

- H23 (2026-08-17): MADE THE COMPARISON THE FRONT DOOR (D23), on the owner's
  brief to check whether the interface really leads with an interactive EF
  version comparison. It did not: the app opened on a setup form, ran the whole
  pipeline on a sample product before anyone asked, had zero filter controls
  anywhere, and rendered only the handful of diff rows that touched a bill of
  materials. Split `compare_versions` out of `run_pipeline` (which now calls it,
  so there is one definition of the delta), added `diff.filter_changes` with its
  own suite (19 tests, runnable standalone), and built section 1: search, scope,
  status, minimum-movement slider, materiality toggle, live count, and a CSV of
  whatever view you have narrowed to. Removed the cold-load pipeline run. Real
  numbers on the real workbooks: 2,647 joined factors, 67 past threshold, 76
  genuinely new, 54 retired, 460 renamed. Checked in a real browser at 375, 768
  and 1440px: zero horizontal scroll at every width, and every filter carries a
  programmatic accessible name. **Found and fixed a serious pre-existing defect
  while checking it:** `inject_styles`'s session_state guard meant the design
  layer was emitted only on a session's first run, so Streamlit removed it on the
  next rerun and the page reverted to Streamlit defaults (captions measured back
  at the default ink instead of #505a5f) the instant a visitor touched anything.
  The guard is gone and a test now asserts exactly one style block AFTER an
  interaction. Also fixed `run_demo.py` writing its report without an explicit
  encoding, which crashed the demo's last stage on Windows cp1252 on the owner's
  own machine. 177 tests green, both CI gates clean. Not done, deliberately:
  filter state in the URL (`st.query_params`), which is the next candidate.

- H22 (2026-08-04): REWORKED the interface (D22) on the owner's brief: make it
  look and behave like a senior product team shipped it, keep the palette. Built
  the direction as a preview first (`docs/mockups/v2_product_ui.html`, three
  screens plus a swatch sheet so "palette intact" is checkable by looking), then
  implemented it. `tokens.css` gained a surface system and a type scale and no new
  hue; `components.css` was rewritten around cards, a shell and real states;
  `components.py` gained masthead, subnav, meter, fact_bar, step, file_chip,
  explanation_head, source_quote and checklist, and `verdict_card` learned the
  two-figure layout; `app.py` moved setup out of the sidebar into three numbered
  steps. Every D20 rule still holds and is still enforced. 151 tests green (the
  one changed assertion was a test pinning the literal "1 row(s)", now written as
  "1 row" by `ui.format.plural`). Checked in a real browser at 375, 768 and
  1440px: zero horizontal scroll, report renders end to end on the real 2025 and
  2026 workbooks. Not done, and deliberately: A-07 is still open (Streamlit's
  file input still has no programmatic accessible name), and the app remains
  light-only because Streamlit's own chrome is pinned light in config.toml.
  Shipped as PR #24, squash-merged `e21222b`.

- H21 (2026-07-31): BUILT the citations (D21), so the memo now shows its work.
  Validated the risky step first: the loader records `source_file`,
  `source_sheet`, `source_row`, and 240 of 240 randomly sampled rows across both
  real workbooks were checked against the actual cells with openpyxl, so the row
  numbers survive the super-header expansion and the forward-fill. `diff.py`
  carries provenance through the join (new workbook where the factor still
  exists, old one where it was removed); `changes_pdf` tags each chunk with its
  document and gains `retrieve_citation`, which shares `_best_chunk` with
  `retrieve_passage` so the quote a reader checks is always the passage the
  explanation was built from; `export.py` renders the quote, its section heading,
  the source document, and the factor's workbook/sheet/row under the "Cited" tag.
  D11 untouched: the retrieval gate still reports 0 wrong hits. The D12 golden
  vector failed as predicted and its fixture now PINS the provenance, with every
  expected row number verified against the fixture's cells rather than copied from
  the loader. 149 tests (was 144), both gates clean, `scripts/check_citations.py`
  prints the evidence on real data, and the memo was rendered in headless Chromium
  to confirm the citation block appears and survives print media. Known wrinkle
  logged, not hidden: in offline mode the reason already embeds the note, so it
  reads twice. Shipped as PR #22, squash-merged `12e27f1`.

Next likely task: **filter state in the URL** (`st.query_params`), so a narrowed
comparison is a link a consultant can send ("every scope 3 factor past
threshold"). Then: **A-07, the one defect left open.** Streamlit's file uploader
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
