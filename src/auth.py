"""
auth.py — the sign-in gate for the paid AI explanation, in plain terms.

The tool is OPEN to everyone: any visitor can run the analysis and read the free
offline explanations, which cost nothing. The Claude/Gemini-written explanations
cost real API money, so they sit behind a Google sign-in and a short approved
list, which is how the owner controls who spends the key.

This module wraps Streamlit's built-in Google sign-in (`st.login` / `st.user`)
so the rest of the app can ask three plain questions:

    sign_in_available()  -> is a login provider configured on this deployment?
    current_user()       -> who is signed in right now (or None)?
    approval(email)       -> is this signed-in person allowed to use the paid AI?

Every function is written so the app STILL RUNS when nothing is configured (local
`streamlit run` with no secrets, the tests, the demo). In that case there is no
sign-in and everyone simply gets the free offline explanations.

Config (set in .streamlit/secrets.toml on the host — see secrets.toml.example):

    [auth]                      # turns Google sign-in on (Streamlit built-in)
    ...

    [access]                    # who may use the paid AI explanations
    emails  = ["you@gmail.com"] # exact addresses allowed
    domains = ["yourclient.com"]# or allow a whole company domain
"""

from __future__ import annotations

import streamlit as st


def _secrets_section(name: str) -> dict:
    """Read one [section] from secrets.toml, returning {} if it (or the file) is
    absent. Reading st.secrets with no secrets file raises, so we guard it."""
    try:
        if name in st.secrets:
            return dict(st.secrets[name])
    except Exception:
        pass
    return {}


def sign_in_available() -> bool:
    """True only when a Google sign-in provider is configured for this deployment.
    When False the app runs open, with the free offline explainer for everyone."""
    return bool(_secrets_section("auth"))


def current_user() -> dict | None:
    """The signed-in user as {name, email}, or None if nobody is signed in (or
    sign-in isn't configured). Never raises."""
    try:
        if st.user.is_logged_in:
            return {
                "name": getattr(st.user, "name", "") or "",
                "email": (getattr(st.user, "email", "") or "").lower(),
            }
    except Exception:
        pass
    return None


def _access_rules() -> tuple[set[str], set[str]]:
    """The approved (emails, domains) from the [access] secrets section, lowercased."""
    cfg = _secrets_section("access")
    emails = {str(e).strip().lower() for e in cfg.get("emails", []) if str(e).strip()}
    domains = {str(d).strip().lower().lstrip("@") for d in cfg.get("domains", []) if str(d).strip()}
    return emails, domains


def approval(email: str | None) -> dict:
    """Decide whether this signed-in person may use the paid AI explanations.

    Returns {"allowed": bool, "reason": str}. Rules:
      - not signed in                     -> not allowed (use free offline).
      - signed in, on the emails/domains  -> allowed.
      - signed in, but NO list configured -> allowed, with reason "open" so the
        app can warn the owner that every signed-in user currently spends the key.
    """
    if not email:
        return {"allowed": False, "reason": "not-signed-in"}

    emails, domains = _access_rules()
    if not emails and not domains:
        # No allow-list set yet. Let the owner test after deploy, but flag it so
        # the app can nudge them to lock it down before sharing widely.
        return {"allowed": True, "reason": "open"}

    domain = email.split("@")[-1] if "@" in email else ""
    if email in emails or (domain and domain in domains):
        return {"allowed": True, "reason": "listed"}
    return {"allowed": False, "reason": "not-approved"}
