"""
test_design_system.py - the gate that keeps the interface honest.

The front-end audit found the two worst defects with a contrast meter, not with
taste: the "we never invent a reason" sentence rendered at 3.69:1 and the
secondary border at 1.45:1. Both would have been caught before they shipped by
arithmetic. This is that arithmetic, wired into the build.

What it checks:

1. Contrast. Every text pair and interactive boundary declared in tokens.css
   with an `@contrast` annotation is resolved in BOTH themes and measured with
   the WCAG 2.1 relative-luminance formula. Text must reach 4.5:1 (AA), a UI
   boundary 3:1 (WCAG 1.4.11). Add a token pair, add its annotation, or this
   test does not know to look at it.
2. Theme parity. The dark tokens are written twice, once for an explicit
   data-theme="dark" and once inside the prefers-color-scheme media query. Two
   copies drift. This asserts they are identical, character for character.
3. Annotation integrity. Every token an annotation names must actually exist,
   so a renamed token cannot silently switch its own contrast check off.

Run it on its own to SEE the numbers:

    python tests/test_design_system.py
"""

from __future__ import annotations

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))  # also works when run directly

import ui  # noqa: E402
from ui.components import SEMANTIC_TABLE_MAX_ROWS  # noqa: E402

TEXT_MIN = 4.5   # WCAG 2.1 AA, normal-size text
UI_MIN = 3.0     # WCAG 2.1 1.4.11, non-text contrast (borders, controls)

MINIMUMS = {"text": TEXT_MIN, "ui": UI_MIN}


# --------------------------------------------------------------------------
# WCAG 2.1 contrast, from the spec rather than from a library
# --------------------------------------------------------------------------

def _channel(value_0_255):
    """Linearize one sRGB channel (WCAG 2.1 relative luminance, step 1)."""
    c = value_0_255 / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour):
    """Relative luminance of a #rrggbb colour, 0 (black) to 1 (white)."""
    h = hex_colour.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f"not a hex colour: {hex_colour!r}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(fg, bg):
    """WCAG contrast ratio between two hex colours, 1.0 to 21.0."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


# --------------------------------------------------------------------------
# Reading tokens.css
# --------------------------------------------------------------------------

DECL = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
CONTRAST = re.compile(r"@contrast\s+(text|ui)\s*:\s*--([a-z0-9-]+)\s+on\s+--([a-z0-9-]+)")
VAR_REF = re.compile(r"var\(\s*--([a-z0-9-]+)\s*\)")


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _block(css, selector):
    """Return the declaration text inside the first `selector { ... }` block.

    Deliberately simple: these blocks contain no nested braces, so finding the
    matching close brace is just the next one.
    """
    start = css.index(selector)
    open_brace = css.index("{", start)
    close_brace = css.index("}", open_brace)
    return css[open_brace + 1:close_brace]


def _declarations(block_text):
    """Parse `--name: value;` pairs out of a block, comments already stripped."""
    return {name: value.strip() for name, value in DECL.findall(block_text)}


def _resolve(tokens):
    """Resolve one level of var() indirection, repeatedly, until stable."""
    out = dict(tokens)
    for _ in range(10):
        changed = False
        for key, value in list(out.items()):
            match = VAR_REF.search(value)
            if match and match.group(1) in out:
                out[key] = VAR_REF.sub(out[match.group(1)], value, count=1).strip()
                changed = True
        if not changed:
            break
    return out


def load_tokens():
    """Return {"light": {...}, "dark": {...}} of fully resolved token values."""
    raw = ui.stylesheet_text(["tokens.css"])
    css = _strip_comments(raw)

    base = _declarations(_block(css, ":root {"))
    light_over = _declarations(_block(css, ':root[data-theme="light"]'))
    dark_over = _declarations(_block(css, ':root[data-theme="dark"]'))

    light = _resolve({**base, **light_over})
    dark = _resolve({**base, **dark_over})
    return {"light": light, "dark": dark}


def load_contrast_rules():
    """Return the [(kind, fg_token, bg_token)] declared in tokens.css."""
    raw = ui.stylesheet_text(["tokens.css"])
    return [(kind, fg, bg) for kind, fg, bg in CONTRAST.findall(raw)]


TOKENS = load_tokens()
RULES = load_contrast_rules()


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_contrast_rules_are_declared():
    """The annotations exist at all. A silent stylesheet proves nothing."""
    assert len(RULES) >= 20, f"only {len(RULES)} @contrast annotations found"
    assert any(kind == "ui" for kind, _, _ in RULES), "no interactive boundary is checked"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("kind,fg,bg", RULES, ids=[f"{k}:{f}-on-{b}" for k, f, b in RULES])
def test_declared_pair_meets_wcag(theme, kind, fg, bg):
    """Every declared pair clears its WCAG floor, in both themes."""
    tokens = TOKENS[theme]
    assert fg in tokens, f"--{fg} is not defined in the {theme} theme"
    assert bg in tokens, f"--{bg} is not defined in the {theme} theme"

    ratio = contrast_ratio(tokens[fg], tokens[bg])
    floor = MINIMUMS[kind]
    assert ratio >= floor, (
        f"{theme}: --{fg} ({tokens[fg]}) on --{bg} ({tokens[bg]}) is "
        f"{ratio:.2f}:1, below the {floor}:1 floor for {kind}"
    )


def test_dark_theme_is_written_identically_in_both_places():
    """The two copies of the dark palette must not drift apart.

    tokens.css declares dark twice: once for an explicit data-theme="dark" and
    once inside prefers-color-scheme for documents that opt into "auto". If one
    is edited and the other is not, a reader's system setting silently changes
    the palette. This catches that.
    """
    css = _strip_comments(ui.stylesheet_text(["tokens.css"]))
    explicit = _declarations(_block(css, ':root[data-theme="dark"]'))
    auto = _declarations(_block(css, ':root[data-theme="auto"]'))
    assert explicit == auto, (
        "the two dark-theme blocks have drifted: "
        f"{sorted(set(explicit.items()) ^ set(auto.items()))}"
    )


def test_explicit_light_matches_the_default_root():
    """data-theme="light" must restate the default, not quietly differ."""
    css = _strip_comments(ui.stylesheet_text(["tokens.css"]))
    base = _declarations(_block(css, ":root {"))
    light = _declarations(_block(css, ':root[data-theme="light"]'))
    resolved_base = _resolve(base)
    mismatched = {
        key: (resolved_base.get(key), value)
        for key, value in light.items()
        if resolved_base.get(key) != value
    }
    assert not mismatched, f"data-theme=light differs from :root for {mismatched}"


def test_decorative_border_is_never_used_as_a_control_boundary():
    """--border is 2.08:1 on white. Guard the rule that keeps it decorative.

    This is the A-08 defect encoded: if someone declares --border as an
    interactive boundary, the annotation would claim a 3:1 promise the colour
    cannot keep, and this test says so in plain terms rather than as a ratio.
    """
    offenders = [(k, f, b) for k, f, b in RULES if k == "ui" and f == "border"]
    assert not offenders, (
        "--border is decorative only (table rules, dividers). Use "
        "--border-control for anything a user can interact with."
    )


def test_every_theme_defines_the_same_colour_tokens():
    """Light and dark must cover the same ground, so nothing falls back silently."""
    light_colours = {k for k, v in TOKENS["light"].items() if v.startswith("#")}
    dark_colours = {k for k, v in TOKENS["dark"].items() if v.startswith("#")}
    assert light_colours == dark_colours, (
        f"only in light: {sorted(light_colours - dark_colours)}, "
        f"only in dark: {sorted(dark_colours - light_colours)}"
    )


# --------------------------------------------------------------------------
# components.css: the rules that are easy to get wrong twice
# --------------------------------------------------------------------------

RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)

# Selectors that describe something a user can click, type into or focus. A
# boundary on one of these owes 3:1 under WCAG 1.4.11.
CONTROL_HINTS = (
    "button", "input", "select", "textarea", "[role=\"button\"]",
    "stDownloadButton", "stFileUploader", "stBaseButton",
)


def _rules(css):
    """Return [(selector, declarations)] for every flat rule in a stylesheet.

    Rules nested inside @media are captured; the @media wrapper itself is not,
    which is what we want since it carries no declarations of its own.
    """
    return [(sel.strip(), decls.strip()) for sel, decls in RULE.findall(_strip_comments(css))]


def _components_css():
    return ui.stylesheet_text(["components.css"])


def test_no_rule_encodes_direction_as_colour():
    """The A-01 root cause, encoded so it cannot come back.

    The mockup carried `.d-up{color:var(--red)}` and `.d-down{color:var(--green)}`.
    Those four rules are why a footprint DECREASE was painted as an alarm three
    centimetres from a green panel calling the same fact good news. Hue belongs
    to epistemic status (cited, not explained, needs review, error). Direction is
    a glyph, a sign and a word.
    """
    # Comments are stripped first: the file explains at length why these rules
    # are absent, and quoting them in prose is not the same as shipping them.
    css = _strip_comments(_components_css())
    banned = [".d-up", ".d-down", ".move.up", ".move.down", ".delta-up", ".delta-down"]
    present = [name for name in banned if name in css]
    assert not present, (
        f"{present} encode direction of travel as colour. Use a glyph, a sign "
        "and a word instead, and keep hue for epistemic status."
    )


def test_controls_never_use_the_decorative_border_token():
    """--border is 2.08:1 on white. It may rule a table; it may not bound a control."""
    offenders = []
    for selector, decls in _rules(_components_css()):
        if not any(hint in selector for hint in CONTROL_HINTS):
            continue
        for line in decls.splitlines():
            if "border" in line and re.search(r"var\(--border\)", line):
                offenders.append((selector.replace("\n", " ").strip(), line.strip()))
    assert not offenders, (
        "these interactive selectors bound a control with the decorative "
        f"--border token (2.08:1). Use --border-control: {offenders}"
    )


def test_streamlit_internals_are_labelled_with_the_verified_version():
    """Fragile selectors must say what they close and what they were checked against.

    `data-testid` attributes are Streamlit internals, not a public API. When an
    upgrade renames one, the rule silently stops applying and a defect quietly
    returns. A named version turns that into something a person can diagnose.
    """
    css = _components_css()
    assert re.search(r"Verified against: Streamlit \d+\.\d+", css), (
        "components.css must state the Streamlit version its data-testid "
        "selectors were verified against"
    )

    undocumented = []
    for match in re.finditer(r'\[data-testid="([^"]+)"\]', css):
        preceding = css[max(0, match.start() - 800):match.start()]
        if "*/" not in preceding:
            undocumented.append(match.group(1))
    assert not undocumented, (
        f"no explanatory comment precedes these fragile selectors: {sorted(set(undocumented))}"
    )


def _boot():
    """A fresh headless run of the real app.py.

    Each fixture gets its OWN instance. AppTest interactions mutate the instance
    in place and `.run()` hands the same object back, so a shared instance would
    let one test's button click decide what another test sees. The expensive
    part (reading both workbooks) is behind st.cache_data and AppTest runs
    in-process, so a second boot costs almost nothing.
    """
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=300).run()
    assert not app.exception, f"app.py raised on boot: {app.exception}"
    return app


@pytest.fixture(scope="module")
def cold_app():
    """The page a first-time visitor receives, before pressing anything.

    This is its own fixture because "what is on the page before any input" is
    now a claim worth checking. The app used to run the whole pipeline on a
    sample product unasked; it does not any more, and the comparison is what a
    cold visit lands on instead.
    """
    return _boot()


@pytest.fixture(scope="module")
def rendered_app():
    """The whole page, after a visitor has run the analysis.

    The click is the point: the report exists because someone asked for it.
    """
    app = _boot()
    run = [b for b in app.button if str(b.label).startswith("Run analysis")]
    assert run, f"no Run analysis button on the page: {[b.label for b in app.button]}"
    app = run[0].click().run()
    assert not app.exception, f"app.py raised after Run: {app.exception}"
    return app


def test_a_cold_visit_lands_on_the_comparison_not_a_form(cold_app):
    """The landing surface is the interactive comparison, and it costs nothing.

    Two claims, both of which used to be false. The first thing on the page is
    the factor comparison, not a setup form; and nothing that needs an upload,
    a sign-in or an API key has run yet.
    """
    page = _page(cold_app)
    headings = re.findall(r"<h2>([^<]+)</h2>", page)
    assert headings and headings[0] == "Compare releases", headings
    assert "Run the analysis above" in page, "the cold page does not say what is missing"

    labels = [str(w.label) for w in cold_app.multiselect]
    assert "Scope" in labels and "What happened to the factor" in labels, labels
    assert cold_app.slider, "no minimum-change filter on the page"
    assert cold_app.text_input, "no search box on the page"


def test_the_comparison_filters_actually_narrow_the_table():
    """Typing in the search box changes what is shown. The whole point.

    Its own instance, because it types into the page and would otherwise leave
    every later test looking at a filtered table.
    """
    app = _boot()
    search = [w for w in app.text_input if "Search" in str(w.label)]
    assert search, [str(w.label) for w in app.text_input]

    before = _showing_count(app)
    after = _showing_count(search[0].set_value("electricity").run())
    assert after < before, f"filter did not narrow the table: {before} -> {after}"
    assert after > 0, "no electricity factor survived the search"


def test_a_narrowed_comparison_becomes_a_real_table_with_magnitude_bars():
    """Filtering down is what earns the good table, and that is the point.

    The full register is thousands of rows, so it is drawn as Streamlit's
    virtualised grid. Narrow it to DEFRA's own material movers and it drops
    under SEMANTIC_TABLE_MAX_ROWS, at which point show_table renders the real
    thing: a captioned <table> with column scopes, a magnitude bar per change
    and the direction spoken in words rather than carried by colour.
    """
    app = _boot()
    material = [t for t in app.toggle if "materiality thresholds" in str(t.label)]
    assert material, [str(t.label) for t in app.toggle]

    app = material[0].set_value(True).run()
    assert not app.exception, app.exception

    narrowed = _showing_count(app)
    assert 0 < narrowed <= SEMANTIC_TABLE_MAX_ROWS, narrowed

    page = _page(app)
    comparison = re.search(
        r"<table><caption>DEFRA conversion factors.*?</table>", page, re.S
    )
    assert comparison, "the narrowed comparison did not render as a real table"
    markup = comparison.group(0)
    assert 'scope="col"' in markup
    assert markup.count('class="fill"') >= narrowed, "a change has no magnitude bar"
    assert "visually-hidden" in markup, "direction is not spoken anywhere in the table"


def _showing_count(app):
    """The "Showing N of M factors" figure the comparison prints.

    Reads captions as well as markdown: the count is a st.caption, which AppTest
    keeps in its own bucket rather than in `.markdown`.
    """
    text = _page(app) + "\n" + "\n".join(str(c.value) for c in app.caption)
    match = re.search(r"Showing ([\d,]+) of ([\d,]+) factors", text)
    assert match, "the comparison did not report how many factors it is showing"
    return int(match.group(1).replace(",", ""))


def _page(app):
    return "\n".join(str(block.value) for block in app.markdown)


def _style_blocks(app):
    return [str(b.value) for b in app.markdown if "<style>" in str(b.value)]


def test_app_injects_the_stylesheet_on_the_first_render(cold_app):
    """The layer is worthless if it never reaches the page."""
    styles = _style_blocks(cold_app)
    assert len(styles) == 1, f"expected one injected style block, found {len(styles)}"
    assert "--border-control" in styles[0], "tokens.css did not reach the page"
    assert "stCaptionContainer" in styles[0], "components.css did not reach the page"
    assert "stMultiSelect" in styles[0], "the comparison filters are unstyled"


def test_the_stylesheet_survives_a_rerun(rendered_app):
    """The design layer must still be there after a visitor touches something.

    This is the bug the old session_state guard caused, encoded so it cannot
    come back. Streamlit reruns the whole script on every interaction, and this
    app reruns constantly now: every filter keystroke on the comparison is a
    rerun. The guard emitted the style block only on the first run, so Streamlit
    dropped the element on the second and the page reverted to Streamlit
    defaults, including the 3.69:1 captions the audit was opened over.

    Exactly one, not zero and not two: one proves it survived, and more than one
    would mean inject_styles is being called twice in a single run, which IS how
    style blocks stack.
    """
    styles = _style_blocks(rendered_app)
    assert len(styles) == 1, f"expected one style block after a rerun, found {len(styles)}"
    assert "--border-control" in styles[0]


def test_the_page_reads_compare_result_confidence_movers_explanations_export(rendered_app):
    """The IA, asserted.

    Compare sits first because it is the only section that needs nothing from
    the visitor, and it is the thing a DEFRA practitioner came to look at.
    Confidence sits before Movers for the opposite reason: the trust gate has to
    arrive before the conclusion gets acted on, not two sections after it.

    Every <h2> on this page is a numbered section the nav can reach. That is the
    invariant, so a transition heading is a subhead rather than an <h2>.
    """
    headings = re.findall(r"<h2>([^<]+)</h2>", _page(rendered_app))
    assert headings == [
        "Compare releases", "Result", "Confidence", "Movers", "Explanations", "Export",
    ]


def test_the_page_uses_real_tables_not_canvas_grids(rendered_app):
    """Defect A-04: Streamlit paints its grids to <canvas>, so they cannot be
    read by assistive tech, selected, searched or printed.

    The rule is not "never a grid": above SEMANTIC_TABLE_MAX_ROWS rows the
    virtualised grid genuinely is the better tool, and the full factor register
    is thousands of rows. The rule is that a grid never appears ALONE, so a
    reader who needs the accessible, printable version can always get it. That
    is what show_table's toggle is for, and this counts them.
    """
    page = _page(rendered_app)
    assert page.count("<table>") >= 3
    assert page.count("<caption>") == page.count("<table>"), "a table has no caption"
    assert 'scope="col"' in page

    escapes = [t for t in rendered_app.toggle if "Accessible" in str(t.label)]
    assert len(escapes) >= len(rendered_app.dataframe), (
        f"{len(rendered_app.dataframe)} canvas-rendered grid(s) on the page but "
        f"only {len(escapes)} offer an accessible, printable version"
    )


def test_the_page_never_carries_direction_by_colour_alone(rendered_app):
    """Every movement on the page also states which way it went, in words."""
    page = _page(rendered_app)
    assert page.count("visually-hidden") >= 2, "no spoken direction found on the page"
    for word in ("fell", "rose", "did not change"):
        if f", {word}</span>" in page:
            break
    else:
        raise AssertionError("no direction word reached the page")


def test_every_disclosure_on_the_page_is_named(rendered_app):
    """Defect A-05: disclosures whose only label was a chevron."""
    page = _page(rendered_app)
    summaries = re.findall(r"<summary>(.*?)</summary>", page, re.S)
    assert summaries, "no disclosures rendered"
    unnamed = [s for s in summaries if len(s.strip()) < 3]
    assert not unnamed, f"unnamed disclosures: {unnamed}"


def test_every_token_used_by_components_is_defined():
    """A typo in a var() name fails silently in CSS. Catch it here instead."""
    used = set(VAR_REF.findall(_components_css()))
    defined = set(TOKENS["light"])
    missing = sorted(used - defined)
    assert not missing, f"components.css uses undefined tokens: {missing}"


# --------------------------------------------------------------------------
# Seeing it work
# --------------------------------------------------------------------------

def _report():
    """Print every declared pair and its measured ratio, both themes."""
    print(f"{len(RULES)} declared pairs, measured in both themes\n")
    header = f"{'kind':5} {'foreground':22} {'background':22} {'light':>8} {'dark':>8}"
    print(header)
    print("-" * len(header))
    worst = []
    for kind, fg, bg in RULES:
        ratios = {}
        for theme in ("light", "dark"):
            tokens = TOKENS[theme]
            ratios[theme] = contrast_ratio(tokens[fg], tokens[bg])
        floor = MINIMUMS[kind]
        mark = "" if min(ratios.values()) >= floor else "  FAILS"
        if mark:
            worst.append((kind, fg, bg, ratios))
        print(
            f"{kind:5} --{fg:20} --{bg:20} "
            f"{ratios['light']:7.2f}: {ratios['dark']:7.2f}:{mark}"
        )
    print()
    if worst:
        print(f"{len(worst)} pair(s) below floor.")
        return 1
    print(f"All pairs clear their floor (text {TEXT_MIN}:1, UI boundaries {UI_MIN}:1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_report())
