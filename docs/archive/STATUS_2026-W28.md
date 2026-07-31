# Status handoffs archive: 2026-W28

Rotated out of `STATUS.md` as newer handoffs arrived. Append-only history.

- H8 (2026-07-07): Added the dependency-audit gate (DECISIONS D13). CI installs
  `pip-audit` and runs `scripts/audit_deps.py`, which audits the requirements'
  transitive closure against known-CVE feeds and fails on any advisory. Kept it
  CI-only (not pytest) because it is online and time-varying, unlike the
  deterministic offline gates; pip-audit stays out of requirements.txt to avoid
  bloating runtime deps. Currently clean. 26 tests green; three CI gates.
- H14 (2026-07-09): Owner asked how to make the tool accessible to non-technical
  users, and whether it lives on GitHub Pages (it can't: Streamlit needs a server).
  Built the hosting/access layer (D17): open to everyone on the free offline
  explainer, paid AI behind Streamlit's built-in Google sign-in + an approved list
  in secrets, spending cap as backstop. New `src/auth.py`; `use_ai`/`force_offline`
  flag threaded app -> pipeline -> explain; `app.py` sign-in UI and free-vs-AI
  banners; `.streamlit/secrets.toml.example`; owner-facing `docs/DEPLOY_GUIDE.md`;
  requirements bumped (streamlit>=1.42, Authlib). +6 tests (44 green), lint clean.
  No sign-in configured => behaves exactly as before. Deploy to Streamlit Cloud is
  the owner's click-through (guide provided); no repo settings changed here.
- H13 (2026-07-08): Reframed the project goal around GENUINE USEFULNESS via a
  six-persona brainstorm (`docs/VISION.md`): primary audience is the UK
  solo/boutique DEFRA consultant, getting-hired is a side effect. Then shipped
  VISION move #2 (real-data ingest) in three steps: `src/ingest.py` (forgiving
  reader), a confirm-your-columns step in `app.py`, and impact-ranking of
  explanations by the user's own footprint. Suite 38 green; app boots clean.
  Next likely: the "find the header row" tolerance for files with a title above
  the headers, then VISION move #3 (a dated, cited, printable memo as the
  first-class output).
- H12 (2026-07-08): Grouped the renamed-and-moved output into rename families
  (D10 follow-up, D14). On real data the HGV rename spanned 420 material variants
  (DEFRA also reordered the sub-tables, so the greedy matcher scattered +-100%
  deltas); those now collapse to ~10 grounded family explanations with an honest
  value-movement range and a "mixed direction" flag, not 420 fabricated single-
  direction blocks (and ~10 API calls, not 420). New `relabel.group_relabels`;
  report/app/run_demo render families; +6 tests (32 green). Footprint math
  untouched (relabels stay review-only, D9).
- H11 (2026-07-08): Owner asked to commit the two source docs shared at project
  start and to make `main` the default branch (P17). Added the build playbook and
  the MVP spec PDF under `docs/reference/`, shipped via PR #10. Default-branch
  switch is a manual owner step (no repo-settings tool / no direct GitHub API here):
  GitHub repo Settings, Branches, set default to `main`. Docs/reference only, no
  code touched.
