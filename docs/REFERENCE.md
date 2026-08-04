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
- **A-07, the one audit defect still open.** Streamlit's file uploader renders an
  `<input type="file">` with no programmatic accessible name, so a screen-reader
  user hears an unlabelled control. Neither CSS nor Python can attach a name to
  it: it needs a Streamlit release that labels it, or a small custom component.
  The visible label and help text are already there, which is why this is the
  cheapest of the twelve to live with in the meantime.
- **Surface the best candidate on a below-threshold match.** The Confidence
  section explains a held line as "Best match scored 49.3, below the 82.0
  confidence threshold, so nothing was assumed." It cannot yet add "the closest
  thing we found was X", because `src/matching.py` keeps only the score once the
  candidate loses (`match_bom`, the `below_threshold` branch). Retaining the
  losing candidate's name is a small change there, and would make the review
  queue much faster to work through. Left rather than smuggled into a view-layer
  pass that was scoped not to touch matching.
- **Offline mode duplicates the quote (from D21).** The offline explainer embeds
  the DEFRA note inside `plain_english_reason`, so the memo shows the note twice:
  once truncated in the reason, once verbatim in the citation block. With a live
  model there is no duplication, because the reason is a short sentence. Fixing it
  means editing the offline explainer's output, which is the grounding layer, so
  it was left out of a citation-rendering change. Worth doing when the offline
  explainer is next opened.
- **The section nav has no active-section highlight (from D22).** It is sticky
  and numbered, which carries most of the value, but nothing marks which section
  you are currently in. Streamlit does not execute `<script>` inside markdown, so
  scroll-spy needs a small custom component. Worth doing if the report grows more
  sections; not worth a component today.
- **The app is light-only, by decision not omission.** `tokens.css` carries a
  full dark theme and the printable memo uses it, but Streamlit paints its own
  chrome before our CSS loads and `.streamlit/config.toml` pins it light, so a
  dark-mode visitor would get a half-dark page. Turning dark on means Streamlit
  theme support for both, not a CSS change.
- **`[data-testid="stElementContainer"]:has(.subnav)` is the one selector doing
  structural work (from D22).** It is what makes the section nav stick, because a
  sticky box cannot leave its containing block and Streamlit sizes every markdown
  wrapper to its content. It depends on two things outside our control: the
  `data-testid` (a Streamlit internal, like the others) and `:has()` (Chrome 105+,
  Safari 15.4+). If the nav ever stops sticking, check those two before the CSS.

- Semantic relabels with low string overlap (Incineration -> Combustion) still
  read as added/removed; would need DEFRA's own relabel notes.
- Package-manager pin + lockfile for reproducible installs (deps are audited now,
  but still unpinned `>=` in requirements.txt).
- **Turn on the sign-in gate (deferred by the owner, D18).** The live app runs
  open: `GEMINI_API_KEY` is set with no `[auth]` section, and `app.py:66` reads
  `use_ai = True if not signin_on else ...`, so anonymous visitors get AI
  explanations on the owner's key. The Google Cloud budget cap is set, which is
  the D17 backstop, and the owner chose to leave the gate off for now. Turn it on
  when the link is shared publicly, when the budget alert fires, or when anyone
  relies on the tool. It is a secrets edit, not a code change: the `[auth]` +
  `[access]` blocks from `.streamlit/secrets.toml.example` per
  `docs/DEPLOY_GUIDE.md`.
- Sandbox network: live Gemini calls and `*.streamlit.app` are both blocked from
  the web sandbox (the proxy denies CONNECT), so anything about the DEPLOY has to
  be verified by the owner. Local tests and the repo remain fully verifiable here.
- **Browser verification IS possible in the sandbox, contrary to what earlier
  sessions assumed.** The proxy blocks the live deploy, not localhost. Chromium
  ships at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, `pip install
  playwright` in a venv gets the driver (dev-only, deliberately NOT in
  `requirements.txt`), and `streamlit run app.py --server.headless true` on
  127.0.0.1 is reachable with `--no-proxy-server`. This is how the design system
  was checked at 375, 768 and 1440. Two traps worth knowing:
  - `chrome --headless --screenshot` fires at the load event, so it captures
    Streamlit's grey loading skeleton. You have to wait for real content, which
    is what Playwright's `wait_for_selector` is for.
  - Chrome's headless window floors at about 500px, so `--window-size=375` does
    not give a 375px viewport. Playwright's `viewport=` does; with raw Chrome,
    put the page in a 375px iframe instead.

## Research / product-evaluation notes

None recorded yet. Add findings here as they accumulate (dataset evaluations,
competitor teardowns, pricing research) so each is captured once and read on
demand rather than re-derived.
