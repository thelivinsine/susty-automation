# Audits

External review documents, saved verbatim as received. These are source material,
not our own copy, so they are kept exactly as delivered (including house-style
violations such as em dashes).

## `2026-07-31_frontend_ux_audit.html`

A front-end, UI/UX, accessibility and branding audit of the live app at
<https://efdiff.streamlit.app/>, dated 31 July 2026. Method: live DOM and
computed-style inspection at a 756x402 CSS px viewport, with contrast ratios
calculated per the WCAG 2.1 relative-luminance formula rather than estimated from
screenshots.

It reports **12 measured defects** (5 critical, 4 high, 3 medium), six structural
gaps in the user flow, a proposed design system, twelve "handbook" patterns, and a
sequenced backlog from P0 to P3.

Two things worth knowing when reading it:

- **Its numbers check out.** Every contrast ratio it reports for its own proposed
  palette reproduces exactly under an independent WCAG 2.1 calculation.
- **It proposes a different visual identity** ("Audit Ledger": warm paper, deep
  verdigris, ochre) from the GOV.UK direction pinned in `docs/mockups/`. The owner
  decided to keep GOV.UK. The audit's palette is being rendered as mockups instead,
  so that decision can be revisited on evidence.

Self-marked `[NEEDS VERIFICATION]` in the document: rendering at 1280px and above,
real keyboard and screen-reader testing, bundle size, and which hosting-platform
chrome can be suppressed. Treat those as open, not as findings.

The response to it is planned in `docs/PLAN_design_system.md`.

Open the file directly in a browser: it is self-contained apart from a webfont
request.
