# CLAUDE.md: EF Version Explainer

Project rules and context for anyone (human or AI) working in this repo.
Read this first.

## What this project is

**EF Version Explainer** compares two annual versions of the UK DEFRA/DESNZ
GHG conversion-factor workbooks, flags factors that changed beyond DEFRA's own
materiality thresholds (**>5% for Scope 1/2, >10% for Scope 3**), recalculates a
product's carbon footprint under both versions, and uses the Claude API to
**explain each change** in plain English plus a methodology-grade note, the
"explain-the-delta" work a consultant would otherwise do by hand.

The wedge is the **explanation**, not the recomputation. Big platforms already
recompute; nobody explains a version delta in a client-ready, methodology-sound
way. That is the whole point of this tool.

## Owner

Suhas Pala. Non-developer domain expert (sustainability / LCA). Explanations of
code choices should be in plain English; prefer simple, readable code over
clever code.

## House rules (read `docs/` first)

Standing working preferences live in **`docs/WORKING_PREFERENCES.md`** and
override defaults. The essentials:

- **No em dashes** in any visible string or chat reply. Use a period, comma,
  colon, parentheses, or "so"/"and". En dash and bullet are fine.
- Act as a decisive CTO for a non-technical owner. One recommended path, not a
  menu. Say what was chosen in one line and proceed.
- **Auto-ship:** when a change is complete and green, open a PR into `main` and
  squash-merge it, then realign the dev branch (`docs/WORKING_PREFERENCES.md` has
  the housekeeping steps). `main` is production and source of truth.
- Token discipline: targeted search over whole-file reads, batch tool calls, no
  subagents for routine work.
- **Pick the session model up front** by the dominant work (frontier for design,
  heavy for build, cheap for fill-in); step up a tier for high-stakes work. The
  per-session guidance and the backlog live in `docs/REFERENCE.md`.
- After every significant task, update **both** `docs/STATUS.md` and
  `docs/PROMPT_LOG.md` (and any stale docs). Backlog and model guidance live in
  `docs/REFERENCE.md`; locked decisions live in `docs/DECISIONS.md` (read before
  undoing anything marked LOCKED). Older handoffs and prompt entries rotate into
  `docs/archive/` by ISO week.

## Hard constraints (do not violate without asking)

- **Stack:** Python + pandas + Streamlit + openpyxl + pdfplumber + the Anthropic
  SDK, plus `rapidfuzz` for fuzzy matching. Nothing else heavyweight.
- **No** database, login, cloud, Docker, or web framework. Data lives as local
  files in `data/` (CSV / parquet / xlsx / pdf).
- **Carbon only** (kg CO2e) for v1. No other impact categories.
- Build in **small, testable steps**. Never scaffold features nobody asked for.
- Every code change must come with a way to **SEE it work**: a runnable check
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

Real DEFRA full-set workbooks live in `data/`. The loader recognizes the gov.uk
names automatically:

- `ghg-conversion-factors-2025-full-set.xlsx`,
  `ghg-conversion-factors-2026-full-set.xlsx`: "Government conversion factors
  for company reporting" (full set), two years. (Aliases `defra_2025.xlsx` /
  `defra_2026.xlsx` also work.)
- `sample_bom_real.csv`: a product bill-of-materials (`line_item, quantity,
  unit`) matched to real activities. A real `data/sample_bom.csv` overrides it.

**Grounding for the explanations:** if a Major Changes PDF (`*change*.pdf`) is in
`data/`, it is used; otherwise the tool reads the **"What's new" sheet inside the
new workbook**, which explains that year's methodology revisions and relabels.

Real full-set workbooks are large; `.gitignore` keeps the generic `defra_*.xlsx`
aliases out of git, but the gov.uk-named files are tracked when committed.

Until real files are added, `scripts/make_synthetic_data.py` generates
**clearly-labelled SYNTHETIC** workbooks in the **same DEFRA layout** (metadata
scope row, guidance preamble, `Activity | descriptor | Unit | kg CO2e` table,
multi-block super-header), plus a changes PDF and a sample BOM, so the whole
pipeline runs today. Synthetic files are marked as such and must never be
presented as real DEFRA figures.

**Real-data note:** across 2025→2026 the full set shows ~500 "added" and ~500
"removed" activities, most of them DEFRA *relabels* (e.g. waste "Incineration with
energy recovery" → "Combustion"; "HGV (all diesel)" → "HGV (non-refrigerated,
all diesel)"). These are reported separately and are **not** counted as material
movers; only factors present in both years and past threshold are "flagged".

## AI / API notes

The explanation layer picks its backend from whichever API key is set:

- **Gemini**: set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`). Model from
  `GEMINI_MODEL` (default `gemini-2.5-flash`). Uses the `google-genai` SDK.
- **Claude**: set `ANTHROPIC_API_KEY`. Model from `ANTHROPIC_MODEL` (default
  `claude-sonnet-5`). Uses the `anthropic` SDK.
- **Offline**: if neither key is set, `explain.py` falls back to a deterministic
  offline explainer that still obeys the grounding rules (so the demo and the
  trap test run without a key). Offline output is labelled so it is never
  mistaken for a real model answer.

If both keys are set, Gemini wins. Whatever the backend, the grounding rules are
enforced in code (`_finalize`), so no model can invent a reason the DEFRA notes
don't contain, and the deterministic target-impact flag always overrides the
model's. Set the key as an environment variable (or in a local `.env`, which is
git-ignored), do not hard-code it.

## How to run

```bash
pip install -r requirements.txt
python scripts/make_synthetic_data.py     # only if you don't have real DEFRA files
python run_demo.py                         # end-to-end on the sample product
streamlit run app.py                       # the dashboard
pytest -q                                  # the tests
```

## What NOT to do

1. Don't add ecoinvent (licensed): DEFRA only for v1.
2. Don't add a database / login / payments.
3. Don't cover every impact category or dataset: carbon + DEFRA proves it.
4. Don't let the AI guess a match or invent a reason.
5. Don't polish before it works end-to-end.
