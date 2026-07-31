# Status handoffs, 2026-W31

- H17 (2026-07-31): Owner set the Google Cloud budget cap and chose to defer the
  sign-in gate on the live app, so the deploy runs OPEN with the cap as the only
  control. Recorded as D18 rather than left as an oversight, with the triggers
  that should flip it (link shared publicly, budget alert fires, anyone relies on
  the tool) and the note that turning it on is a secrets edit, not a code change.
  D18 also corrects the D17 write-up: `src/auth.py` degrades to "open, offline for
  all" only when no API key is set, and to "open, AI for all" when one is.
  Docs-only, no code touched.
- H16 (2026-07-31): Owner-facing session, no pipeline code changed. Walked the
  owner through the two manual steps the sandbox cannot do: the GitHub default
  branch is now `main` (verified via the API: `default_branch: "main"`), and the
  app is deployed on Streamlit Community Cloud at <https://efdiff.streamlit.app/>
  with a Gemini key created in Google AI Studio. Could not verify the live app:
  the sandbox proxy denies CONNECT to `*.streamlit.app`, so the owner checks the
  provider banner and the 2.344 to 2.305 demo figure. **Open risk flagged, not
  yet fixed:** the deploy has `GEMINI_API_KEY` set with no `[auth]` section, and
  `app.py:66` sets `use_ai = True` when sign-in is not configured, so the public
  URL currently spends the owner's key for every anonymous visitor. Fix is either
  the `[auth]` + `[access]` secrets from `docs/DEPLOY_GUIDE.md` or removing the
  key. README refreshed with the live link, a Vision section, and a correction
  (it still claimed "no login, no cloud" after D17 shipped both).
