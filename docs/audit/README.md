# Audits

Point-in-time audit records. External reviews are saved verbatim as received
(source material, not our own copy, so they keep house-style violations such as
em dashes); audits run in-session are our own copy and follow house style, but
are still kept as a record of what was found AT THE TIME rather than rewritten
as findings get fixed. Where a finding has since been actioned, a short status
note says so and points at the decision/status entry that did it, rather than
editing the finding itself away.

## `2026-08-17_frontend_gap_analysis.md`

An in-session front-end audit and gap analysis of the running app against
`CLAUDE.md`/`docs/VISION.md`'s stated goal, on the owner's real 2025/2026
workbooks, measured in a real browser at 375/738/1440px. Found the front door
D23 built showed WHAT changed and never WHY, and took 15 to 44 measured seconds
to paint. Sequenced P0 to P4. **P0 and P1 shipped the same day** (DECISIONS
D24, PR #29, squash-merged `e6e2b90`); P2 to P4 are still open and tracked in
`STATUS.md`.

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
