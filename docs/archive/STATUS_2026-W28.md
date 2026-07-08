# Status handoffs archive: 2026-W28

Rotated out of `STATUS.md` as newer handoffs arrived. Append-only history.

- H8 (2026-07-07): Added the dependency-audit gate (DECISIONS D13). CI installs
  `pip-audit` and runs `scripts/audit_deps.py`, which audits the requirements'
  transitive closure against known-CVE feeds and fails on any advisory. Kept it
  CI-only (not pytest) because it is online and time-varying, unlike the
  deterministic offline gates; pip-audit stays out of requirements.txt to avoid
  bloating runtime deps. Currently clean. 26 tests green; three CI gates.
