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
- `STATUS_2026-W28.md`: status handoff H8. (H1–H7 predate this archive
  convention and live in git history and the prompt log.)
