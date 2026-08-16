"""
ui - the owned design layer for the Streamlit app.

Today `app.py` injects no CSS at all, so every visual decision in the product is
a Streamlit default. That is what the front-end audit measured 12 defects
against (docs/audit/). This package holds the layer that replaces those
defaults: the tokens, the components built on them, and the number formatting.

`inject_styles()` is the entry point. Call it once per script run, right after
`st.set_page_config(...)`, and every component class in this package resolves.
Once per RUN, not once per session: see the note in the function.

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


def inject_styles():
    """Emit the design layer into the page. Call it once per script run.

    It used to guard on a session_state flag so that it wrote the block only on
    the FIRST run of a session, on the theory that re-emitting would stack a
    copy per rerun. That theory was wrong, and the guard was the bug.

    Streamlit addresses elements by their position in the script, so the same
    st.markdown at the same position REPLACES its predecessor on a rerun; it
    never stacks. What the guard actually did was skip the element entirely on
    every rerun, at which point Streamlit removed the one already on the page,
    and the whole design layer went with it: the page silently fell back to
    Streamlit defaults the moment a visitor touched any widget. Measured in a
    real browser, first load against one rerun: captions went from #505a5f
    (7.07:1) to the default ink, and every card, masthead and table rule
    stopped resolving.

    Stacking only happens if this is called more than once in a SINGLE run,
    which is what test_design_system counts.
    """
    import streamlit as st

    st.markdown(f"<style>\n{stylesheet_text()}\n</style>", unsafe_allow_html=True)
