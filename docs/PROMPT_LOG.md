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
