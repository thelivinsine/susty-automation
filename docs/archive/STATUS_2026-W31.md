# Status handoffs, 2026-W31

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
