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
Added/removed are reported separately. The relabel-pairing open question is now
addressed for the common case: see D9.

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

## D9. Relabel matching, chosen over more CI gates (LOCKED direction)
Why this and not another quality gate: the owner challenged whether a lint gate
or loader golden-vectors were the highest-leverage next work. Honest assessment:
the microcopy linter (D-less, shipped) is cosmetic, not correctness. The loader
is already partly covered by the real-workbook test, so golden-vectors would be
incremental hardening of working code. The tool's wedge is the explanation, and
its two real weak spots are retrieval quality and the added/removed clutter.
Relabel pairing attacks the clutter and is the most visible product improvement,
so it was chosen.

How pairing works (`src/relabel.py`, `detect_relabels`): pair a "removed" old
activity with an "added" new one only when it is defensible:
- hard gates: same unit, same scope;
- base similarity: rapidfuzz `token_set_ratio` >= 90 on the whole name;
- leaf guard: the identifying LEAF (last " - " segment, i.e. the fuel/variant)
  must not be SUBSTITUTED. A leaf addition ("Fuel oil" to "Fuel oil (mineral)")
  is fine; a two-way leaf swap ("Petrol" vs "Diesel", "CNG" vs "LPG") is only
  trusted at near-identity (>= 97), so a genuine synonym rename
  ("propylene" to "propene", leaf unchanged) passes but a fuel flip does not.
Assignment is greedy one-to-one (highest score first, each side used once).
Below the bar: never guessed, the activities stay added/removed (the D2 rule).

Result on the owner's real 2025->2026 data: 460 of ~525 added/removed paired as
relabels, leaving 76 genuinely new and 54 genuinely removed (was ~500/500 noise).

Boundaries (deliberate, honest):
- Semantic renames with low string overlap ("Incineration with energy recovery"
  to "Combustion") are NOT caught; those need DEFRA's own relabel notes. Left as
  added/removed rather than guessed.
- Relabels are a review-only grouping in the report and app; they are NOT used in
  the footprint math (which only uses BOM-matched factors present in both years),
  so a mispaired relabel cannot corrupt the carbon number.
- A relabel whose factor value ALSO moved past threshold is shown in the relabel
  table with its delta, but is not yet routed through the AI explainer. That
  (explaining renamed-and-moved factors) is the natural follow-up.
