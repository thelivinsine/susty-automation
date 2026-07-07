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
