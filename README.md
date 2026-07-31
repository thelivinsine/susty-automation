# EF Version Explainer

**Explain the delta when emission factors change.**

**Live app:** <https://efdiff.streamlit.app/>

Every year the official databases that convert activity (a litre of diesel, a
kWh of grid electricity) into kg CO₂e quietly update their numbers. When they do,
every company's carbon footprint silently shifts, and someone has to work out
*what changed, why, and whether it breaks the company's climate targets.* Today
that is manual consulting work in Excel and Word.

This tool does it automatically. Given **two annual versions of the UK
DEFRA/DESNZ GHG conversion-factor workbooks** and **one product's
bill-of-materials**, it:

1. **Normalizes** both workbooks into one tidy table.
2. **Diffs** them and flags factors that moved beyond DEFRA's own materiality
   thresholds (>5% Scope 1/2, >10% Scope 3).
3. **Matches** the product's materials to DEFRA activities, and flags anything
   it can't match with confidence rather than guessing.
4. **Recomputes** the product footprint under both versions and reports how much
   of it could actually be computed (coverage %).
5. **Explains** each flagged change in plain English + a methodology-grade note,
   **grounded strictly in the official DEFRA "major changes" report**, and says
   "no official reason found" instead of inventing one.

The wedge is step 5, on the long tail. The headline movers (the grid-electricity
drop, aviation, rail) get free write-ups within days of each release. What nobody
produces is complete, per-factor, reproducible coverage against *your* register.

## Goal, purpose, vision

**Goal.** Turn the annual DEFRA factor update from a week of manual Excel
archaeology into a report you can read in ten minutes and hand to a client.

**Purpose.** Serve the UK solo or boutique carbon consultant, the person who
personally re-bases a client inventory every year and has to defend each number.
Two things here are built for exactly that and are hard to get elsewhere: the
relabel-family reconciliation that collapses DEFRA's ~500 added and ~500 removed
rows into a handful of readable rename families, and the no-guess discipline
enforced in code (an unconfident match is flagged `needs_review`, and a change the
DEFRA notes do not explain says so verbatim instead of inventing a reason). That
discipline is the point: it is what lets a consultant put their name on the
output, and what a raw chatbot prompt cannot give them.

**Vision.** A world where updating to the new year's factors is a reviewed,
cited, ten-minute task instead of a week of guesswork, and where "why did this
number move?" always has a traceable answer.

The honest current state, and the roadmap out of it, live in
[`docs/VISION.md`](docs/VISION.md): a six-persona expert panel judged the tool
"partly useful" until it eats a real inventory rather than a toy 5-line BOM.
Real-data ingest has since shipped. The cited, dated, printable memo has not.

## Quickstart

```bash
pip install -r requirements.txt

# generate clearly-labelled synthetic demo data (skip if you have real DEFRA files)
python scripts/make_synthetic_data.py

# run the whole pipeline end-to-end and write a report
python run_demo.py

# or explore it in the browser
streamlit run app.py

# run the tests
pytest -q
```

### Using real DEFRA data

The demo ships with **synthetic, clearly-labelled** factor data (in the same
DEFRA layout) so it runs anywhere. To use genuine figures, download the full-set
workbooks from gov.uk ("Government conversion factors for company reporting") and
drop them into `data/`:

- `ghg-conversion-factors-2025-full-set.xlsx`,
  `ghg-conversion-factors-2026-full-set.xlsx`: two years of the full workbook
  (the gov.uk filenames work as-is; `defra_2025.xlsx` / `defra_2026.xlsx` also work)
- `sample_bom_real.csv`: your product's bill-of-materials (`line_item, quantity, unit`)

The tool prefers real files over the synthetic ones automatically. For the change
explanations it uses a Major Changes PDF if you add one (`*change*.pdf`),
otherwise it reads the **"What's new" sheet inside the new workbook**.

> **A note on real data:** between two years the full set typically shows several
> hundred "added" and "removed" activities, most of them DEFRA *relabels* (e.g.
> "HGV (all diesel)" → "HGV (non-refrigerated, all diesel)"). The tool reports
> those separately and only counts factors present in *both* years, past
> threshold, as material movers.

### The AI explanation layer

The explainer picks its backend from whichever API key is set, no code change
needed:

```bash
# Google Gemini (default model gemini-2.5-flash; override with GEMINI_MODEL)
export GEMINI_API_KEY=your-key-here

# …or Anthropic Claude (default claude-sonnet-5; override with ANTHROPIC_MODEL)
export ANTHROPIC_API_KEY=your-key-here
```

Set it in your shell before running, or (easier) copy the template and fill in
your key:

```bash
cp .env.example .env      # then paste your key into .env (it's git-ignored)
```

The app and `run_demo.py` load `.env` automatically. If both keys are set, Gemini
wins. Without any key the tool falls back to a deterministic **offline** explainer
that obeys the same grounding rules, so the demo, and the "won't invent a reason"
trap test, run without any key.

> **GitHub secrets note:** repository secrets only reach **GitHub Actions**
> runs, not your laptop or the Streamlit dashboard. Use a local `.env` for
> running locally; use GitHub secrets only if you run this in a CI workflow (and
> Streamlit Cloud's own Secrets manager if you deploy the dashboard there).

Whichever model runs, the grounding rules are enforced in code: it can only use
the numbers and DEFRA text passed to it, and where the notes are silent it must
say so rather than invent a reason.

## Putting it online for non-technical users

The tool is a Streamlit app, so it can't live on GitHub Pages (that only serves
static files). The intended home is **Streamlit Community Cloud** (free), which
gives you a shareable link users open in a browser, no install.

Access is designed so the tool stays open while API cost stays controlled:

- **Open to everyone** on the free, deterministic offline explanations.
- **AI-written explanations behind Google sign-in**, unlocked only for people on
  an approved list (set in the host's secrets). Signed-in-but-not-approved users,
  and anonymous visitors, still get the free offline version.
- A **spending cap** on the API account as the hard backstop.

When no sign-in provider is configured (local `streamlit run`, the demo, the
tests), the app runs exactly as before: the API key, if set, drives the explainer
for everyone. The full click-by-click setup is in
[`docs/DEPLOY_GUIDE.md`](docs/DEPLOY_GUIDE.md); the secrets template is
[`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example).

## How it's built

Deliberately boring and readable: Python + pandas + Streamlit + openpyxl +
pdfplumber + rapidfuzz + the Gemini and Anthropic SDKs. No database and no web
framework. Data lives as local files in `data/`. The only two additions to that
rule are the optional Google sign-in that guards the paid AI tier and the
Streamlit Cloud deployment that hosts the app.
See [`CLAUDE.md`](CLAUDE.md) for the full design and the domain rules.

```
src/
  loader.py      load_defra()      normalize a DEFRA workbook
  diff.py        diff_versions()   flag material changes by threshold
  matching.py    match_bom()       BOM -> factor, never guesses
  recompute.py   recompute()       footprint old vs new + coverage
  changes_pdf.py load_change_chunks()/retrieve_passage() grounding over the
                 Major Changes PDF or the workbook's "What's new" sheet
  explain.py     explain_change()  grounded Claude call (+ offline fallback)
  report.py      build_markdown_report()
  pipeline.py    run_pipeline()    the glue
app.py           Streamlit dashboard
run_demo.py      one-command end-to-end demo
```

## The one rule that must not break

**Never silently guess.** A wrong factor match, or an invented reason for a
change, is worse than admitting uncertainty. It's the whole credibility of the
tool. Low-confidence matches are flagged for a human; changes the DEFRA report
doesn't explain are reported as unexplained, not fabricated.
