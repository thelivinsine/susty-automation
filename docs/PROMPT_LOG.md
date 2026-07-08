# Prompt / session log (append-only)

One entry per owner prompt. Verbatim prompt, timestamp (date-level), branch,
response summary, artifacts. No secrets, no internal model identifier.
Branch for all entries below: `claude/project-setup-i1gyff`.

---

### 2026-07-06 · P1
**Prompt (verbatim):** "start working on this project" (with two attachments: the
Build Playbook markdown and the MVP Spec PDF).

**Response summary:** Built the EF Version Explainer MVP end to end. Project
skeleton, CLAUDE.md, requirements. Pipeline modules: loader, diff, matching (no
guess), recompute (coverage), changes_pdf retrieval, explain (grounded, with
offline fallback), report, pipeline, app, run_demo. Shipped clearly-labelled
synthetic DEFRA-format data so it runs offline. Noted the build environment
cannot reach gov.uk. Tests mirror the acceptance criteria including the grounding
trap test.

**Artifacts:** CLAUDE.md, README.md, requirements.txt, .gitignore, src/*.py,
app.py, run_demo.py, scripts/make_synthetic_data.py, tests/*, data/synthetic/*.
Commit `826726b`.

---

### 2026-07-07 · P2
**Prompt (verbatim):** "i uploaded defra files"

**Response summary:** The files were not in the environment. Searched everywhere,
found nothing, explained the likely upload-size cause and the options.

**Artifacts:** none (investigation only).

---

### 2026-07-07 · P3
**Prompt (verbatim, via question):** "i think both are full sets but of different
years"

**Response summary:** Confirmed full-set expectation. Files still absent at that
point.

**Artifacts:** none.

---

### 2026-07-07 · P4
**Prompt (verbatim):** "they're already committed in github"

**Response summary:** Found the two real full-set workbooks on the branch (2025
1.8MB, 2026 2.1MB, user commit `becaf9e`). Inspected the real format, then
reworked the loader to it (scope metadata, forward-fill fix, super-header block
expansion, Year column ignored). Loaded 2111/2133 factors across 27 sheets.
Stopped auto-flagging added/removed as movers (most are DEFRA relabels). Wired
the workbook "What's new" sheet as the grounding source. Built a realistic
real-data BOM. Demo footprint 2.344 to 2.305 kg CO2e, electricity change
explained from the real DEFRA text. Added a real-workbook test.

**Artifacts:** src/loader.py, src/diff.py, src/changes_pdf.py, src/paths.py,
src/pipeline.py, src/report.py, app.py, run_demo.py, scripts/make_synthetic_data.py,
data/sample_bom_real.csv, tests/test_pipeline.py, README.md, CLAUDE.md.
Commit `81ed728`.

---

### 2026-07-07 · P5
**Prompt (verbatim):** "I want to use my gemini api key. not claude. where do i
provide the key?"

**Response summary:** Added a Gemini backend (google-genai). Backend selected by
key: Gemini, else Claude, else offline. Grounding enforced in code for every
backend. Confirmed the Gemini endpoint is blocked in the build sandbox and that
it degrades gracefully. Documented where to set the key.

**Artifacts:** src/explain.py, requirements.txt, app.py, run_demo.py, README.md,
CLAUDE.md. Commit `477d9bd`.

---

### 2026-07-07 · P6
**Prompt (verbatim):** "can i just add it in github secrets?"

**Response summary:** Explained GitHub secrets only reach GitHub Actions, not a
local or Streamlit run. Set up the simplest path: auto-load a git-ignored `.env`
via python-dotenv, with `.env.example`. Verified `.env` is ignored and the key
plus model override load automatically.

**Artifacts:** app.py, run_demo.py, requirements.txt, .env.example, README.md.
Commit `ef09b29`.

---

### 2026-07-07 · P7
**Prompt (verbatim):** A standing "Working preferences & practices" message
(non-technical owner, no em dashes, token discipline, auto-ship to main,
post-merge housekeeping, required docs: status doc + decisions log + prompt log,
locked-decisions convention, security posture). Full text is the source for
`WORKING_PREFERENCES.md`.

**Response summary:** Persisted preferences to `docs/WORKING_PREFERENCES.md` and
referenced them from CLAUDE.md. Created the status doc, decisions log, and this
prompt log. Scrubbed em dashes from user-facing output strings (report, app,
run_demo). Established `main` as production from the green setup branch and
adopted the auto-ship + housekeeping workflow going forward.

**Artifacts:** docs/WORKING_PREFERENCES.md, docs/STATUS.md, docs/DECISIONS.md,
docs/PROMPT_LOG.md, CLAUDE.md, src/report.py, app.py, run_demo.py. Commit and
main-establishment recorded in STATUS.md.

---

### 2026-07-07 · P8
**Prompt (verbatim):** "what's next?"

**Response summary:** Picked the first CI quality gate: a microcopy linter that
enforces the no-em-dash house rule as code. Built `scripts/lint_microcopy.py`
(AST-based: flags em dashes in user-facing Python string literals, excluding
docstrings and comments, plus anywhere in Markdown; allowlists the synthetic
data generator, which mirrors DEFRA's third-party formatting). Wired it into
pytest (`tests/test_microcopy.py`) and a new GitHub Actions workflow
(`.github/workflows/ci.yml`) that runs the gate then the tests on every PR into
`main`. The linter caught two real user-facing violations the earlier scrub
missed (`src/recompute.py` note strings), which are now fixed, plus scrubbed em
dashes from README.md and CLAUDE.md. Verified: linter clean, fails correctly on
a planted em dash, and `pytest` green at 8 passed.

**Artifacts:** scripts/lint_microcopy.py, tests/test_microcopy.py,
.github/workflows/ci.yml, src/recompute.py, README.md, CLAUDE.md, docs/STATUS.md,
docs/PROMPT_LOG.md.

---

### 2026-07-07 · P9
**Prompt (verbatim):** "before you implement this - are you sure these lint gates
or golden vector tests are the most effective solutions for the problems or are
you just doing it becuase it was mentioned as best practices from previus
projects?" then "alright then, go ahead with the revised recommendation and
document this decision".

**Response summary:** Owner challenged the priority. Agreed the microcopy linter
was cosmetic (cheap, already shipped) and that loader golden-vectors would be
incremental, since the real-workbook test already covers the loader. Reframed
around the wedge (the explanation): its weak spots are retrieval quality and the
added/removed clutter. Recommended and then built RELABEL MATCHING as the highest
visible product value. `src/relabel.py::detect_relabels` pairs removed<->added
under hard gates (same unit, same scope) + name similarity (token_set_ratio >=90)
+ a leaf-substitution guard: the identifying leaf (last " - " segment, the fuel/
variant) must not be swapped, so petrol->diesel and cng->lpg false positives are
blocked while a genuine synonym rename (propylene->propene) passes. Greedy
one-to-one; below the bar stays added/removed (no-guess). Wired into pipeline,
report (a review-only "Relabels" section), app, and run_demo; added a synthetic
relabel pair. On the owner's real data: 460 of ~525 added/removed paired, leaving
76 genuinely new and 54 removed. Relabels are NOT used in the footprint math, so
a mispair cannot corrupt the carbon number. Documented the decision and its
boundaries in DECISIONS D9 (and updated D4). Verified: 17 tests green, linter
clean, demo runs end-to-end on real data.

**Artifacts:** src/relabel.py, tests/test_relabel.py, src/pipeline.py,
src/report.py, app.py, run_demo.py, scripts/make_synthetic_data.py,
data/synthetic/*, docs/DECISIONS.md, docs/STATUS.md, docs/PROMPT_LOG.md.

Note: P8 to P10 were done on branch `claude/whats-next-syd3jf` (not the
`claude/project-setup-i1gyff` named at the top of this file), each auto-shipped
to `main` via a squash-merged PR (#1 microcopy gate, #2 relabel matching).

---

### 2026-07-07 · P10
**Prompt (verbatim):** "document the session"

**Response summary:** Confirmed the session was already documented incrementally:
STATUS.md (handoffs H3, H4), this log (P8, P9), and DECISIONS D9 all shipped with
PRs #1 and #2 and are on `main`. Added this P10 entry to keep the append-only log
one-per-prompt, and recorded that P8 to P10 ran on `claude/whats-next-syd3jf`.
Session summary: (1) shipped the microcopy CI gate; (2) after the owner
challenged the priority, pivoted to and built relabel matching with a leaf guard
that blocks fuel-swap false positives; (3) documented the pivot and its
boundaries. Gates at session end: 17 tests green, microcopy linter clean, demo
runs end-to-end on real DEFRA data.

**Artifacts:** docs/PROMPT_LOG.md.

---

### 2026-07-07 · P11
**Prompt (verbatim):** "What's the next task?" then "yes"

**Response summary:** Realigned the stale dev branch onto `main` (it was 3 commits
behind: the microcopy gate, relabel matching, and the P10 log entry were already
merged). Recommended the D9 follow-up (explain renamed-and-moved factors) over a
retrieval-quality harness because a material change shown without a reason is the
more urgent hole in the wedge, then built it. Added `diff.is_material(pct, scope)`
as the single shared materiality rule and refactored the `flagged` column onto it.
In the pipeline, routed every material relabel pair through the same grounded
explainer as the flagged factors, retrieving on both the old and new name and
keeping the stronger hit (empty passage still yields the honest "no reason"). New
`relabel_explanations` output surfaced in the report (⚠ marker + a "Why the
renamed factors also moved" section), the app, and run_demo. Made the synthetic
Fuel-oil relabel material (+6.9% Scope 1) and grounded it with a changes note so
the path runs offline and is tested. Added an `is_material` unit test and a
pipeline test. Verified: 19 tests green, microcopy linter clean, demo runs
end-to-end on real DEFRA data (real material relabels explained). Documented in
DECISIONS D10 and STATUS handoff H5. Branch `claude/next-task-ydh8wl`.

**Artifacts:** src/diff.py, src/pipeline.py, src/report.py, app.py, run_demo.py,
scripts/make_synthetic_data.py, data/synthetic/*, tests/test_relabel.py,
docs/DECISIONS.md, docs/STATUS.md, docs/PROMPT_LOG.md.

---

### 2026-07-07 · P12
**Prompt (verbatim):** "go ahead"

**Response summary:** Built the retrieval-quality harness for the grounding step
(the next candidate from STATUS). Added `scripts/eval_retrieval.py`: it scores
`changes_pdf.retrieve_passage` against a labelled gold set for precision, recall,
and refusal accuracy, and fails on any WRONG grounding note (the failure a plain
hit-count cannot see, and the one D2 forbids). The harness immediately surfaced a
real defect: retrieval scored `max(keyword_overlap, title_fuzz)`, so a fuzzy title
match on shared boilerplate could fire a hit on the wrong note ("Petrol (average
biofuel blend)" -> the diesel note at 0.87; on real data, "Plug-in Hybrid" car/van
factors -> a "Calculating emissions" heading at ~0.55). Fixed by making keyword
overlap the gate so the title only refines a passage whose overlap already clears
the bar. Verified empirically on the real "What's new" data: 7 title-only false
positives became honest "no reason found" with zero genuine hits lost, and the
real electricity retrieval stays covered. Added a 3-test gate
(`tests/test_retrieval_quality.py`) and a CI step. 22 tests green, both linters
clean. Documented in DECISIONS D11 and STATUS handoff H6. Branch
`claude/next-task-ydh8wl`.

**Artifacts:** src/changes_pdf.py, scripts/eval_retrieval.py,
tests/test_retrieval_quality.py, .github/workflows/ci.yml, docs/DECISIONS.md,
docs/STATUS.md, docs/PROMPT_LOG.md.

---

### 2026-07-07 · P13
**Prompt (verbatim):** "go ahead"

**Response summary:** Added loader/diff golden-vector tests, the next CI gate the
owner liked. Chose this over a dependency-audit gate (higher value: the loader is
the fragile foundation and a silent parsing regression corrupts every carbon
number) and over semantic relabels (needs unavailable DEFRA notes, risks the
no-guess rule). Built `tests/test_golden_loader.py`: a small two-sheet fixture
written in code (an INDEPENDENT oracle, not reusing make_synthetic_data.py) that
exercises every tricky loader path (scope-from-metadata, "Scope 3 (indirect)"
normalization, forward-filled descriptors, an ignored Year column, unit
normalization, (activity, unit) dedup, and super-header block expansion). It pins
the EXACT normalized loader output and the EXACT diff results (pct_change, status,
flagged across a Scope-1 mover, a Scope-3 mover, a sub-threshold change, an equal
factor, and an added/removed pair). Runs in the existing pytest CI step, so it
gates every PR without the big data files. 26 tests green, both existing gates
clean. Documented in DECISIONS D12 and STATUS handoff H7. Branch
`claude/next-task-ydh8wl`.

**Artifacts:** tests/test_golden_loader.py, docs/DECISIONS.md, docs/STATUS.md,
docs/PROMPT_LOG.md.

---

### 2026-07-07 · P14
**Prompt (verbatim):** "go ahead"

**Response summary:** Added the dependency-audit gate, chosen over semantic
relabels (which need unavailable DEFRA notes and risk the no-guess rule). Built
`scripts/audit_deps.py`, a wrapper that runs `pip-audit -r requirements.txt` over
the declared deps and their transitive closure, and wired it into CI as its own
step (installs pip-audit, then runs the wrapper). Kept it CI-only rather than a
pytest test because a dependency audit is online and time-varying (a clean tree
can flag later with no code change), unlike the deterministic offline gates; and
kept pip-audit OUT of requirements.txt so the app's runtime deps stay lean.
Verified it runs clean in the sandbox (no known vulnerabilities). 26 tests green,
all three CI gates clean. Documented in DECISIONS D13 and STATUS handoff H8.
Branch `claude/next-task-ydh8wl`.

**Artifacts:** scripts/audit_deps.py, .github/workflows/ci.yml, docs/DECISIONS.md,
docs/STATUS.md, docs/PROMPT_LOG.md.

---

### 2026-07-08 · P15
**Prompt (verbatim):** "how can I view the product?"

**Response summary:** Gave the owner three ways to view the tool and, because the
session runs in a cloud sandbox where Streamlit is not reachable, rendered the
LIVE pipeline output as a browser-viewable HTML Artifact from the real DEFRA 2025
to 2026 data (footprint 2.344 to 2.305 kg CO2e, 85.7% coverage, the UK electricity
change explained, HGV rename-and-move examples, one line held for review). Also
documented the two local commands: `streamlit run app.py` (the interactive
dashboard) and `python run_demo.py` (writes reports/demo_report.md). Flagged a real
UX issue found while rendering: on real data the renamed-and-moved section (D10)
emits ~420 near-duplicate entries (the same HGV rename repeated across weight
classes and units), which bloats the report; proposed grouping them.

**Artifacts:** none committed (external Artifact rendered from a live run; no repo
change).

---

### 2026-07-08 · P16
**Prompt (verbatim):** "looks good. why not use the design and color scheme used by
DEFFRA but not a literal copy so that the users are familiar with the visuals"

**Response summary:** Rebuilt the report-view Artifact in the GOV.UK Design System
idiom (DEFRA sits inside GOV.UK), evoking it without cloning: black masthead with
an environment-green keyline, a phase banner with a "Prototype" tag, the green
confirmation panel for the headline result, GOV.UK tag pills, big-number stats,
the bordered summary/key-value explanation block, GOV.UK-style tables, the warning
text component (the "!" in a black circle), a green start button, the GOV.UK
palette (blue #1d70b8, green #00703c, red #d4351c, grey rules, yellow #ffdd00
focus), and Arial (GOV.UK's own GDS Transport fallback). Light and dark themes.
Added an independence disclaimer (not affiliated with or endorsed by DEFRA / GOV.UK,
visually inspired only), which matters if it goes client-facing. Preserved the
mockup at `docs/mockups/govuk_report_view.html` as the reference for theming the
real Streamlit app next. Offered to theme app.py to match (config.toml palette +
CSS) and fold in the 420-duplicate fix at the same time.

**Artifacts:** docs/mockups/govuk_report_view.html (design reference; external
Artifact updated at the same URL).

---

### 2026-07-08 · P17
**Prompt (verbatim):** "document the session"

**Response summary:** Recorded P15 to P17 in this log and added STATUS handoff H9.
This block of prompts was about SEEING the product, not changing the pipeline: the
committed output is the design-reference mockup plus these docs. Captured the two
open follow-ups the exploration surfaced: (1) dedupe the renamed-and-moved output
(420 near-duplicates on real data), and (2) optionally theme the Streamlit app to
the GOV.UK-familiar look using the saved mockup. No pipeline code changed; 26 tests
still green.

---

### 2026-07-08 · P18
Branch: `claude/best-practices-instructions-p7hgfh`.

**Prompt (verbatim):** "attached is another set of best practices instructions
for this project" (attachment: `modelanddocspractices.md`, a standing-preferences
doc covering per-session model selection and documentation structure/archival),
then "open pr and merge".

**Response summary:** Adopted the doc. The project already had the status,
decisions, and prompt-log docs, so I added the missing pieces: `docs/REFERENCE.md`
(the read-on-demand reference doc holding the per-session model-selection guidance
and the backlog moved out of STATUS), and the `docs/archive/` ISO-week rotation
convention with an index, rotating handoff H8 into `STATUS_2026-W28.md`. Recorded
the four-doc structure, the reference-doc role, and the archival/rotation rules in
WORKING_PREFERENCES.md and CLAUDE.md, and trimmed STATUS to a lean snapshot.
Docs-only; no pipeline code changed. Note: the assigned branch was cut from a stale
base, so I reset it onto current `main` before applying, to avoid clobbering the
merged PRs #4 to #8.

**Artifacts:** docs/REFERENCE.md, docs/archive/README.md,
docs/archive/STATUS_2026-W28.md, docs/WORKING_PREFERENCES.md, docs/STATUS.md,
docs/PROMPT_LOG.md, CLAUDE.md. PR #9.

**Artifacts:** docs/PROMPT_LOG.md, docs/STATUS.md.

---

### 2026-07-08 · P17
**Prompt (verbatim):** "1. commit the playbook and ef version explainer docs
shared in the beginning of the chat to the repo as I can't find them anywhere in
the repo. 2. set the main branch as default"

**Response summary:** Committed the two source documents shared at the start (the
build playbook and the MVP spec PDF) into `docs/reference/`, shipped via PR #10
squash-merged into `main`, then realigned the dev branch. Could not set the
repository default branch to `main`: there is no MCP tool for repo settings and no
direct GitHub API access in this environment, so it is a manual owner step (GitHub
repo Settings, Branches, switch default to `main`). Note: this session's branch was
far behind the shared `main` (parallel sessions had merged PRs #1 to #9); the
fetch and reset brought the tree up to the current state and integration was clean.

**Artifacts:** docs/reference/Build_Playbook.md,
docs/reference/MVP_Spec_and_Build_Playbook.pdf. PR #10. docs/PROMPT_LOG.md,
docs/STATUS.md.
### 2026-07-08 · P19
Branch: `claude/whats-next-fnjxkf` (reset onto current `main`, which had merged
PRs #5 to #9 the stale base lacked).

**Prompt (verbatim):** "What's next?"

**Response summary:** Picked the top backlog item, then found it was bigger than a
readability chore. On the owner's real data the renamed-and-moved path (D10) was
emitting 420 near-identical explanation blocks and ~420 explain_change API calls
per run, and because DEFRA reordered the HGV sub-tables the greedy matcher scattered
mixed-direction +-100% deltas: 420 confident single-direction explanations off that
scatter is the fabricated precision D2 forbids. Fixed by grouping relabels into
rename families (`relabel.group_relabels`), so 460 pairs read as 11 table families
and 420 material pairs as 10 grounded family explanations (~10 API calls). Kept it
honest: value movement is a RANGE with an up/down split, a both-ways family gets a
"mixed direction, review each" flag not a false single-direction claim, and the
grounded note (retrieved once per family) explains the whole family including why
the deltas scatter. One-variant families keep their full names, so the synthetic
Fuel-oil relabel is unchanged. Footprint math untouched (relabels stay review-only,
D9). 32 tests green (was 26); demo and microcopy gate clean. Recorded as D14; moved
the finer within-family pairing to the REFERENCE backlog.

**Artifacts:** src/relabel.py, src/pipeline.py, src/report.py, app.py, run_demo.py,
tests/test_relabel.py, docs/DECISIONS.md, docs/STATUS.md, docs/REFERENCE.md,
docs/PROMPT_LOG.md.

---

Branch for all entries below: `claude/project-progress-review-b8wwaa`.

### 2026-07-08 · P20
**Prompt (verbatim):** "how's the project going compared to the goal and plan as
per the docs"

**Response summary:** Read the original plan (`docs/reference/Build_Playbook.md`,
the MVP spec) against the living docs and the code, and gave an honest scorecard:
the MVP the playbook describes is built, green (32 tests), and running on the real
DEFRA 2025->2026 workbooks; all 7 build prompts and all 4 acceptance criteria are
met; the project has gone beyond the plan into relabel families and three CI gates.
Named the deliberate open gaps (within-family per-variant deltas, Streamlit
theming, semantic relabels, lockfile, Gemini only reachable on the owner's
machine). No code changed.

**Artifacts:** none (assessment only).

---

### 2026-07-08 · P21
**Prompt (verbatim):** "i want you to remember a new goal: the getting hired part
should be a side effect of this tool. I want this tool to be genuinely useful to
specific audience in sustainability field/community. is it fulfilling that? if not,
what should be scoped and how should the goal and scope be formaulated? ... brainstorm
this using multiple agents with various expertise and personalities ... produce a
thorough report of goal, scope, audience, vision and mission".

**Response summary:** Ran a multi-agent Workflow: six diverse expert personas (LCA
practitioner, climate-SaaS strategist, standards/assurance expert, solo-consultant
end user, skeptical VC, community/GTM lead), two adversarial critiques, and a
synthesis (9 agents, web-grounded competitive + regulatory claims). Unanimous
verdict: "partly useful" today, because the tool eats a toy 5-line BOM, not the
user's real factor register (strong where least defensible, absent where the moat
lives). Reframed: primary audience is the UK solo/boutique DEFRA consultant;
getting-hired is a side effect (in a small pond the public artifact IS the hiring
strategy). Wrote vision, mission, positioning, scope IN/OUT, risks, and the next 3
moves to `docs/VISION.md`. Key external finding: the "nobody explains the DEFRA
delta" wedge is false (Acclaro, EmissionFactors.net, Circular Ecology, the EMA,
and DEFRA's own reports explain the headline movers for free); the defensible
value is the long tail against the user's own register.

**Artifacts:** docs/VISION.md.

---

### 2026-07-08 · P22
**Prompt (verbatim):** "I don't understand your findings nor recommendations.
explain me clearly"

**Response summary:** Re-explained the panel's findings in plain English for the
non-technical owner: the tool has two halves (the working, valuable half is the
relabel reconciliation and the no-guess honesty; the missing half is that it only
runs on a fake tiny product list, not a real messy client spreadsheet). Named the
one real user (the small independent UK consultant, who is also who would hire
him), and gave the three next moves. No code changed.

**Artifacts:** none (explanation only).

---

### 2026-07-08 · P23
**Prompt (verbatim):** "go ahead" (to write a concrete plan for VISION move #2,
make the tool accept a real user's spreadsheet).

**Response summary:** Read how the BOM flows today (`pipeline.py` reads a clean
3-column CSV) and wrote `docs/PLAN_real_data_ingest.md`: a 4-step, plain-English
plan (forgiving reader, confirm-your-columns in the app, rank changes by impact on
the user's own footprint, a locking test), each with a way to SEE it work, plus an
explicit OUT list and the "validate with a real file first" advice. Also committed
the untracked `docs/VISION.md` (stop-hook flagged it). Recorded the goal reframe as
DECISIONS D15.

**Artifacts:** docs/PLAN_real_data_ingest.md, docs/VISION.md, docs/DECISIONS.md.

---

### 2026-07-08 · P24
**Prompt (verbatim):** "go ahead with step 1"

**Response summary:** Built the forgiving inventory reader `src/ingest.py`: reads
.csv/.xlsx, guesses which column is the item/quantity/unit from awkward headers via
a plain synonyms list (no AI), reports its confidence so the app can ask when
unsure, tolerates "1,200"-style numbers, and SETS ASIDE rows with a blank/garbled
quantity, missing unit, or missing item (with a reason) instead of guessing, the
no-guess rule (D2) extended to the column level. Added `scripts/check_ingest.py`
(runs it on a deliberately messy fixture, prints the mapping and set-aside rows)
and `tests/test_ingest.py` (6 tests). Suite 38 green. Recorded as DECISIONS D16.

**Artifacts:** src/ingest.py, scripts/check_ingest.py, tests/test_ingest.py,
docs/DECISIONS.md.

---

### 2026-07-08 · P25
**Prompt (verbatim):** "go ahead with step 2"

**Response summary:** Wired the reader into `app.py`. The uploader now accepts
.csv and .xlsx with any column names; after upload the app shows three dropdowns
pre-filled with the guessed mapping for the user to confirm or fix, and the Run
button stays disabled until the mapping is complete and unambiguous. Set-aside rows
are listed in a new "Rows set aside" section. The built-in sample still runs when
nothing is uploaded. The microcopy gate caught two em dashes I introduced (the
"— select —" placeholder and a caption), now fixed. Verified: app boots headless
(HTTP 200, no errors) and a messy in-memory xlsx runs read->guess->build->full
pipeline end to end on synthetic data (2 good rows matched, 2 set aside). Suite 38
green.

**Artifacts:** app.py.

---

### 2026-07-08 · P26
**Prompt (verbatim):** "go ahead with step 3"

**Response summary:** Made the report lead with the changes that moved the user's
OWN footprint the most. Each flagged factor's explanation now carries
`footprint_impact` (kg CO2e it moved in this product, summed across the BOM lines
that matched it) and its share of the total change; explanations are sorted by that
impact. Report and app show the kg impact and share next to each change. Verified on
synthetic data: aluminium (72.6% of the total change) leads, then electricity,
diesel, plastics, water (which fell 15.8% but is last because it barely touches this
product). Suite 38 green, microcopy clean. Updated STATUS (H13) and the plan doc to
mark steps 1-3 shipped.

**Artifacts:** src/pipeline.py, src/report.py, app.py, docs/STATUS.md,
docs/PLAN_real_data_ingest.md.

---

### 2026-07-08 · P27
**Prompt (verbatim):** "document the session"

**Response summary:** Recorded P20 to P27 in this log, added DECISIONS D15 (goal
reframed to genuine usefulness, primary audience the UK solo/boutique DEFRA
consultant, getting-hired a side effect) and D16 (real-data ingest as the
demo-to-tool build, no-guess extended to columns), and refreshed STATUS. Session
summary: (1) honest status review against the original plan; (2) a six-persona
multi-agent brainstorm that reframed the goal around genuine usefulness
(`docs/VISION.md`); (3) shipped VISION move #2 (real-data ingest) in three steps,
forgiving reader + confirm-your-columns + impact ranking. Gates at session end: 38
tests green, microcopy linter clean, app boots. Open next: header-row tolerance,
then VISION move #3 (a dated, cited, printable memo), and validating with a real
client file.

**Artifacts:** docs/PROMPT_LOG.md, docs/DECISIONS.md, docs/STATUS.md.
