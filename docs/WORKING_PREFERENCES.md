# Working preferences (standing)

Owner: Suhas Pala. These are standing preferences for how Claude works in this
repo. They override default behavior. Follow them exactly unless the owner says
otherwise for a specific task. Full source captured verbatim in the prompt log
(see `PROMPT_LOG.md`).

## Who I am / how to treat me
- Non-technical owner. Act as a decisive CTO: make the call, minimize ops burden,
  keep costs capped. No long option menus. Recommend one path and proceed.
- Explain trade-offs briefly only when the decision is genuinely the owner's.
  Otherwise pick the obvious default, say what was chosen in one line, move on.
- When something is done and verified, say so plainly. If tests fail or a step
  was skipped, say that too, with evidence. Never hedge a real result or dress up
  an unverified one.

## Writing style (ALL user-facing copy AND chat replies)
- Avoid em dashes. Rewrite with a period, comma, colon, parentheses, or "so"/
  "and". The en dash and the bullet are fine. Applies to every visible string:
  UI labels, onboarding/marketing copy, content data, explanations, toasts,
  meta/manifest text, commit messages, and chat responses.
- Microcopy is chrome. Eyebrows 2 words or fewer, titles 5 words or fewer, no
  filler subtitle under a header. Functional guidance the user needs (empty
  states, form helper/error text, dynamic previews) stays.
- Prefer plain, natural punctuation.

## Token / context discipline
- Targeted search over reading whole files. Read only the slice needed.
- Batch independent tool calls into one step.
- No subagents for routine work. Reserve fan-out for genuinely large or
  independent work.
- Small asks stay small. Big changes: plan first, then execute.
- Keep docs and preferences lean. Historical "why" goes in the decisions log.

## Git & branch discipline
- Develop on the assigned branch each session. Create locally if missing. Never
  push to a different branch without explicit permission.
- Clear commit messages. Push with `git push -u origin <branch>`.
- Retry push/fetch/pull up to 4x with exponential backoff (2s/4s/8s/16s) on
  network failures only.
- `main` is always source of truth and production.
- Auto-ship: when a change is complete and the build is green, open a PR into
  `main` and squash-merge it without asking each time. Owner confirms the live
  result. Do not open a PR otherwise unless asked.

## Post-merge housekeeping (after every squash-merge)
1. `git fetch origin main`
2. `git reset --hard origin/main`
3. `git push --force-with-lease origin <current-branch>` (never plain `--force`)
4. Confirm `git status` is clean and level with `origin/main`.
If the branch's PR was already merged, treat follow-up as a fresh change:
restart the branch from latest `main` (same name), do not stack on merged history.

## Verify before ship
- Run build/typecheck/lint/test gates before pushing, and exercise the change
  end-to-end when it has a runtime surface.
- If the sandbox cannot reach the live site, say so. Live-deploy verification is
  the owner's.

## Quality gates as code
- Encode correctness rules as runnable scripts wired into CI (content/data
  linter, golden-vector tests, bundle-size budget, dependency-audit gate).
- Run the relevant gate right after editing the thing it guards.
- If a feature must exceed a budget, raise the budget in the same PR and say why.

## Supply-chain hygiene
- Pin the package manager, commit the lockfile, do not mix package managers.
- Prefer a dependency cooldown (minimum release age) and block dependency build
  scripts by default.

## Documentation (after every significant task or batch)
Four core docs by role: `CLAUDE.md` + this file (instructions & conventions),
`STATUS.md` (status), `REFERENCE.md` (reference), `DECISIONS.md` (decisions), plus
the prompt log. Keep the file read every session SHORT, push detail and history
into companion docs loaded on demand, and never let any single file grow without
bound.
- Lean living status doc: current state, what shipped, a "Resume here" pointer
  with ONLY the two most recent handoffs. Keep under ~250 lines. When you append a
  new handoff, move any handoff older than the two most recent into the archive.
- Reference doc (`REFERENCE.md`): stable, low-churn, read on demand. The backlog,
  research/product-evaluation notes, and the per-session model-selection guidance.
- Separate decisions log for the "why" behind locked decisions. Read it before
  undoing anything marked "locked". Terse rule in `CLAUDE.md`, full reasoning here.
- Append-only prompt/session log: one entry per owner prompt (verbatim prompt,
  timestamp, branch, response summary, artifacts: files, commit SHAs, PR numbers).
  Never paste secrets or the internal model identifier. Append to the tail; read
  only the last ~30 lines to get the last entry number and template.
- Archival & rotation by ISO week under `docs/archive/` with an index:
  `STATUS_YYYY-Www.md` and `PROMPT_LOG_YYYY-Www.md`. Rotate prompt-log entries out
  when the live file passes ~1,200 lines (keep ~current plus the last 5 sessions).
  Archives are append-only: never rewrite entries when moving them.
- "Update the documentation" means BOTH the status doc AND the prompt log (plus
  any stale plan/CLAUDE.md), without being asked to name the prompt log. Ship all
  doc updates in the same PR as the work.

## Locked decisions convention
- When the owner says a decision is locked, do not revisit its structure or
  behavior without an explicit request. Terse rule here / in decisions log; full
  reasoning in the decisions log.

## Security posture
- Assist with authorized/defensive security and legitimate dual-use tooling.
  Refuse destructive, mass-targeting, or evasion-for-malice requests.
- For anything hard to reverse or outward-facing, confirm first unless durably
  authorized.
