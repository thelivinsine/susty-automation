
- H23 (2026-08-17): MADE THE COMPARISON THE FRONT DOOR (D23), on the owner's
  brief to check whether the interface really leads with an interactive EF
  version comparison. It did not: the app opened on a setup form, ran the whole
  pipeline on a sample product before anyone asked, had zero filter controls
  anywhere, and rendered only the handful of diff rows that touched a bill of
  materials. Split `compare_versions` out of `run_pipeline` (which now calls it,
  so there is one definition of the delta), added `diff.filter_changes` with its
  own suite (19 tests, runnable standalone), and built section 1: search, scope,
  status, minimum-movement slider, materiality toggle, live count, and a CSV of
  whatever view you have narrowed to. Removed the cold-load pipeline run. Real
  numbers on the real workbooks: 2,647 joined factors, 67 past threshold, 76
  genuinely new, 54 retired, 460 renamed. Checked in a real browser at 375, 768
  and 1440px: zero horizontal scroll at every width, and every filter carries a
  programmatic accessible name. **Found and fixed a serious pre-existing defect
  while checking it:** `inject_styles`'s session_state guard meant the design
  layer was emitted only on a session's first run, so Streamlit removed it on the
  next rerun and the page reverted to Streamlit defaults (captions measured back
  at the default ink instead of #505a5f) the instant a visitor touched anything.
  The guard is gone and a test now asserts exactly one style block AFTER an
  interaction. Also fixed `run_demo.py` writing its report without an explicit
  encoding, which crashed the demo's last stage on Windows cp1252 on the owner's
  own machine. 177 tests green, both CI gates clean. Not done, deliberately:
  filter state in the URL (`st.query_params`), which is the next candidate.
