# CLAUDE.md — EF Version Explainer

Project rules and context for anyone (human or AI) working in this repo.
Read this first.

## What this project is

**EF Version Explainer** compares two annual versions of the UK DEFRA/DESNZ
GHG conversion-factor workbooks, flags factors that changed beyond DEFRA's own
materiality thresholds (**>5% for Scope 1/2, >10% for Scope 3**), recalculates a
product's carbon footprint under both versions, and uses the Claude API to
**explain each change** in plain English plus a methodology-grade note — the
"explain-the-delta" work a consultant would otherwise do by hand.

The wedge is the **explanation**, not the recomputation. Big platforms already
recompute; nobody explains a version delta in a client-ready, methodology-sound
way. That is the whole point of this tool.

## Owner

Suhas Pala. Non-developer domain expert (sustainability / LCA). Explanations of
code choices should be in plain English; prefer simple, readable code over
clever code.

## Hard constraints (do not violate without asking)

- **Stack:** Python + pandas + Streamlit + openpyxl + pdfplumber + the Anthropic
  SDK, plus `rapidfuzz` for fuzzy matching. Nothing else heavyweight.
- **No** database, login, cloud, Docker, or web framework. Data lives as local
  files in `data/` (CSV / parquet / xlsx / pdf).
- **Carbon only** (kg CO2e) for v1. No other impact categories.
- Build in **small, testable steps**. Never scaffold features nobody asked for.
- Every code change must come with a way to **SEE it work** — a runnable check
  or printed result.
- Keep functions small and named in plain language.

## The domain rule that must never be broken

**Never silently guess.** A wrong emission-factor match, or an invented reason
for a change, is worse than admitting uncertainty. This is the credibility of
the tool (and of the owner):

- Factor matching below the confidence threshold is flagged `needs_review`, not
  guessed.
- The AI explanation layer may only use numbers passed into it. It must **never
  invent or estimate a factor**. If the DEFRA changes report does not explain a
  change, it must say exactly:
  `No official reason found in the DEFRA changes report.`

## The pipeline (src/)

```
DEFRA old.xlsx ┐
               ├─►[loader]─►[diff]─► flagged changes ┐
DEFRA new.xlsx ┘                                     │
                                                     ├─►[explain]─► Report
Product BOM CSV ─►[matching]─►[recompute]────────────┘   (grounded in changes PDF)
```

| Module | Function | Job |
|---|---|---|
| `src/loader.py` | `load_defra(path, version_label)` | Normalize a DEFRA workbook to one tidy table: `activity, unit, kg_co2e, scope, category, version` |
| `src/diff.py` | `diff_versions(df_old, df_new)` | Join on (activity, unit), compute `pct_change`, set `flagged` per thresholds; mark added/removed |
| `src/matching.py` | `match_bom(bom_df, factors_df)` | Map BOM line items to DEFRA activities: exact → fuzzy → `needs_review`. Never guesses. |
| `src/recompute.py` | `recompute(matched_df, diff_df)` | Footprint old vs new; per-line deltas; totals; coverage % |
| `src/explain.py` | `explain_change(...)` | Grounded Claude call → plain-English reason + methodology note + target flag |
| `src/report.py` | `build_markdown_report(...)` | Assemble the one-page Markdown report |
| `app.py` | Streamlit UI | Sidebar (pick versions, upload BOM) + main report view |
| `run_demo.py` | end-to-end | Runs the whole pipeline on the sample product with one command |

## Data (data/)

Real DEFRA data is **not** committed (large, and the build environment cannot
reach gov.uk). To use real data, drop these into `data/`:

- `defra_2025.xlsx`, `defra_2026.xlsx` — "Government conversion factors for
  company reporting" (full set) for two years, from gov.uk.
- `defra_changes_2026.pdf` — the DEFRA "major changes" report for the new year.
- `sample_bom.csv` — a product bill-of-materials (`line_item, quantity, unit`).

Until real files are added, `scripts/make_synthetic_data.py` generates
**clearly-labelled SYNTHETIC** DEFRA-format workbooks, a changes PDF, and a
sample BOM so the whole pipeline runs today. Synthetic files are marked as such
and must never be presented as real DEFRA figures.

## AI / API notes

- Model: `claude-sonnet-5` for the explanation layer (cost/quality balance).
- Set `ANTHROPIC_API_KEY` to use the real API. If it is not set, `explain.py`
  falls back to a deterministic **offline** explainer that still obeys the
  grounding rules (so the demo and the trap test run without a key). Offline
  output is labelled so it is never mistaken for a real model answer.

## How to run

```bash
pip install -r requirements.txt
python scripts/make_synthetic_data.py     # only if you don't have real DEFRA files
python run_demo.py                         # end-to-end on the sample product
streamlit run app.py                       # the dashboard
pytest -q                                  # the tests
```

## What NOT to do

1. Don't add ecoinvent (licensed) — DEFRA only for v1.
2. Don't add a database / login / payments.
3. Don't cover every impact category or dataset — carbon + DEFRA proves it.
4. Don't let the AI guess a match or invent a reason.
5. Don't polish before it works end-to-end.
