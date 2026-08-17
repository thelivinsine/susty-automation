# Front-end audit and gap analysis, 2026-08-17

Method: read `CLAUDE.md`, `docs/VISION.md` and `docs/STATUS.md` for the stated
goal and purpose, then ran the app (`streamlit run app.py`) on the owner's real
2025/2026 DEFRA full-set workbooks and measured it in a real browser (Chromium,
via the Claude Browser preview tools) at 375, 738/768 and 1440px, before and
after pressing Run. Findings below are measured, not eyeballed.

**Status note (added after the fact):** gaps G1 and G2, and the two P0
recommendations they produced, were fixed the same day. See
[DECISIONS.md D24](../DECISIONS.md) and `STATUS.md` H24 for what shipped
(PR #29, squash-merged `e6e2b90`). This document is kept as the point-in-time
record of what the audit found, the way `2026-07-31_frontend_ux_audit.html` is
kept verbatim; it is not updated to erase what has since been closed.

## What the app is supposed to do

From `VISION.md` and `CLAUDE.md`: hand a UK solo consultant a grounded,
no-guess, cited answer to "what moved in the new DEFRA release and why", with
the **explanation as the wedge**, not the recomputation. D23 made the
interactive comparison the app's front door.

## What holds up

Not flattery, these are the things tried and not broken:

- The design layer survives reruns (exactly one token stylesheet after
  interacting), the sticky numbered nav and its scrollspy work, `:focus-visible`
  and `prefers-reduced-motion` are handled.
- Zero horizontal page scroll at 375, 738 and 1440px (`scrollWidth ==
  clientWidth` at all three).
- Direction never rides on colour: glyph, sign and a screen-reader word.
- The trust discipline is genuinely visible in the UI: coverage meter against
  the stated 95% bar, held lines explained in a sentence rather than a score,
  completeness checklist before export, "Cited" badge with the verbatim DEFRA
  quote.
- Every number on screen reconciles with the pipeline (2,111 / 2,133 / 67 / 76
  / 54 / 460).

## Gap analysis

The through-line: **the front door delivered the commodity half of the product
(the diff) and hid the differentiated half (the grounded reason).** Everything
in P0 followed from that.

| # | Gap | Evidence |
|---|---|---|
| G1 | Front door shows what changed, never why | `explain_flagged_only` in `pipeline.py` restricted explanations to activities in an uploaded BOM. A cold visitor saw 67 material movers and zero reasons. |
| G2 | 15.3s of spinner before the front door painted | Timed `compare_versions` on the real workbooks. Cache was in-process, so it was paid again on every restart, redeploy or Cloud sleep. |
| G3 | Workbooks parsed twice per session | `run_pipeline` called the uncached `compare_versions`, not the `@st.cache_data` wrapper in `app.py`. A Run click cost another 14.1s. |
| G4 | Default table is a canvas grid with machine column names | Measured in the default state: `canvas` 1, `<table>` 0, headers read `activity, unit, scope, kg_co2e_old`. The readable version only appeared above 500 rows behind a toggle. |
| G5 | Status is filterable but not visible | The displayed columns omitted `status`. Filtering to "New" showed `n/a` in one factor column with no word saying why. |
| G6 | Language is product/BOM-first, audience is register-first | H1 read "against your product", section 2 "Product footprint". `VISION.md` section 6 explicitly says kill the toy BOM as the hero. |
| G7 | No release picker, and the settings that exist are hidden | Sidebar auto-collapses at 768px and under, while the canvas says "Rename either in the sidebar." |
| G8 | Nothing is shareable | No filter state in the URL. The caption says "Clear the filters" but no such control exists. |
| G9 | After a run, the answer is 1,700px down | Measured `#s-result` offset. The masthead flips to "Report ready" and nothing takes the reader there. |
| G10 | Counts do not reconcile on screen | Fact bar says 2,111 and 2,133, table says 2,647, section 3 says 1,597. Nothing explains that 2,647 is the union. |
| G11 | One label, two meanings | `reason` rendered as "Why it was set aside" in both the held-for-review table (not set aside) and the actual set-aside table. |
| G12 | Masthead drops the version pair under 768px | `.fact` is `display:none`, losing the one fact that identifies the run. |
| G13 | Four export files rebuilt on every rerun | `export_pack` was uncached, 0.19s per filter keystroke. |
| G14 | A-07 stale as written | The file input carried `aria-label="file upload"` on this Streamlit build. The name is generic rather than absent, and the Upload button read "uploadUpload" (icon ligature leaking into the name). |

## Recommendations

**P0, ship this week. Both are small and both are about the front door.**

1. **Explain the movers on the landing surface.** Add a "Why did this change"
   drawer to the comparison, for the material movers only, using the existing
   grounded retrieval path with no BOM required. This is the wedge, and today
   it is behind an upload. Cheapest honest version: run `retrieve_citation` for
   the top movers and show the verbatim DEFRA quote plus "No official reason
   found in the DEFRA changes report" where there is none. No model call needed
   for v1 of this.
2. **Kill the 15 second cold spinner.** One word first: `persist="disk"` on the
   `_compare` cache. If Cloud restarts still bite, commit a prebuilt parquet of
   the joined diff and load that, regenerating it with a script when the
   workbooks change.

**P1, next.**

3. **Stop parsing the workbooks twice.** Give `run_pipeline` an optional
   `comparison=` argument and pass the cached one from `app.py`. Roughly three
   lines, saves 14s on the Run click.
4. **Make the default table readable.** Rename and format the columns before
   handing them to `st.dataframe` (`column_config`), so "Factor (2025)",
   "Factor (2026)", "Change" appear instead of `kg_co2e_old`. Same words as the
   semantic table.
5. **Show the status column,** with the "Renamed" flag. A filter you can set
   but cannot see the result of is a broken loop.

**P2, this cycle.**

6. **Reframe the copy from product to register.** H1 to something like "What
   changed between two DEFRA releases, and why". Keep the product recompute as
   the second act, which is what the page order already does. This is the
   visible half of the VISION reframe.
7. **Filter state in the URL** (`st.query_params`), already the repo's own next
   candidate. It turns a narrowed view into a link a consultant can send.
8. **Let the reader pick the releases,** or at minimum move the version labels
   out of the collapsing sidebar into step 1 where the canvas already points.
9. **Take the reader to the answer after a run:** collapse section 1 to a one
   line summary once results exist, or scroll to `#s-result`.

**P3, polish.**

10. Add one sentence reconciling 2,111 + 2,133 into 2,647.
11. Split the `reason` column label into "Why it was held" and "Why it was set
    aside".
12. Keep the version pair in the masthead under 768px (shrink it, do not hide
    it).
13. Cache `export_pack`.
14. Retest and restate A-07 rather than carrying it as written.
15. Add a skip link and an in-app preview of the printable memo, so the
    deliverable is visible before download.

**P4, resist for now.** Dark mode (Streamlit theme job, not CSS), a second
dataset, and any drill-down that turns the comparison into a spreadsheet clone.

## What actually shipped from this list

P0 items 1 and 2, and P1 items 3, 4 and 5, shipped the same day as D24 (PR #29,
squash-merged `e6e2b90`). P2 through P4 remain open; the current priority order
lives in `STATUS.md`'s "Resume here" section.
