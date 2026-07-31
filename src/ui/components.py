"""
components.py - the markup the app emits, built on tokens.css and components.css.

Every function here RETURNS an HTML string rather than drawing to the screen.
That is deliberate: it means the markup can be asserted in a test with no
Streamlit runtime, no browser and no screenshot, which is how the escaping rule
and the table semantics below are actually enforced rather than merely intended.
`write()` is the one function that touches Streamlit.

Two rules run through all of it.

ESCAPING IS NOT OPTIONAL. Line items come from a file the user uploaded and this
markup is emitted through `unsafe_allow_html`. Every interpolated value goes
through `esc()`. A `<script>` in a BOM line has to come out as inert text, and
there is a test that says so.

TABLES ARE REAL TABLES. Streamlit paints its data grids to a `<canvas>`, so
they cannot be read by a screen reader, selected, searched or printed (defect
A-04). For a tool whose output goes into an assurance folder that is a category
error, so `table()` emits a genuine `<table>` with a `<caption>` and
`scope="col"` headers.
"""

from __future__ import annotations

import html

from .format import direction, human_column, sig_figs, signed

# Above this many rows a real <table> stops being pleasant to use and
# Streamlit's virtualised grid is the better tool. app.py switches on this and
# offers the semantic table behind a toggle instead.
SEMANTIC_TABLE_MAX_ROWS = 500

# Badge kinds. The key is the epistemic status, never a direction of travel.
BADGE_KINDS = {
    "cited": "green",       # a verbatim reason from the DEFRA notes
    "silent": "grey",       # the notes do not explain this one
    "review": "yellow",     # held for a human, never guessed
    "error": "red",         # something genuinely went wrong
    "neutral": "blue",      # a plain label, for example a scope
    "done": "green",        # a run that finished, not a judgement on the answer
}


def esc(value):
    """Escape a value for HTML. The only way a value should ever reach markup."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def write(*fragments):
    """Emit HTML fragments into the Streamlit page.

    Fragments are joined without blank lines on purpose: a blank line inside an
    HTML block makes Streamlit's Markdown parser close the block early and leak
    raw tags onto the page.
    """
    import streamlit as st

    st.markdown("".join(fragments), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def table(df, caption, columns=None, numeric_cols=(), direction_cols=(),
          figures=4, empty_text=None):
    """A real, readable, printable table.

    caption is required, not decorative: it is what tells a screen-reader user
    what the table is before they enter it, and what labels the table in print.

    direction_cols get a glyph, an explicit sign and a hidden word instead of a
    bare number, so which way a value moved survives greyscale and a screen
    reader. Everything in those cells is derived from the number itself, never
    from user text, so this does not open a hole in the escaping rule.

    The scroll container carries `contain: paint` as well as `overflow-x: auto`.
    Without it a table wider than its container still contributes its width to
    the page, so the whole page gains a phantom horizontal scroll into blank
    space. Measured while building the mockups: 480px of empty scroll at 375px
    wide with the rule absent, 0 with it present.
    """
    cols = [str(c) for c in (columns if columns is not None else df.columns)]
    moving = {str(c) for c in direction_cols}
    numeric = {str(c) for c in numeric_cols} | moving

    if len(df) == 0:
        return alert(empty_text or "Nothing to show here.", kind="none")

    head = "".join(
        f'<th scope="col" class="{"num" if col in numeric else "item"}">'
        f"{esc(human_column(col))}</th>"
        for col in cols
    )

    body = []
    for _, row in df.iterrows():
        cells = []
        for col in cols:
            value = row.get(col)
            if col in moving:
                way = direction(value)
                cells.append(
                    f'<td class="num">'
                    f'{movement(value, way["glyph"], way["word"], figure=signed(value, figures))}'
                    f"</td>"
                )
            elif col in numeric:
                cells.append(f'<td class="num">{esc(sig_figs(value, figures))}</td>')
            else:
                cells.append(f'<td class="item">{esc(value)}</td>')
        body.append(f"<tr>{''.join(cells)}</tr>")

    return (
        '<div class="table-scroll">'
        f"<table><caption>{esc(caption)}</caption>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )


# ---------------------------------------------------------------------------
# Small pieces
# ---------------------------------------------------------------------------

def badge(text, kind="neutral"):
    """A status tag. Always carries its own words, never colour alone.

    Colour is a second channel here, not the channel. A greyscale print, a
    colour-blind reader and a screen reader all get the same information from
    the text, which is the point of the colour-independence rule.
    """
    tint = BADGE_KINDS.get(kind, "blue")
    return f'<span class="tag {tint}">{esc(text)}</span>'


def movement(value, glyph, word, figure=None):
    """Show which way a number moved, in glyph, sign and word, with no hue.

    The glyph is decorative and hidden from assistive tech; the word carries the
    meaning. This is the replacement for the red-up/green-down convention that
    painted a falling footprint as an alarm.
    """
    shown = esc(figure if figure is not None else "")
    mark = f'<span class="dir" aria-hidden="true">{esc(glyph)}</span> ' if glyph else ""
    return (
        f'<span class="move tnum">{mark}{shown}'
        f'<span class="visually-hidden">, {esc(word)}</span></span>'
    )


def definitions(pairs):
    """A key-and-value block: the label above, the prose below.

    Used for the explanation drawer, where each row is a question the consultant
    has to be able to answer ("why it changed", "methodology note").
    """
    rows = "".join(
        f'<div class="row"><div class="key">{esc(key)}</div>'
        f'<div class="val">{value}</div></div>'
        for key, value in pairs
    )
    return f'<div class="kv">{rows}</div>'


def stat_row(items):
    """The big-number row: value large, label small and underneath."""
    cells = "".join(
        f'<div class="stat"><div class="v tnum">{esc(value)}</div>'
        f'<div class="k">{esc(label)}</div></div>'
        for value, label in items
    )
    return f'<div class="stats">{cells}</div>'


def alert(text, kind="warning", title=None):
    """A message with a role, so assistive tech announces it as one.

    kind="none" is the quiet empty state ("nothing to show"), which is not a
    warning and must not be dressed as one.
    """
    if kind == "none":
        return f'<p class="empty">{esc(text)}</p>'
    role = "alert" if kind == "error" else "note"
    heading = f'<span class="hd">{esc(title)}</span>' if title else ""
    return (
        f'<div class="warning" role="{role}">'
        '<span class="icon" aria-hidden="true">!</span>'
        f'<span class="txt">{heading}{esc(text)}</span></div>'
    )


def disclosure(summary, body_html, count=None, open_by_default=False):
    """A named, collapsible section.

    Every disclosure carries a summary that says what is inside and how much of
    it (defect A-05 was disclosures whose only label was a chevron). Uses a real
    `<details>` element, so it is keyboard-operable without any JavaScript and
    prints expanded under the print rules.
    """
    label = esc(summary)
    if count is not None:
        label += f" ({esc(count)})"
    is_open = " open" if open_by_default else ""
    return (
        f"<details class=\"disclosure\"{is_open}>"
        f"<summary>{label}</summary>"
        f'<div class="disclosure-body">{body_html}</div>'
        "</details>"
    )


def verdict_card(headline, figure, movement_html, note=None, partial=False):
    """The result, stated once, at the top.

    The green panel means "the run completed and this is the answer", not "good
    news". That is why the direction of travel lives inside it as a glyph and a
    word rather than as the panel's colour, and why the neutral `partial`
    variant exists: when coverage is below the stated bar, the honest signal is
    that the number is incomplete, which is neither good nor bad.
    """
    variant = " panel--partial" if partial else ""
    tail = f'<div class="base">{esc(note)}</div>' if note else ""
    return (
        f'<div class="panel{variant}">'
        f'<div class="lab">{esc(headline)}</div>'
        f'<div class="fig tnum">{esc(figure)}</div>'
        f'<div class="sub">{movement_html}</div>'
        f"{tail}</div>"
    )


def section(title, level=2, caption=None):
    """A section heading with the GOV.UK rule above it.

    level is explicit so the page keeps one H1 and a clean H2/H3 spine, which is
    defect A-12 (the live page ran H2, H1, H3).
    """
    tag = f"h{int(level)}"
    note = f'<p class="caption">{esc(caption)}</p>' if caption else ""
    return (
        f'<div class="section"><div class="h2wrap">'
        f"<{tag}>{esc(title)}</{tag}></div>{note}</div>"
    )
