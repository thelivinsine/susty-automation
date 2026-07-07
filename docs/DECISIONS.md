# Decisions log

The "why" behind decisions. Read before undoing anything marked LOCKED.

## D1. DEFRA only, carbon only, for v1 (LOCKED)
No ecoinvent (licensed), no other impact categories. DEFRA full-set workbooks
prove the concept. Rationale: the wedge is the explanation, not dataset breadth.

## D2. Never silently guess (LOCKED)
Factor matches below the confidence threshold are flagged `needs_review`, not
guessed. The AI layer may only use numbers passed to it, and must say "No
official reason found in the DEFRA changes report" when the notes are silent.
This is the credibility of the tool. Enforced in code (`matching.py`,
`explain._finalize`), not left to prompt wording.

## D3. Loader targets the real full-set layout
Scope is read from sheet metadata (not a column). Table header is
`Activity | descriptors | Unit | kg CO2e | breakdowns`. Descriptor columns are
forward-filled (guarded on `pd.notna`, since `str(NaN) == "nan"` would otherwise
overwrite a level). Repeated `kg CO2e` blocks are expanded per sub-category using
the super-header row. A `Year` column is ignored so factors join across years.

## D4. Added/removed are not "material movers"
On real 2025 to 2026 data there are roughly 500 added and 500 removed activities,
most of which are DEFRA relabels (for example "Incineration with energy recovery"
to "Combustion", "HGV (all diesel)" to "HGV (non-refrigerated, all diesel)").
`flagged` means a material percent change on a factor present in both years.
Added/removed are reported separately. Open question: detect and match relabels
as continuations (not yet built).

## D5. Grounding source: Major Changes PDF, else workbook "What's new"
No standalone changes PDF was provided. The 2026 workbook ships a "What's new"
sheet that explains the year's methodology revisions and relabels. The pipeline
prefers a `*change*.pdf` in `data/`, otherwise reads "What's new". This makes the
explanation layer real on the owner's actual data.

## D6. Explanation backend is provider-agnostic, selected by key
Gemini if `GEMINI_API_KEY`/`GOOGLE_API_KEY` is set (default `gemini-2.5-flash`),
else Claude if `ANTHROPIC_API_KEY` (default `claude-sonnet-5`), else the offline
explainer. Gemini wins if both are set. Owner chose Gemini. Keys load from a
git-ignored `.env` (via python-dotenv) so they are never committed. Grounding and
the target-impact flag are enforced in code for every backend.

Note: the Claude Code web build environment blocks the Gemini endpoint (HTTP 403;
only PyPI and Anthropic are allowlisted), so live Gemini calls run on the owner's
machine, not in that sandbox. Verified graceful fallback to offline mode there.

## D7. Synthetic demo data mirrors the real layout
`scripts/make_synthetic_data.py` emits real-format workbooks (metadata scope row,
guidance preamble, Activity/descriptor/Unit/kg CO2e table, multi-block
super-header) plus a changes PDF and sample BOM. Clearly labelled SYNTHETIC.
Keeps the whole pipeline and the trap test runnable offline and exercises the
real parser.

## D8. main established from the setup branch
`main` did not exist at the start (empty repo). It was created as production from
the completed, green setup work. Going forward, changes ship via PR squash-merged
into `main`, then the dev branch is realigned per the housekeeping rule.
