# Design mockups

Static, self-contained HTML mockups of the EF Version Explainer report, kept as a
visual reference. These are NOT part of the running app (the live product is the
Streamlit app in `app.py`); they exist to pin a look before theming the real UI.

## `govuk_report_view.html`

The mockup that pinned the palette (D19) and the one the v1 design layer was
ported from. Superseded as a layout reference by `v2_product_ui.html` (D22); its
colours are still the source of truth and are unchanged.

The one-page version-delta report in a **GOV.UK Design System** visual idiom,
evoked for familiarity, not a literal copy: black masthead with an environment
green keyline, a phase banner, the green confirmation panel for the headline
result, GOV.UK tag pills, big-number stats, a bordered summary/key-value
explanation block, GOV.UK-style tables, the warning-text component, the GOV.UK
palette (blue `#1d70b8`, green `#00703c`, red `#d4351c`, yellow `#ffdd00` focus),
and Arial (GOV.UK's own GDS Transport fallback). Light and dark themes.

Independent work: not affiliated with, or endorsed by, DEFRA, DESNZ, or GOV.UK.
The style is inspired by the GOV.UK Design System for familiarity only.

Open it directly in a browser (no server, no build): it is a single file with all
CSS inline and no external requests.

## `v2_product_ui.html`

The **current** direction, and the one the live app now implements (DECISIONS
**D22**). Same palette as `govuk_report_view.html`, every hex still from
`src/ui/tokens.css`; what changes is the object it makes. Three screens behind a
switcher at the top:

- **Set up**: the three-step flow (versions, inventory, confirm your columns)
  with a preview of the uploaded file as read, and a sticky action bar.
- **Report**: the whole delta report under a masthead and a sticky section nav.
  The verdict is two figures and a delta chip over a strip of qualifying facts;
  coverage is a meter against the 95% bar; deltas carry magnitude bars;
  explanations lead with the status tag and the impact on the reader's own
  footprint, with the DEFRA quote set as a source block.
- **System**: the swatch sheet (so "the palette is unchanged" can be checked by
  looking), the status tags, the controls, the four message roles, the empty and
  loading states, and a note on what changed and why.

Self-contained, no external requests, light and dark. Open it directly in a
browser. The figures are the same real 2025 to 2026 snapshot the other mockups
use, so they drift with the data in the same way.

Where the shipped app differs, and why: the mockup's setup screen has a sticky
bottom action bar and a "use the sample product" button, and its downloads are
file cards. The app uses a plain primary button with a line of helper text and
Streamlit's own download buttons, because those are widgets Streamlit renders
and restyling them further would mean fighting internals for no gain in
comprehension. Everything else on these screens is what the app does.

## `report_data_snapshot.json`

The real numbers the mockup was rendered from: a snapshot of the pipeline output
on the owner's real DEFRA 2025 and 2026 full-set workbooks (footprint, coverage,
diff stats, the flagged explanation, a sample of renamed-and-moved factors, and
the needs-review line). The figures in the HTML are hardcoded from this snapshot,
so they will drift if the data or pipeline changes; regenerate both together when
using this as a live reference.

## `ledger_report_view.html` and `ledger_result_canvas.html`

The **alternative** direction, proposed by the July 2026 front-end audit
(`docs/audit/2026-07-31_frontend_ux_audit.html`): warm paper, deep verdigris,
ochre reserved for review, editorial serif display, monospace for every figure.
Called "Audit Ledger" in that document.

These were built so the identity decision could be made by looking rather than by
reading a description. **The decision is settled: GOV.UK won** (owner, 2026-07-31,
recorded as DECISIONS **D19**). These two files are the **rejected alternative**,
kept so a future revisit starts from artefacts rather than from an argument. They
are not built, not themed, and nothing in the app reads from them.

- **`ledger_report_view.html`** is mockup A: the *same* report, the *same*
  numbers and the *same* copy as `govuk_report_view.html`, so the only variable
  is the visual system. Open the two side by side.
- **`ledger_result_canvas.html`** is mockup B: the *proposed structure* rather
  than the current one (Result, Confidence, Movers, Explanations, Review,
  Export), with a persistent action bar, a section rail, coverage as a control,
  an evidence drawer, and a pre-export checklist. It doubles as the component
  reference sheet: every token, badge, alert role, button, empty state and stale
  state, in both themes.

Both are self-contained single files with no external requests. The three
typefaces the audit specifies (Newsreader, Public Sans, JetBrains Mono) are
named first in each font stack and will be used if installed locally, otherwise
the files fall back to system faces. Shipping the real faces would mean
vendoring woff2 files or adding a CDN, which is a separate decision.

### The rule these mockups demonstrate

> Hue encodes **epistemic status**, how far a number can be trusted.
> Direction (up or down) is carried by glyph, sign and word.

This is the audit's answer to its own most severe finding: the live app paints a
footprint *decrease* red, because the framework assumes down is bad. Compare the
"Renamed and moved" rows in the two report mockups. The GOV.UK version colours a
fall green and a rise red; the Ledger version spends colour only on whether the
change is cited, unexplained, or held for review.

### Measured comparison

Ratios computed with the WCAG 2.1 relative-luminance formula. Every figure the
audit reported for its own palette reproduces exactly.

| | GOV.UK (chosen) | Audit "Ledger" |
|---|---|---|
| Canvas | `#ffffff` | `#FBFAF7` warm paper |
| Body text | `#0b0c0c` **19.59:1** | `#14181C` **17.09:1** |
| Muted text | `#505a5f` **7.07:1** | `#5C646E` **5.74:1** |
| Primary action | `#00703c`, white on it **6.21:1** | `#0B5750`, white on it **8.42:1** |
| Caution | red `#d4351c` 4.86:1 | ochre `#8A5A05` 5.67:1 |
| Interactive border | `#b1b4b6` **2.08:1, fails 1.4.11** | `#8F8A80` **3.29:1, passes** |
| Focus | yellow `#ffdd00` plus black underline | 2px brand outline |
| Type | Arial, zero external requests | three families, needs vendoring or a CDN |

**Where GOV.UK wins:** the focus state is the strongest in either system, it
makes no external requests (which matters for a tool handling confidential
client data), body contrast is higher, and it carries an institutional
association with the DEFRA source material.

**Where the Ledger palette wins, and it is not only taste:** it has a colour for
"we do not know" (GOV.UK's four tints are blue, green, red and grey, so that
state has to borrow grey, which also means "inactive"); it keeps red for genuine
errors rather than spending it on a review flag; and a dedicated monospace face
makes a figure visually distinct from prose.

**A defect in the chosen direction, found while building these:**
`govuk_report_view.html` uses `--border #b1b4b6`, which is **2.08:1** on white
and fails WCAG 1.4.11 for any interactive boundary. The audit could not catch it
because it inspected the live app, not this file. Fix, staying authentic: keep
`#b1b4b6` for decorative table rules, use `#0b0c0c` for interactive boundaries,
which is what GOV.UK Frontend does for input borders.

### Verified, not eyeballed

Both Ledger files were checked in headless Chromium at 375, 414, 640, 768, 1024
and 1440px:

- **58 contrast pairs** across both themes, all passing (4.5:1 for text, 3:1 for
  UI boundaries).
- **Zero horizontal page scroll** at every width. Getting there caught a real
  bug worth knowing about: a table wider than its `overflow-x:auto` container
  still contributes its width to the initial containing block, so the page gains
  a phantom horizontal scroll into blank space even though the table itself
  scrolls correctly. `contain: paint` on the scroll container is the fix, and it
  is commented as load-bearing in both files. The audit's own report avoids this
  only incidentally, because its entrance animation creates a containing block.
- **No tap target under 44px**, semantic tables with `<caption>`, `scope="col"`
  and `scope="row"`, keyboard-reachable scroll regions, and no em dashes.

## What these are for now

The theming step is done: `src/ui/` is the live design layer and
`.streamlit/config.toml` matches it (D20), and the product-UI rework on top of it
shipped as D22. These files stay as the visual record: `v2_product_ui.html` is
the current reference, `govuk_report_view.html` is where the palette came from,
and the two Ledger files are the rejected alternative.
