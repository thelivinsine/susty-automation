"""
ui - the owned design layer for the Streamlit app.

Today `app.py` injects no CSS at all, so every visual decision in the product is
a Streamlit default. That is what the front-end audit measured 12 defects
against (docs/audit/). This package holds the layer that replaces those
defaults: the tokens, the components built on them, and the number formatting.

`inject_styles()` is the entry point. Call it once, right after
`st.set_page_config(...)`, and every component class in this package resolves.

The stylesheets are plain `.css` files rather than Python strings on purpose:
they can be linted, diffed, opened in a browser, and read by someone who does
not write Python. `stylesheet_text()` returns the same CSS without needing a
Streamlit runtime, which is what the contrast test reads.
"""

from __future__ import annotations

import os

UI_DIR = os.path.dirname(os.path.abspath(__file__))

# Order matters: tokens define the custom properties everything else consumes.
STYLESHEETS = ("tokens.css", "components.css")

# Streamlit reruns the whole script on every interaction, so the guard lives in
# session_state rather than a module global.
_INJECTED_FLAG = "_ui_styles_injected"


def stylesheet_path(name):
    """Absolute path to one of this package's stylesheets."""
    return os.path.join(UI_DIR, name)


def stylesheet_text(names=None):
    """Return the design layer's CSS as one string.

    Pure file reading, no Streamlit import, so tests and the export memo can
    use exactly the same bytes the app serves.
    """
    parts = []
    for name in names or STYLESHEETS:
        with open(stylesheet_path(name), encoding="utf-8") as fh:
            parts.append(f"/* ---- {name} ---- */\n{fh.read()}")
    return "\n".join(parts)


def inject_styles(force=False):
    """Emit the design layer into the page, once per session.

    Returns True if it wrote the style block, False if it was already there.
    Set force=True to re-emit (useful while editing CSS with the app running).
    """
    import streamlit as st

    if not force and st.session_state.get(_INJECTED_FLAG):
        return False
    st.markdown(f"<style>\n{stylesheet_text()}\n</style>", unsafe_allow_html=True)
    st.session_state[_INJECTED_FLAG] = True
    return True
