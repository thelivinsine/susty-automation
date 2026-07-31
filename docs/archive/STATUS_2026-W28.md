
- H15 (2026-07-09): Merged the hosting/access layer to `main` (PR #15, `31da74b`).
  It collided with the real-data ingest work (PR #14) that landed first, so the
  branch was rebased onto the new `main` and the overlap resolved by keeping BOTH
  features: `app.py` runs ingest (upload + confirm-your-columns) AND the sign-in
  gate in one path; `pipeline.py` keeps impact-ranking AND `force_offline` on both
  explain calls; docs renumbered (hosting decision is D17, its handoff H14). 44
  tests green after the merge, lint clean, app boots. Dev branch realigned to the
  merged `main`. Next open items unchanged: header-row tolerance in ingest, then
  VISION move #3 (a dated, cited, printable memo as the first-class output).
