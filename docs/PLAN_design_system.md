# Plan: design system, handbook UI, and export pack

Status: **approved, not yet implemented.** Written 2026-07-31.
Source document: `docs/audit/2026-07-31_frontend_ux_audit.html`.

## Why this work

A front-end, UI/UX, accessibility and branding audit was run against the live app
at <https://efdiff.streamlit.app/> by inspecting the real DOM and computed styles
(not from screenshots). It found **12 measured defects**, five of them critical.
Its central charge is that the interface contradicts the product's own promise:

- The engine refuses to guess. The interface guesses on its behalf: it paints a
  **favourable** result red (`#BD4043` on a red wash) three centimetres from a
  green panel reporting the same fact positively.
- The "we never invent a reason" sentence, which is the whole credibility of the
  tool, renders at **3.69:1**, below the AA floor. The discipline that justifies
  the price is the least legible text on the page.
- The three data tables are painted to `<canvas>`, so they cannot be read by a
  screen reader, selected, searched, or **printed**. For a tool whose output goes
  into an assurance folder, that is a category error.
- The primary action is Streamlit's default red at **3.30:1**, and below 768px
  the sidebar auto-collapses and takes every input and the only submit button
  with it, leaving the app apparently read-only.

Today `.streamlit/config.toml` does not exist and `app.py` injects no CSS at all,
so every visual decision in the product is a framework default. Closing these
defects and adding an owned, token-driven design layer is what turns the app from
a working analysis script into something a consultant can put their name on,
which is what `docs/VISION.md` move #3 already asks for.

## Decisions taken by the owner

1. **Visual identity: keep GOV.UK.** `docs/mockups/govuk_report_view.html` stays
   the approved direction. The audit's alternative palette is **not** implemented
   in the app, but **is** to be rendered as mockups so the choice can be revisited
   against real numbers rather than against a description.
2. **Scope: the 12 defects + design system + IA reorder + the multi-format export
   pack.** Deferred: run history, year-over-year mapping memory, the keyboard
   review queue, the `/factors` library.
3. **Fonts:** the GOV.UK choice settles this. Arial and the system stack, so
   **zero external font requests**, consistent with the existing mockup.

## One constraint conflict, and how it is resolved

The audit asks for a **PDF** in the export pack. `pdfplumber` only *reads* PDFs,
and CLAUDE.md forbids adding anything heavyweight, which rules out reportlab and
weasyprint. `docs/VISION.md` already settled this: ship a **print-ready HTML memo**
with a provenance header that the user prints to PDF from the browser ("HTML-to-PDF
respects the no-heavy-deps rule"). That is what will be built. A true generated PDF
binary would be a new dependency decision, to be taken separately.

## The two brandings, compared

Ratios computed with the WCAG 2.1 relative-luminance formula, not quoted. **Every
figure the audit reported for its own palette reproduces exactly**, which is a
reasonable credibility check on the rest of the document.

| | GOV.UK mockup (chosen) | Audit "Ledger" |
|---|---|---|
| Canvas | `#ffffff` clinical white | `#FBFAF7` warm paper |
| Body text | `#0b0c0c` **19.59:1** | `#14181C` **17.09:1** |
| Muted text | `#505a5f` **7.07:1** | `#5C646E` **5.74:1** |
| Primary action | green `#00703c`, white on it **6.21:1** | verdigris `#0B5750`, white on it **8.42:1** |
| Caution state | red `#d4351c` 4.86:1 | ochre `#8A5A05` 5.67:1 |
| Interactive border | `#b1b4b6` **2.08:1, fails 1.4.11** | `#8F8A80` **3.29:1, passes** |
| Focus | yellow `#ffdd00` + black underline, very strong | 2px brand outline, conventional |
| Type | Arial, no external requests | three families, needs a CDN or vendored files |
| Numerics | `tabular-nums`, no distinct face | dedicated mono face for every figure |
| Dark theme | present, all ratios pass | present, all ratios pass |

**Where GOV.UK is genuinely stronger:** the focus state is the best in either
system; it ships zero external requests, which matters for a tool whose users
handle confidential client data; body contrast is higher; and it carries an
implicit institutional association with the DEFRA source material.

**Where the audit's palette is stronger, and it is not only taste:**

1. **It has a colour for "we do not know."** GOV.UK's four tints are blue, green,
   red and grey. The three-state model (cited / not explained / needs review) needs
   a neutral that reads as honest rather than as either reassuring or alarming. In
   the GOV.UK set that state has to borrow grey, which also means "inactive".
2. **It avoids red entirely for results.** Red in this domain reads as "error",
   and a needs-review flag is the tool working correctly, not failing.
3. **A dedicated monospace face for figures** makes a number visually distinct
   from prose, which is the distinction this audience cares about.

**A defect in the chosen direction that the audit did not catch** (it inspected
the live app, not the mockup): the GOV.UK mockup's `--border #b1b4b6` is **2.08:1**
on white, which **fails WCAG 1.4.11** for any interactive boundary. Same class of
failure as A-08. Fix, staying authentically GOV.UK: keep `#b1b4b6` for decorative
table rules, and use `#0b0c0c` for interactive boundaries, which is what GOV.UK
Frontend itself does for input borders. The dark theme's `#5c5f61` at 3.04:1
scrapes through and is left alone.

**Net:** GOV.UK is a sound choice and needs three things grafted on from the audit:
a **yellow needs-review tint** (`#fff7bf` on `#594d00`, **7.77:1**), the
**hue-encodes-confidence rule**, and the **interactive border fix**.

## The defects to close

Critical: A-01 delta chip inverts meaning · A-02 CTA 3.30:1 · A-03 captions 3.69:1 ·
A-04 canvas data grids · A-05 unnamed disclosures.
High: A-06 grid overflow (1236px in 714px) · A-07 unlabelled file input ·
A-08 secondary border 1.45:1 · A-09 CTA clipped and sidebar auto-hides below 768px.
Medium: A-10 22px toolbar targets · A-11 three message types share one green style ·
A-12 heading order runs H2, H1, H3.

## The design system

### Tokens

The GOV.UK mockup already carries a complete dual-theme token set, currently
trapped in a static file the app cannot use. Lift it into `src/ui/tokens.css` as
the single source of truth, then extend it.

Keep as-is (all AA-clean on white): `--black #0b0c0c`, `--ground #ffffff`,
`--grey-1 #f3f2f1`, `--grey-2 #e7e6e5`, `--border #b1b4b6`, `--secondary #505a5f`,
`--blue #1d70b8`, `--blue-dark #003078`, `--green #00703c`, `--red #d4351c`,
`--focus #ffdd00`, plus the `prefers-color-scheme: dark` block and the
`:root[data-theme]` overrides.

Add, because GOV.UK's four tag tints do not cover the states the audit needs:

| Token | Light | Purpose |
|---|---|---|
| `--tag-yellow-bg` / `-tx` | `#fff7bf` / `#594d00` | **needs review** (the one loud state) |
| `--tag-grey-bg` / `-tx` | `#eeefef` / `#383f43` | **not explained** (notes are silent) |
| `--tag-green-bg` / `-tx` | `#cce2d8` / `#005a30` | **cited** (verbatim DEFRA reason) |
| `--border-interactive` | `#0b0c0c` | fixes the 2.08:1 boundary failure |
| spacing scale | `4 8 12 16 24 32 48 64 96 128` | one 8px rhythm, no ad-hoc margins |
| `--measure` | `74ch` | prose cap; tables may break it, nothing else may |
| `--rail` / `--pad-card` | `280px` / `28px` | constant card padding, so density comes from type size |

Red is **retired from result semantics** and reserved for genuine errors.

### The load-bearing rule

> **Hue encodes epistemic status. Direction is carried by glyph, sign and word.**

A footprint that rises is not "bad", it may be the correct, well-cited answer. A
footprint that falls on a low-confidence match is the genuinely alarming case, and
today it is painted the calmest colour on the page. This kills A-01 at the root
instead of swapping two colours. It also means deleting the mockup's own
`.d-up{color:var(--red)}` and `.d-down{color:var(--green)}`, which encode exactly
the convention the audit condemns.

### Type

18px body (the mockup's existing choice), 16px small, 13px table, Arial throughout,
`font-variant-numeric: tabular-nums` on **every** numeric cell without exception,
right-aligned numerics, and significant-figure formatting by magnitude so
`1199.7254` and `0.0634` stop sitting in the same column. Full precision moves to
the drawer and the export.

## Files

| Path | Change | What it does |
|---|---|---|
| `.streamlit/config.toml` | new | `[theme]` GOV.UK palette, so the red CTA never flashes before CSS loads |
| `src/ui/tokens.css` | new | The token layer, both themes |
| `src/ui/components.css` | new | Component and state classes, Streamlit `data-testid` overrides, print rules |
| `src/ui/__init__.py` | new | `inject_styles()`, once per session |
| `src/ui/components.py` | new | `render_table`, `verdict_card`, `stat_row`, `badge`, `alert`, `disclosure`, `definition` |
| `src/ui/format.py` | new | `sig_figs`, `signed_pct`, `kg`, `human_column` |
| `src/export.py` | new | `run_identity`, `to_xlsx`, `to_json`, `to_print_html`, `completeness_checklist` |
| `app.py` | rewrite of the view layer | IA reorder, semantic tables, named disclosures, heading spine, action bar |
| `src/report.py` | extend | Reuse for the Markdown artifact; add the provenance header |
| `scripts/lint_microcopy.py` | extend | Scan `.css` and `.html`; allowlist `docs/audit/` |
| `tests/test_design_system.py` | new | Contrast, escaping, table semantics |
| `tests/test_export_pack.py` | new | Four artifacts, one shared run id |
| `docs/mockups/ledger_*.html` | new | Two mockups of the audit's recommended branding |

`app.py` keeps calling `run_pipeline` exactly as it does now. **No pipeline,
matching, diff or explanation logic changes in this pass**, so the analytical test
suite is untouched by design.

## Implementation notes

**1. Token and component layer.** `inject_styles()` reads both CSS files and emits
them once via `st.markdown(unsafe_allow_html=True)`, guarded by a `session_state`
flag. The overrides that close defects:

```css
[data-testid="stCaptionContainer"]{ opacity:1; color:var(--secondary) }          /* A-03 */
[data-testid="stBaseButton-primary"]{ background:var(--green); min-height:44px } /* A-02 */
[data-testid="stDownloadButton"] button{ border:1px solid var(--border-interactive) } /* A-08 */
[data-testid="stElementToolbarButton"]{ min-width:44px; min-height:44px }        /* A-10 */
:focus-visible{ outline:3px solid var(--focus); box-shadow:0 4px var(--black) }
```

These `data-testid` selectors are **version-fragile**: they are Streamlit
internals, not a public API. Each gets a comment naming the defect it closes and
the Streamlit version it was verified against, so a future upgrade that breaks
them is diagnosable rather than mysterious.

**2. Semantic tables (A-04, A-06).** `render_table(df, columns, caption,
numeric_cols)` emits a real `<table>` with `<caption>`, `scope="col"` headers and
right-aligned tabular numerics, inside an `overflow-x:auto` container so the
contributors grid stops clipping.

*Security, and it is not optional.* BOM line items come from a user-uploaded file
and this renders through `unsafe_allow_html`. Every cell goes through
`html.escape(str(v), quote=True)` before interpolation, with a test asserting that
a `<script>` in a line item comes out inert. Above roughly 500 rows, keep
`st.dataframe` for interactivity and offer the semantic table behind an
"accessible, printable" toggle; below it, the semantic table is the default.

**3. Information architecture (F-04, A-12).** Reorder to **Result, Confidence,
Movers, Explanations, Export**, so the trust gate arrives before the conclusion
rather than two sections after it. The Result section is one verdict card: new
footprint at display size, the change as the second-largest element with an
explicit word ("down 1.68%, 0.04 kg lighter"), no hue carrying direction. Coverage
becomes a **control**: clicking 85.7% opens the 14.3% that did not match, each with
its best candidate and score. `below_threshold` renders as a sentence: "Match score
49.3, below the 60 confidence threshold, so nothing was assumed." Heading spine
becomes H1, then one H2 per section, then H3 within, closing A-12. Every expander
gets a named summary carrying its count, closing A-05.

**4. The sub-768px control loss (A-09, F-02).** Separate setup from commit:
parameters stay in the rail, and the **Run control moves into the main canvas** as
a persistent action bar carrying run state (Ready, Running, Complete). This is the
one fix that survives the sidebar auto-collapsing, because the action is no longer
inside the thing that disappears. `initial_sidebar_state="expanded"` alone does not
fix it, since Streamlit still collapses on narrow viewports.

**5. Export pack (P9, P10).** `run_identity()` builds an in-memory dict per run:
client, product, both version labels, factor counts, a mapping hash, coverage,
unresolved review count, operator, UTC timestamp, and a short run id hashed from
the inputs. **Nothing is persisted**, so the no-database rule holds. Four artifacts
from one action, all stamped with the same run id: XLSX (movers, full mapping,
review log, method sheet) via pandas and openpyxl, JSON via stdlib, Markdown via
the existing `build_markdown_report`, and a print-ready HTML memo with `@media
print` rules, expanded disclosures and repeated table headers. A pre-export
checklist lists what is unresolved, and anything unchecked is written into the
export's front matter. The consultant can always ship; they can never ship
silently.

**6. Mockups of the audit's recommended branding.** Two self-contained files, no
external requests, rendered from the real figures in
`docs/mockups/report_data_snapshot.json` so they are directly comparable to the
GOV.UK mockup:

- `docs/mockups/ledger_report_view.html`: the same report, same numbers, in the
  audit's palette, light and dark. A true A/B against the GOV.UK view.
- `docs/mockups/ledger_result_canvas.html`: the audit's *proposed structure*
  rather than the current one (verdict card, coverage-as-control, semantic movers
  table with per-row confidence badges, evidence drawer, action bar). Doubles as
  the design-system reference sheet, showing every token, badge, alert role and
  component state in both themes.

`docs/mockups/README.md` gains a section explaining that these render the audit's
recommendation, that GOV.UK remains the implemented direction, and that they exist
to make that choice reversible on evidence. It also carries the measured
comparison table above, including the `--border` failure.

**7. Microcopy gate.** `scripts/lint_microcopy.py` scans only `.py` and `.md`, so
new `.css` and `.html` files carrying visible copy would slip the no-em-dash rule.
Extend `iter_target_files` to include them, treating them like Markdown. Add
`docs/audit/` to `ALLOWLIST_PREFIXES`: the audit is a verbatim third-party document
full of em dashes, exactly like `docs/reference/`. The new mockups are our own copy
and **are** linted.

## Verification

Deterministic, no browser:

1. `pytest tests/test_design_system.py -q`
   - **Contrast:** parse every token pair out of `tokens.css`, compute WCAG 2.1
     relative luminance in pure Python, assert text pairs >= 4.5:1 and UI
     boundaries >= 3:1, in **both** themes. This is the test that would have caught
     A-03 and A-08 before they shipped.
   - **Escaping:** a line item of `<script>alert(1)</script>` renders inert.
   - **Semantics:** emitted tables contain `<caption>` and `scope="col"`.
   - **Colour independence:** every state exposes a glyph and a text label, not
     just a class, so a greyscale render still separates them.
2. `pytest tests/test_export_pack.py -q`: four artifacts, all carrying the same run
   id, with unresolved review items present in the front matter.
3. `python scripts/lint_microcopy.py`: clean across the new `.css` and `.html`.
4. `pytest -q`: the existing 44 tests still pass, untouched.
5. `python run_demo.py`: end-to-end, still prints 2.344 to 2.305.

Visual, needs a browser:

6. `streamlit run app.py`, checked at 375, 768, 1024 and 1440: no horizontal scroll
   below 640, the Run control reachable at every width, and print preview producing
   a complete expanded document with visible tables.
7. Both new mockups opened directly in a browser, light and dark toggled.

The sandbox proxy denies CONNECT to `*.streamlit.app`, so confirmation on the live
deploy stays the owner's, as it was for the deploy itself.

## Housekeeping when this ships

Update `docs/STATUS.md` and `docs/PROMPT_LOG.md`, record the design-system decision
and the PDF-to-print-HTML resolution in `docs/DECISIONS.md`, and refresh the
"GOV.UK theming" backlog line in `docs/REFERENCE.md`, which this pass delivers.
