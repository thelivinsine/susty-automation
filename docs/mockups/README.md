# Design mockups

Static, self-contained HTML mockups of the EF Version Explainer report, kept as a
visual reference. These are NOT part of the running app (the live product is the
Streamlit app in `app.py`); they exist to pin a look before theming the real UI.

## `govuk_report_view.html`

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

## `report_data_snapshot.json`

The real numbers the mockup was rendered from: a snapshot of the pipeline output
on the owner's real DEFRA 2025 and 2026 full-set workbooks (footprint, coverage,
diff stats, the flagged explanation, a sample of renamed-and-moved factors, and
the needs-review line). The figures in the HTML are hardcoded from this snapshot,
so they will drift if the data or pipeline changes; regenerate both together when
using this as a live reference.

## Next step this reference is for

Theming the actual Streamlit app (`app.py`) to this look via a
`.streamlit/config.toml` palette plus targeted CSS, so the real product matches
the mockup. See STATUS "Known gaps / next candidates".
