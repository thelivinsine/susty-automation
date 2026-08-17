
- H22 (2026-08-04): REWORKED the interface (D22) on the owner's brief: make it
  look and behave like a senior product team shipped it, keep the palette. Built
  the direction as a preview first (`docs/mockups/v2_product_ui.html`, three
  screens plus a swatch sheet so "palette intact" is checkable by looking), then
  implemented it. `tokens.css` gained a surface system and a type scale and no new
  hue; `components.css` was rewritten around cards, a shell and real states;
  `components.py` gained masthead, subnav, meter, fact_bar, step, file_chip,
  explanation_head, source_quote and checklist, and `verdict_card` learned the
  two-figure layout; `app.py` moved setup out of the sidebar into three numbered
  steps. Every D20 rule still holds and is still enforced. 151 tests green (the
  one changed assertion was a test pinning the literal "1 row(s)", now written as
  "1 row" by `ui.format.plural`). Checked in a real browser at 375, 768 and
  1440px: zero horizontal scroll, report renders end to end on the real 2025 and
  2026 workbooks. Not done, and deliberately: A-07 is still open (Streamlit's
  file input still has no programmatic accessible name), and the app remains
  light-only because Streamlit's own chrome is pinned light in config.toml.
  Shipped as PR #24, squash-merged `e21222b`.
