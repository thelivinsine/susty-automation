# Archive index

Append-only history, rotated by ISO week. Loading one week stays cheap because
each week file is small. Never rewrite entries when moving them here.

## What rotates here
- Status handoffs older than the two most recent (from `STATUS.md`).
- Prompt-log entries once the live `PROMPT_LOG.md` passes ~1,200 lines (keep
  roughly the current session plus the last ~5 sessions live).

File naming, one per ISO week, matching each moved entry's own date:
`STATUS_YYYY-Www.md` and `PROMPT_LOG_YYYY-Www.md`.

## Weeks archived
- `STATUS_2026-W28.md`: status handoffs H8, then H11 to H14 rotated out on
  2026-07-31. (H1–H7 predate this archive convention and live in git history and
  the prompt log.)
- `STATUS_2026-W31.md`: status handoff H16, rotated out on 2026-07-31 when H18
  landed and pushed it past the two-most-recent rule.
  Then H19 and H18 on 2026-07-31, and H20 on 2026-08-04 when H22 landed.
  Then H21 on 2026-08-17 when H24 landed (both H21 and H22 fell out of the
  two-most-recent window at once).
- `STATUS_2026-W32.md`: status handoff H22, rotated out on 2026-08-17 when H24
  landed.
- `STATUS_2026-W34.md`: status handoff H23, rotated out on 2026-08-17 when H25
  landed. Then H24 on 2026-08-17 when H26 landed.
