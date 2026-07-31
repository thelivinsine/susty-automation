# Reference (read on demand)

Stable, low-churn notes: the backlog, the per-session model guidance, and
research / product-evaluation findings. Consult when relevant, not every session.
Terse rules live in `CLAUDE.md`; the "why" behind locked decisions lives in
`DECISIONS.md`.

## Per-session model selection

The assistant does not auto-pick a model per task. Whatever is set in `/model`
runs the whole session, and it cannot reassign itself mid-task. So pick the model
at the START of each session based on the dominant work. Subagents you spawn can
run on a cheaper model separately.

Rule of thumb: design/decide with the frontier model, build with a heavy model,
fill in with a cheap one. Step UP a tier for ambiguous or high-stakes work (legal,
payments, security, and here the no-guess grounding logic). A "plan then switch"
hybrid (frontier while planning, cheaper to execute) is useful.

| Tier | Best for | Cost |
| --- | --- | --- |
| Frontier (Fable / Opus-plan) | Architecture and system design, LCA/methodology nuance, pricing/monetization, persuasive marketing copy, research-heavy planning | Highest |
| Heavy (Opus) | Cross-cutting implementation: multi-file features, careful refactors, the grounding/no-guess layer, anything touching factor matching or the AI explanation contract | High |
| Standard (Sonnet) | Well-specified build work: features from an approved plan, UI from a design, structured content, doc-following integrations | Medium |
| Cheap (Haiku) | Mechanical, well-bounded edits: placeholder fills, config flips, single-file copy tweaks | Low |

How to apply it:
- At session start, tell the owner which tier the dominant work wants, and why, in
  one line. If the work is mixed, name the split (e.g. "design with frontier, then
  switch to heavy to build").
- Map the task, not the topic. A routine UI tweak is standard, but step up to
  heavy the moment a fix turns gnarly or spans many files. Drafting legal or
  marketing copy is frontier even though it is "just text".
- Design and build can be two sessions/models: plan on the frontier tier, then the
  owner switches and the assistant executes against the written plan.
- When you finish planning something big, write the plan to a doc so the cheaper
  build session can execute without re-deriving it.

## Backlog / next candidates

(Moved out of `STATUS.md` so the status doc stays a lean snapshot.)

- Within-family relabel pairing: grouping the renamed-and-moved output into rename
  families (D14) made it readable and honest, but the underlying per-variant deltas
  still scatter +-100% because DEFRA REORDERED the HGV sub-tables and the greedy
  matcher pairs old rows against reordered new rows. A finer within-family pairing
  (align sub-rows by their leaf/variant, or use DEFRA's own row map) would make the
  per-variant deltas trustworthy. Left rather than guessed for now.
- Streamlit theming: a GOV.UK-familiar look was designed for the standalone report
  view (`docs/mockups/govuk_report_view.html`). The real app (`app.py`) still uses
  Streamlit defaults; theming it to match (config.toml palette + CSS) is a natural
  next step (P16).
- Semantic relabels with low string overlap (Incineration -> Combustion) still
  read as added/removed; would need DEFRA's own relabel notes.
- Package-manager pin + lockfile for reproducible installs (deps are audited now,
  but still unpinned `>=` in requirements.txt).
- **Open wallet on the live deploy (do this first).** The app is public at
  <https://efdiff.streamlit.app/> with `GEMINI_API_KEY` set and no `[auth]`
  section. `app.py:66` reads `use_ai = True if not signin_on else ...`, so with
  sign-in unconfigured every anonymous visitor gets AI explanations on the
  owner's key. That is D17's documented behavior and correct for a local run, but
  on a public URL it removes the cost control D17 exists to provide. Fix: add the
  `[auth]` + `[access]` secrets per `docs/DEPLOY_GUIDE.md`, or remove the key so
  the public app serves the free offline explainer only. A billing budget alert on
  the Google project is the backstop either way, not the fix.
- Sandbox network: live Gemini calls and `*.streamlit.app` are both blocked from
  the web sandbox (the proxy denies CONNECT), so anything deployment-specific has
  to be verified by the owner. Local tests and the repo remain fully verifiable
  here.

## Research / product-evaluation notes

None recorded yet. Add findings here as they accumulate (dataset evaluations,
competitor teardowns, pricing research) so each is captured once and read on
demand rather than re-derived.
