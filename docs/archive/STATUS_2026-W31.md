

- H19 (2026-07-31): Implemented `docs/PLAN_design_system.md` end to end, in four
  commits: the token layer, the component builders, the app view-layer rewrite,
  and the export pack. The app had injected no CSS at all and had no
  `.streamlit/config.toml`, so every visual decision was a Streamlit default;
  that is what the audit's 12 defects were measured against. **11 of the 12 are
  now closed** (A-07 is not, see below). The load-bearing change is that hue now
  encodes epistemic status only (cited, not explained, needs review, error) and
  direction of travel is carried by a glyph, an explicit sign and a word, which
  kills A-01 at the root rather than swapping two colours. Two claims from the
  plan were verified by measurement rather than assertion: all 26 declared token
  pairs clear their WCAG floor in both themes (the figures the plan predicted,
  including the 7.77:1 yellow tint and the 19.59:1 border, reproduce exactly),
  and in headless Chromium at a true 375px viewport the memo shows zero phantom
  horizontal scroll, while removing `contain: paint` reproduces the defect at
  248px. **The running app was checked in a browser as well**, which earlier
  sessions assumed was impossible here (the proxy blocks the live deploy, not
  localhost, so `streamlit run` plus Playwright works; recipe in `REFERENCE.md`).
  At 375, 768 and 1440: zero phantom scroll, zero canvas grids, green CTA at
  44px, captions at 7.07:1, no tap target under 44px. That pass caught three
  defects no unit test could, all fixed. Tests went 44 to 144. Nothing in the
  pipeline, matching, diff or explanation layer was touched.

- H18 (2026-07-31): Front-end audit received, branding decided, design-system
  work planned. Saved the external UI/UX/accessibility audit verbatim
  (`docs/audit/`), which measured **12 defects** in the live app (5 critical) by
  reading the real DOM: a footprint *decrease* painted red beside a green panel
  saying the same thing positively, the primary CTA at 3.30:1, every caption at
  3.69:1 (including the no-guess sentence), tables rendered to `<canvas>` so they
  cannot be read by assistive tech or printed, and the sidebar auto-collapsing
  below 768px taking every input and the only submit button with it. Independently
  recomputed every contrast ratio the audit reported for its own palette: all
  reproduce exactly. The audit proposed replacing the visual identity; the owner
  reviewed both directions as working mockups on the same real figures and **kept
  GOV.UK** (D19), so the two "Ledger" mockups are committed as the rejected
  alternative rather than deleted. The owner separately approved implementing the
  audit's fix for the three defects that sit underneath the look: a yellow
  needs-review tint (GOV.UK's four tints leave no colour for "held for review"),
  hue-encodes-epistemic-status with direction carried by glyph and word, and a
  `--border-control` split because `#b1b4b6` is 2.08:1 and fails 1.4.11. Two
  findings the audit could not have made, both now in the plan: that same
  `--border` failure lives in our own approved mockup, and a table wider than its
  `overflow-x:auto` container still gives the *page* a phantom horizontal scroll
  (480px of blank space at 375px) unless the container carries `contain:paint`.
  **Docs and mockups only, no pipeline or app code touched**; 44 tests green.
  Next: implement `docs/PLAN_design_system.md`, starting with the token layer.

- H20 (2026-07-31): Design session for the CITED half of VISION move #3, planned
  in `docs/PLAN_cited_memo.md`. Scope shrank on contact with D20: the dated,
  printable memo shipped in the export pack, so only the citations are left. The
  gap, stated precisely: `_explanations_html` prints a green "Cited" tag whenever
  the reason is not the verbatim NO_REASON sentence, but never prints what the
  reason was grounded in, so the memo asserts groundedness without evidence and
  the reader cannot tell a correct grounding from a wrong one. That matters
  because D11 exists to stop wrong groundings and its gold set proves they were
  possible. Underneath, most of the provenance is not in the data: the loader
  records the sheet but not the source file or row, `retrieve_passage` returns the
  matched note and `explain._finalize` drops it, `load_change_chunks` never records
  whether the PDF or the "What's new" sheet won, and no publication date is parsed
  anywhere. Decided: write into D20's memo rather than build a second document,
  change what is RETURNED and never what is CHOSEN so D11 stays locked, and print
  a missing publication date as not stated rather than inferring it. Design only,
  no code changed.

- H21 (2026-07-31): BUILT the citations (D21), so the memo now shows its work.
  Validated the risky step first: the loader records `source_file`,
  `source_sheet`, `source_row`, and 240 of 240 randomly sampled rows across both
  real workbooks were checked against the actual cells with openpyxl, so the row
  numbers survive the super-header expansion and the forward-fill. `diff.py`
  carries provenance through the join (new workbook where the factor still
  exists, old one where it was removed); `changes_pdf` tags each chunk with its
  document and gains `retrieve_citation`, which shares `_best_chunk` with
  `retrieve_passage` so the quote a reader checks is always the passage the
  explanation was built from; `export.py` renders the quote, its section heading,
  the source document, and the factor's workbook/sheet/row under the "Cited" tag.
  D11 untouched: the retrieval gate still reports 0 wrong hits. The D12 golden
  vector failed as predicted and its fixture now PINS the provenance, with every
  expected row number verified against the fixture's cells rather than copied from
  the loader. 149 tests (was 144), both gates clean, `scripts/check_citations.py`
  prints the evidence on real data, and the memo was rendered in headless Chromium
  to confirm the citation block appears and survives print media. Known wrinkle
  logged, not hidden: in offline mode the reason already embeds the note, so it
  reads twice. Shipped as PR #22, squash-merged `12e27f1`.
