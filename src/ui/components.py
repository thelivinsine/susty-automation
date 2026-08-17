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

    # A magnitude bar beside each movement, scaled to the largest movement in
    # its own column. It is what turns "which of these numbers matters" from an
    # arithmetic exercise into a glance. The bar is ink in both directions: size
    # is the only thing it encodes, exactly as the glyph is the only thing that
    # encodes direction.
    widest = {}
    for col in moving:
        try:
            biggest = max(abs(float(v)) for v in df[col] if v == v and v is not None)
        except (TypeError, ValueError):
            biggest = 0.0
        widest[col] = biggest or 0.0

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
                try:
                    share = abs(float(value)) / widest[col] * 100 if widest[col] else 0.0
                except (TypeError, ValueError):
                    share = 0.0
                mark = movement(value, way["glyph"], way["word"], figure=signed(value, figures))
                cells.append(
                    '<td class="num"><span class="bar">'
                    '<span class="track" aria-hidden="true">'
                    f'<span class="fill" style="width:{share:.4g}%"></span></span>'
                    f"{mark}</span></td>"
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


ALERT_VARIANTS = {
    "warning": "",                  # a plain statement that needs attention
    "ok": " warning--ok",           # something completed or was confirmed
    "review": " warning--review",   # held for a human, never guessed
    "error": " warning--error",     # something genuinely went wrong
}


def alert(text, kind="warning", title=None):
    """A message with a role, so assistive tech announces it as one.

    Four roles, four looks. kind="none" is the quiet empty state ("nothing to
    show"), which is not a warning and must not be dressed as one.
    """
    if kind == "none":
        return f'<p class="empty">{esc(text)}</p>'
    role = "alert" if kind == "error" else "note"
    variant = ALERT_VARIANTS.get(kind, "")
    heading = f'<span class="hd">{esc(title)}</span>' if title else ""
    return (
        f'<div class="warning{variant}" role="{role}">'
        '<span class="icon" aria-hidden="true">!</span>'
        f'<span class="txt">{heading}{esc(text)}</span></div>'
    )


def disclosure(summary, body_html, count=None, open_by_default=False,
               summary_html=None):
    """A named, collapsible section.

    Every disclosure carries a summary that says what is inside and how much of
    it (defect A-05 was disclosures whose only label was a chevron). Uses a real
    `<details>` element, so it is keyboard-operable without any JavaScript and
    prints expanded under the print rules.

    summary_html is for the explanation cards, whose summary is a composed row
    (status tag, what changed, what it did to this footprint) rather than a
    sentence. It is markup this module built, never user text, and `summary` is
    still required so the plain label exists for anyone reading the source.
    """
    label = esc(summary)
    if count is not None:
        label += f" ({esc(count)})"
    is_open = " open" if open_by_default else ""
    return (
        f"<details class=\"disclosure\"{is_open}>"
        f"<summary>{summary_html or label}</summary>"
        f'<div class="disclosure-body">{body_html}</div>'
        "</details>"
    )


def verdict_card(headline, figure, movement_html, note=None, partial=False,
                 pair=None, facts=(), status=None, run_id=None):
    """The result, stated once, at the top.

    Green means "the run completed and this is the answer", not "good news".
    It is carried by the 4px rail and the status tag rather than by filling the
    card, so the figure itself stays ink on ground where a number is most
    readable. The neutral `partial` variant is the honest signal when coverage
    sits below the stated bar: the number is incomplete, which is neither good
    news nor bad.

    pair renders the two totals as two figures with an arrow between them
    (("2025", "2.344"), ("2026", "2.305")), which is what lets old and new be
    compared at a glance. Without it the card shows the single `figure`.

    facts is the strip along the bottom: the handful of things a reader needs
    beside the headline so the number is never read on its own.
    """
    variant = " panel--partial" if partial else ""

    tags = badge(*status) if status else ""
    run = f'<span class="run">{esc(run_id)}</span>' if run_id else ""
    top = (
        f'<div class="top"><span class="eyebrow">{esc(headline)}</span>{tags}{run}</div>'
        if (headline or tags or run) else ""
    )

    if pair:
        (old_label, old_figure), (new_label, new_figure) = pair
        figures = (
            f'<div class="figure"><div class="lab">{esc(old_label)}</div>'
            f'<div class="fig tnum">{esc(old_figure)}</div>'
            '<div class="unit">kg CO2e</div></div>'
            '<div class="arrow" aria-hidden="true">&#8594;</div>'
            f'<div class="figure"><div class="lab">{esc(new_label)}</div>'
            f'<div class="fig tnum">{esc(new_figure)}</div>'
            '<div class="unit">kg CO2e</div></div>'
        )
    else:
        figures = f'<div class="figure"><div class="fig tnum">{esc(figure)}</div></div>'

    words = f'<div class="words">{esc(note)}</div>' if note else ""
    delta = (
        f'<div class="delta"><span class="amount">{movement_html}</span>{words}</div>'
        if (movement_html or note) else ""
    )

    strip = ""
    if facts:
        cells = "".join(
            f'<div><div class="k">{esc(key)}</div><div class="v tnum">{esc(value)}</div></div>'
            for key, value in facts
        )
        strip = f'<div class="facts">{cells}</div>'

    return (
        f'<div class="panel{variant}">'
        '<div class="rail"></div>'
        f"{top}"
        f'<div class="main">{figures}{delta}</div>'
        f"{strip}</div>"
    )


def meter(value_pct, bar_pct, label, beside=None, legend=None):
    """A percentage measured against the bar it has to clear.

    A bare "85.7%" does not say whether that is enough, so the stated bar is
    drawn on the track. There is no hue in here on purpose: partial coverage is
    a fact about the answer, not an alarm.
    """
    fill = max(0.0, min(100.0, float(value_pct or 0)))
    mark = max(0.0, min(100.0, float(bar_pct)))
    reading = f"{label}. Bar is {bar_pct:g} percent."
    ends = legend or ("0%", f"{bar_pct:g}% bar", "100%")
    marks = "".join(f"<span>{esc(text)}</span>" for text in ends)
    aside = f'<span class="beside">{esc(beside)}</span>' if beside else ""
    return (
        f'<div class="headline"><span class="big tnum">{esc(label)}</span>{aside}</div>'
        '<div class="meter">'
        f'<div class="track" role="img" aria-label="{esc(reading)}">'
        f'<div class="fill" style="width:{fill:.4g}%"></div>'
        f'<div class="mark" style="left:{mark:.4g}%"></div>'
        "</div>"
        f'<div class="legend">{marks}</div>'
        "</div>"
    )


def fact_bar(items):
    """A row of counted facts: [(label, value)].

    Used where a paragraph of statistics was doing the work of a table, for
    example the version scan. Counts are scannable; a sentence full of numbers
    is not.
    """
    cells = "".join(
        f'<div><div class="k">{esc(key)}</div><div class="v tnum">{esc(value)}</div></div>'
        for key, value in items
    )
    return f'<div class="factbar">{cells}</div>'


def masthead(product, subtitle, fact_label=None, fact_value=None, status=None):
    """The app shell's top bar: what this is, what it is comparing, run state.

    It exists because the page opened on a bare title that said none of those
    things, so a reader arriving at a long report had no way to tell which two
    releases produced it.
    """
    fact = (
        f'<div class="fact"><b>{esc(fact_label)}</b>{esc(fact_value)}</div>'
        if fact_label else ""
    )
    tag = badge(*status) if status else ""
    return (
        '<div class="masthead">'
        '<span class="mark" aria-hidden="true">EF</span>'
        f'<span class="word">{esc(product)}<span>{esc(subtitle)}</span></span>'
        f'<span class="right">{fact}{tag}</span>'
        "</div>"
    )


def subnav(items):
    """The sticky section nav: [(anchor, label)] in reading order.

    Numbered because the sections ARE a sequence: result, then whether it can be
    trusted, then what moved, then why, then what to send. The number is the
    argument, not decoration.
    """
    links = "".join(
        f'<a href="#{esc(anchor)}"><span class="n">{i}</span>{esc(label)}</a>'
        for i, (anchor, label) in enumerate(items, start=1)
    )
    return f'<nav class="subnav" aria-label="Report sections">{links}</nav>'


def scrollspy(items):
    """Mark the section the reader is currently in, in the nav.

    Streamlit does not execute `<script>` inside markdown, so this is returned
    as the body of a `st.components.v1.html` iframe, which does run scripts and
    (being same-origin) can reach the page that hosts it.

    Three properties this deliberately has:

    1. **Best-effort.** Every step is inside a try/catch and the first failure
       returns silently. If a Streamlit upgrade sandboxes the iframe away from
       its parent, the nav loses its highlight and loses nothing else. That is
       why the resting state of the nav is legible on its own.
    2. **No stored references.** The handler re-queries the links and sections
       on every frame it runs, because Streamlit replaces DOM nodes on rerun and
       anything cached would point at detached elements.
    3. **No user text.** The only values interpolated are the anchor ids this
       module was given, JSON-encoded. Nothing from an uploaded file reaches it.

    items is the same [(anchor, label)] the nav was built from; only the anchors
    are used, so the two cannot drift apart.
    """
    import json

    anchors = json.dumps([anchor for anchor, _ in items])

    return (
        "<script>(function () {\n"
        "  var doc, win;\n"
        "  try { win = window.parent; doc = win.document; } catch (e) { return; }\n"
        "  if (!doc) { return; }\n"
        "  var IDS = __ANCHORS__;\n"
        # The nav parks under Streamlit's header, so a section counts as current
        # once its heading passes just below that. Same number as the CSS
        # scroll-margin, so a clicked link lands on the section it just lit.
        "  var LINE = 150;\n"
        "  var queued = false;\n"
        "  function paint() {\n"
        "    queued = false;\n"
        "    try {\n"
        "      var current = null;\n"
        "      for (var i = 0; i < IDS.length; i++) {\n"
        "        var el = doc.getElementById(IDS[i]);\n"
        "        if (el && el.getBoundingClientRect().top <= LINE) { current = IDS[i]; }\n"
        "      }\n"
        "      if (!current) { current = IDS[0]; }\n"
        "      var links = doc.querySelectorAll('.subnav a');\n"
        "      var here = null;\n"
        "      for (var j = 0; j < links.length; j++) {\n"
        "        var mine = links[j].getAttribute('href') === '#' + current;\n"
        "        if (mine) { links[j].setAttribute('aria-current', 'true'); here = links[j]; }\n"
        "        else { links[j].removeAttribute('aria-current'); }\n"
        "      }\n"
        # Narrow screens scroll the nav sideways, so the marked link can sit off
        # the end of it. scrollLeft is set directly rather than with
        # scrollIntoView, which would also scroll the page and fight the reader.
        "      if (here && current !== win.__efNavAt) {\n"
        "        win.__efNavAt = current;\n"
        "        var strip = here.parentNode;\n"
        "        var left = here.offsetLeft;\n"
        "        var right = left + here.offsetWidth;\n"
        "        if (left < strip.scrollLeft) { strip.scrollLeft = left; }\n"
        "        else if (right > strip.scrollLeft + strip.clientWidth) {\n"
        "          strip.scrollLeft = right - strip.clientWidth;\n"
        "        }\n"
        "      }\n"
        "    } catch (e) { /* a half-built page on rerun: the next frame retries */ }\n"
        "  }\n"
        "  function schedule() {\n"
        "    if (queued) { return; }\n"
        "    queued = true;\n"
        "    win.requestAnimationFrame(paint);\n"
        "  }\n"
        # Scroll events do not bubble, and the page scrolls inside Streamlit's
        # main element rather than the window, so the listener is registered in
        # the CAPTURE phase on the document. That catches the scroll whichever
        # element turns out to be the scroller.
        "  if (!win.__efNavSpy) {\n"
        "    win.__efNavSpy = true;\n"
        "    doc.addEventListener('scroll', schedule, true);\n"
        "    win.addEventListener('resize', schedule);\n"
        "  }\n"
        # On a rerun the script runs again over fresh nodes, so paint once now
        # rather than waiting for the reader to scroll.
        "  schedule();\n"
        "}());</script>"
    ).replace("__ANCHORS__", anchors)


def file_uploader_label(label):
    """Give the file uploader's two hidden controls a real accessible name.

    A-07 (`docs/DECISIONS.md` D20): Streamlit's native `<input type="file">`
    inside `st.file_uploader` carries its OWN `aria-label` ("file upload"),
    ignoring the widget's `label` argument entirely, so `label_visibility=
    "collapsed"` leaves it with no connection to what is actually being
    asked for. Worse, live-measured against Streamlit 1.61.1: the visible
    "Upload" button next to it has an explicit but EMPTY `aria-label`,
    which does not suppress the accessible name, it just makes the browser
    fall through to the button's own text content instead: the Material
    icon ligature "upload" run straight into the visible word "Upload",
    with no separator, read aloud as one garbled "uploadUpload" (the
    front-end audit's G14, confirmed live here, not the "no name at all"
    this was first filed as in D20).

    Neither is fixable from CSS, which cannot set an ARIA attribute, or
    from `st.file_uploader`'s own arguments. Runs the same way `scrollspy`
    does: as the body of a same-origin `st.components.v1.html` iframe,
    best-effort behind a try/catch, re-run fresh on every Streamlit rerun
    (never cached) since Streamlit replaces the uploader's DOM nodes then.
    `label` is JSON-encoded, the only value interpolated into the script.
    """
    import json

    safe_label = json.dumps(label)

    return (
        "<script>(function () {\n"
        "  var doc, win;\n"
        "  try { win = window.parent; doc = win.document; } catch (e) { return; }\n"
        "  if (!doc) { return; }\n"
        "  try {\n"
        "    var zone = doc.querySelector('[data-testid=\"stFileUploaderDropzone\"]');\n"
        "    if (!zone) { return; }\n"
        "    var label = __LABEL__;\n"
        "    var input = zone.querySelector('input[type=\"file\"]');\n"
        "    if (input) { input.setAttribute('aria-label', label); }\n"
        "    var btn = zone.querySelector('button');\n"
        "    if (btn) { btn.setAttribute('aria-label', 'Upload ' + label); }\n"
        "  } catch (e) { /* a half-built page on rerun: the next rerun retries */ }\n"
        "}());</script>"
    ).replace("__LABEL__", safe_label)


def step(number, title, hint=None, state="now"):
    """One numbered step of the setup flow.

    state is "now", "done" or "next", so a reader can see where they are in a
    sequence rather than being handed three controls at once.
    """
    mark = "&#10003;" if state == "done" else esc(number)
    note = f'<div class="h">{esc(hint)}</div>' if hint else ""
    return (
        f'<div class="step {esc(state)}"><span class="n" aria-hidden="true">{mark}</span>'
        f'<span><span class="t">{esc(title)}</span>{note}</span></div>'
    )


def file_chip(name, detail):
    """The uploaded file, named and measured, so it is clear what will be read."""
    suffix = (str(name).rsplit(".", 1)[-1] if "." in str(name) else "file")[:4]
    return (
        '<div class="file">'
        f'<span class="ic" aria-hidden="true">{esc(suffix.upper())}</span>'
        f'<span class="nm">{esc(name)}<span class="mt">{esc(detail)}</span></span>'
        "</div>"
    )


def explanation_head(status_html, name, meta, impact=None, impact_note=None):
    """The summary row of an explanation card.

    Status first, then what changed, then what it did to THIS product, because
    the status is what decides whether the rest can be quoted to a client.
    """
    right = ""
    if impact is not None:
        note = f'<span class="k">{esc(impact_note)}</span>' if impact_note else ""
        right = f'<span class="impact"><span class="v">{esc(impact)}</span>{note}</span>'
    return (
        f'<span class="xhead">{status_html}'
        f'<span class="who"><span class="name">{esc(name)}</span>'
        f'<span class="meta">{esc(meta)}</span></span>{right}</span>'
    )


def source_quote(text, cite):
    """A DEFRA extract, set as a source rather than as our own prose."""
    return (
        f'<blockquote class="src">{esc(text)}'
        f"<cite>{esc(cite)}</cite></blockquote>"
    )


def checklist(rows):
    """The pre-send list: state first, then the item, then the detail."""
    body = "".join(
        f'<div class="row">{state_html}'
        f'<span class="tx"><b>{esc(label)}</b>{esc(detail)}</span></div>'
        for state_html, label, detail in rows
    )
    return f'<div class="check">{body}</div>'


def section(title, level=2, caption=None, eyebrow=None, anchor=None):
    """A section heading, with its place in the sequence stated above it.

    level is explicit so the page keeps one H1 and a clean H2/H3 spine, which is
    defect A-12 (the live page ran H2, H1, H3). anchor is what the sticky nav
    scrolls to.
    """
    tag = f"h{int(level)}"
    top = f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    note = f'<p class="caption">{esc(caption)}</p>' if caption else ""
    ident = f' id="{esc(anchor)}"' if anchor else ""
    return (
        f'<div class="section"{ident}>{top}'
        f"<{tag}>{esc(title)}</{tag}>{note}</div>"
    )
