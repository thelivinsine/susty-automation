
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

- H24 (2026-08-17): A front-end audit of the running app (real 2025/2026
  workbooks, measured in a browser) found the front door D23 built showed WHAT
  changed and never WHY, and took 15 to 44 measured seconds to paint on a cold
  visit. Both fixed (D24), plus three smaller P1 gaps the same audit measured.
  `pipeline.cited_reasons` grounds every flagged factor in the current filtered
  view in DEFRA's own words via the existing `retrieve_citation` (so D11's
  wrong-note guard covers this surface too), with no model call: 46 of 67 real
  flagged factors (69%) come back cited, the rest show the exact `NO_REASON`
  sentence. `pipeline.write_snapshot`/`load_snapshot` plus a committed,
  hash-verified `data/register_snapshot/` (built by the new
  `scripts/build_register_snapshot.py`) cut the cold parse from 43.8s (measured,
  same real workbooks) to 0.157s, a live parse only firing on an actual hash
  mismatch, itself now disk-cached so a redeploy only pays it once per container.
  `run_pipeline(comparison=...)` reuses section 1's parse on a Run click instead
  of repeating it, proven both by a sentinel-column test and by `run_demo.py`
  still completing end to end. The default (>500 row) grid gained readable
  column headers and a `status_label` ("New"/"Retired"/"Renamed") column,
  confirmed live via the grid's own column picker rather than assumed. 195 tests
  green (was 177), both CI gates clean, zero horizontal scroll at 375/768/1440.
  Not done, deliberately: AI-written prose on the front door (VISION.md's point
  is that this layer stays free and verbatim for everyone), and the P2/P3 items
  from the same audit (copy reframe from product to register, filter state in
  the URL, a release picker, scrolling to the result after a run). Shipped as
  [PR #29](https://github.com/thelivinsine/susty-automation/pull/29),
  squash-merged `e6e2b90`.

- H25 (2026-08-17): Owner reported a redacted `ImportError` on the live Cloud
  app (`from pipeline import (...)` at app.py:65). Investigated the codebase
  first, per systematic debugging: `pipeline.py` exports every name app.py
  imports, and the full chain (`loader`/`diff`/`relabel`/`matching`/
  `recompute`/`changes_pdf`/`explain`/`paths`) imported clean both in the
  existing environment and in a fresh venv built straight from
  `requirements.txt`, so nothing local reproduced it. Closed the one real gap
  found regardless: no `runtime.txt` existed, so Cloud picked its own default
  Python untested against this repo (local dev runs 3.14). Added `runtime.txt`
  pinning `python-3.14`, the version proven clean by that fresh-venv test and
  195 green tests, shipped as
  [PR #31](https://github.com/thelivinsine/susty-automation/pull/31),
  squash-merged `d9cb493`. That alone did not fix the live app: the owner's
  actual Cloud log (previously hidden by Streamlit's redaction) showed
  `ImportError: cannot import name 'cited_reasons' from 'pipeline'` repeating
  identically across five separate redeploys over ~26 minutes, even though the
  first of those pulls landed 2 seconds after the PR #29 merge that added
  `cited_reasons`. Fetched `src/pipeline.py` straight from
  `raw.githubusercontent.com/thelivinsine/susty-automation/main` to rule out a
  push/sync problem: the function was correctly there, byte-identical to the
  local repo, the whole time. Root cause: a Streamlit Community Cloud platform
  bug, not this codebase, an incremental hot-pull redeploy serving a stale
  cached module instead of a clean reload. Fix was a full **Reboot app** (not
  another push), which the owner ran; app confirmed working live. No code fix
  was needed for the actual bug. Documented the gotcha in `STATUS.md` and
  `docs/DEPLOY_GUIDE.md` so a future redacted-error report goes straight to
  "reboot, don't just redeploy" rather than repeating this investigation.

- H26 (2026-08-17): Picked up the audit's own P2 list (STATUS's own "next
  likely task" pointer, H24's note). Item 6, reframe the copy from product to
  register: the H1 read "Compare two DEFRA releases against your product" and
  its caption led with "Recompute your footprint," both product-first even
  though section 1 (the register, diffed and explained with no upload) is the
  actual front door and the whole point of `VISION.md`'s reframe. Changed the
  H1 to "What changed between two DEFRA releases, and why" and the caption to
  lead with the register explanation, naming the product recompute as the
  second act rather than the headline. `app.py`'s H1/caption block only, no
  pipeline change. 195 tests green (unchanged, nothing pinned this string),
  microcopy gate clean, checked live in a running Streamlit app against the
  real 2025/2026 workbooks rather than assumed from the diff. Shipped as
  [PR #33](https://github.com/thelivinsine/susty-automation/pull/33),
  squash-merged `aa0a601`.
