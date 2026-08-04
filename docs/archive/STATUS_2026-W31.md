

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
