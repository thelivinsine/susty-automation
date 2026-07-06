# EF Version Explainer

**Explain the delta when emission factors change.**

Every year the official databases that convert activity (a litre of diesel, a
kWh of grid electricity) into kg CO₂e quietly update their numbers. When they do,
every company's carbon footprint silently shifts — and someone has to work out
*what changed, why, and whether it breaks the company's climate targets.* Today
that is manual consulting work in Excel and Word.

This tool does it automatically. Given **two annual versions of the UK
DEFRA/DESNZ GHG conversion-factor workbooks** and **one product's
bill-of-materials**, it:

1. **Normalizes** both workbooks into one tidy table.
2. **Diffs** them and flags factors that moved beyond DEFRA's own materiality
   thresholds (>5% Scope 1/2, >10% Scope 3).
3. **Matches** the product's materials to DEFRA activities — and flags anything
   it can't match with confidence rather than guessing.
4. **Recomputes** the product footprint under both versions and reports how much
   of it could actually be computed (coverage %).
5. **Explains** each flagged change in plain English + a methodology-grade note,
   **grounded strictly in the official DEFRA "major changes" report** — and says
   "no official reason found" instead of inventing one.

The wedge is step 5. Big platforms recompute the new number; nobody explains a
version delta in a client-ready, methodology-sound way.

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

The demo ships with **synthetic, clearly-labelled** factor data so it runs
anywhere. To use genuine figures, download from gov.uk ("Government conversion
factors for company reporting") and drop these into `data/`:

- `defra_2025.xlsx`, `defra_2026.xlsx` — two years of the full workbook
- `defra_changes_2026.pdf` — the "major changes" report for the new year
- `sample_bom.csv` — your product's bill-of-materials (`line_item, quantity, unit`)

The tool automatically prefers real files over the synthetic ones.

### The AI explanation layer

Set `ANTHROPIC_API_KEY` to use the Claude API (`claude-sonnet-5`) for the
explanations. Without a key the tool falls back to a deterministic **offline**
explainer that obeys the same grounding rules — so the demo, and the "won't
invent a reason" trap test, run without any key.

## How it's built

Deliberately boring and readable: Python + pandas + Streamlit + openpyxl +
pdfplumber + rapidfuzz + the Anthropic SDK. No database, no login, no cloud.
See [`CLAUDE.md`](CLAUDE.md) for the full design and the domain rules.

```
src/
  loader.py      load_defra()      normalize a DEFRA workbook
  diff.py        diff_versions()   flag material changes by threshold
  matching.py    match_bom()       BOM -> factor, never guesses
  recompute.py   recompute()       footprint old vs new + coverage
  changes_pdf.py retrieve_passage() grounding retrieval over the changes PDF
  explain.py     explain_change()  grounded Claude call (+ offline fallback)
  report.py      build_markdown_report()
  pipeline.py    run_pipeline()    the glue
app.py           Streamlit dashboard
run_demo.py      one-command end-to-end demo
```

## The one rule that must not break

**Never silently guess.** A wrong factor match, or an invented reason for a
change, is worse than admitting uncertainty — it's the whole credibility of the
tool. Low-confidence matches are flagged for a human; changes the DEFRA report
doesn't explain are reported as unexplained, not fabricated.
