"""
test_ui_components.py - the markup contract.

Three things are being defended here, all of them from the front-end audit.

ESCAPING. BOM line items come from a file a stranger uploaded, and the app
renders them through `unsafe_allow_html`. If a line item can inject markup, an
accessibility fix has become a security hole. A `<script>` has to come out inert.

SEMANTICS. Streamlit paints its data grids to a `<canvas>` (defect A-04), so
they cannot be read aloud, selected, searched or printed. Our tables must be
real tables with a caption and column scopes.

COLOUR INDEPENDENCE. Nothing may depend on hue alone. Every status carries its
own words and every direction carries a word as well as a glyph, so the meaning
survives a greyscale print, a colour-blind reader and a screen reader.

Run it on its own to SEE the markup:

    python tests/test_ui_components.py
"""

from __future__ import annotations

import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ui import components as c      # noqa: E402
from ui import format as f          # noqa: E402


def _frame():
    return pd.DataFrame(
        {
            "line_item": ["Electricity generated, UK", "Diesel (average blend)"],
            "co2e_old": [0.15045, 0.12854],
            "co2e_new": [0.11132, 0.12918],
            "line_delta": [-0.03913, 0.00064],
        }
    )


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

def test_a_script_in_an_uploaded_line_item_comes_out_inert():
    """The one that matters. An uploaded file must not be able to inject markup."""
    hostile = pd.DataFrame(
        {"line_item": ["<script>alert(1)</script>"], "co2e_new": [1.0]}
    )
    html = c.table(hostile, caption="Contributors", numeric_cols=["co2e_new"])

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_hostile_input_cannot_break_out_of_an_attribute_or_a_caption():
    """Quotes and angle brackets are escaped, so a value cannot start a tag.

    The payload's own text may still read as "onmouseover=" on the page. That is
    fine and is the point: it is inert text content, not an attribute, because
    the quotes that would have closed ours are escaped.
    """
    payload = '" onmouseover="alert(1)'
    text = re.search(r"^<span[^>]*>(.*)</span>$", c.badge(payload)).group(1)
    assert '"' not in text and "<" not in text and ">" not in text
    assert "&quot;" in text

    caption = c.table(_frame(), caption='"><img src=x onerror=alert(1)>')
    assert "<img" not in caption
    assert "&lt;img src=x onerror=alert(1)&gt;" in caption


def test_every_component_escapes_its_text():
    """A sweep, so a component added later cannot quietly skip escaping."""
    payload = "<b>x</b>"
    fragments = [
        c.badge(payload),
        c.alert(payload),
        c.alert(payload, title=payload),
        c.stat_row([(payload, payload)]),
        c.verdict_card(payload, payload, "", note=payload),
        c.section(payload, caption=payload),
        c.disclosure(payload, "<p>body</p>"),
        c.movement(-1.0, "▼", payload, figure=payload),
    ]
    for fragment in fragments:
        assert "<b>" not in fragment, f"unescaped text leaked into: {fragment[:120]}"
        assert "&lt;b&gt;" in fragment


# ---------------------------------------------------------------------------
# Table semantics
# ---------------------------------------------------------------------------

def test_tables_are_real_tables_with_a_caption_and_column_scopes():
    html = c.table(_frame(), caption="Biggest contributors", numeric_cols=["co2e_new"])

    assert "<table>" in html
    assert "<caption>Biggest contributors</caption>" in html
    assert html.count('scope="col"') == len(_frame().columns)
    assert "<thead>" in html and "<tbody>" in html


def test_the_scroll_container_cannot_drag_the_page_with_it():
    """`contain: paint` is load-bearing, not decoration.

    Without it a table wider than its container still contributes its width to
    the page, so the whole page gains a phantom horizontal scroll into blank
    space. Measured at 375px while building the mockups: 480px of empty scroll.
    """
    html = c.table(_frame(), caption="Contributors")
    assert 'class="table-scroll"' in html

    from ui import stylesheet_text

    css = stylesheet_text(["components.css"])
    block = re.search(r"\.table-scroll\s*\{(.*?)\}", css, re.S)
    assert block, "no .table-scroll rule found"
    assert "contain: paint" in block.group(1)
    assert "overflow-x: auto" in block.group(1)


def test_numeric_columns_are_right_aligned_and_formatted():
    html = c.table(_frame(), caption="Contributors", numeric_cols=["co2e_old"])
    assert '<td class="num">0.1505</td>' in html      # 4 significant figures
    assert '<td class="item">Electricity generated, UK</td>' in html


def test_column_headings_are_human_readable():
    html = c.table(_frame(), caption="Contributors")
    assert "Line item" in html
    assert "kg CO2e (old)" in html
    assert "line_item" not in html


def test_an_empty_table_gives_a_quiet_empty_state_not_an_alarm():
    """Defect A-11: three message types shared one style. Nothing to show is
    not a warning and must not be dressed as one."""
    html = c.table(_frame().iloc[0:0], caption="Contributors", empty_text="Nothing moved.")
    assert 'class="empty"' in html
    assert "role=" not in html
    assert "Nothing moved." in html


# ---------------------------------------------------------------------------
# Colour independence
# ---------------------------------------------------------------------------

def test_direction_is_a_word_and_a_glyph_never_a_colour():
    down = f.direction(-0.039)
    up = f.direction(0.5)
    flat = f.direction(0)

    assert down["word"] == "fell" and down["glyph"] == "▼"
    assert up["word"] == "rose" and up["glyph"] == "▲"
    assert flat["word"] == "did not change"
    for result in (down, up, flat):
        assert "colour" not in result and "color" not in result


def test_the_movement_glyph_is_hidden_and_the_word_is_read_out():
    """A screen reader hears "fell", not "black down pointing triangle"."""
    html = c.movement(-0.039, "▼", "fell", figure="-0.03913")
    assert 'aria-hidden="true"' in html
    assert '<span class="visually-hidden">, fell</span>' in html
    assert "-0.03913" in html


def test_every_badge_carries_its_own_words():
    for kind in c.BADGE_KINDS:
        html = c.badge(f"status {kind}", kind=kind)
        assert f"status {kind}" in html, f"badge {kind} has no text label"


def test_badge_kinds_describe_status_not_direction():
    """Hue is spent on what we know, never on which way a number went."""
    forbidden = {"up", "down", "good", "bad", "rise", "fall", "increase", "decrease"}
    assert not forbidden & set(c.BADGE_KINDS)


# ---------------------------------------------------------------------------
# Disclosures and headings
# ---------------------------------------------------------------------------

def test_a_disclosure_is_named_and_carries_its_count():
    """Defect A-05: disclosures whose only label was a chevron."""
    html = c.disclosure("Rows set aside", "<p>body</p>", count=3)
    assert "<summary>Rows set aside (3)</summary>" in html
    assert "<details" in html


def test_headings_are_explicit_about_their_level():
    """Defect A-12: the live page ran H2, H1, H3."""
    assert "<h2>Result</h2>" in c.section("Result")
    assert "<h3>Detail</h3>" in c.section("Detail", level=3)


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def test_significant_figures_make_a_column_scannable():
    """1199.7254 and 0.0634 stop sitting in the same column as raw floats."""
    assert f.sig_figs(1199.7254) == "1,200"
    assert f.sig_figs(0.06345) == "0.06345"
    assert f.sig_figs(2.3442) == "2.344"
    assert f.sig_figs(0.177) == "0.1770"      # trailing zero kept, so columns align
    assert f.sig_figs(0) == "0"


def test_missing_numbers_say_so_rather_than_printing_zero():
    """A missing factor is not a zero factor. Never guess, not even visually."""
    assert f.sig_figs(None) == "n/a"
    assert f.sig_figs(float("nan")) == "n/a"
    assert f.kg(None) == "n/a"
    assert f.signed_pct(None) == "n/a"


def test_signed_values_always_show_their_sign():
    assert f.signed(0.00064) == "+0.0006400"
    assert f.signed(-0.03913) == "-0.03913"
    assert f.signed_pct(-26.04) == "-26.0%"
    assert f.signed_pct(45.3) == "+45.3%"


def test_unknown_columns_still_get_a_readable_heading():
    assert f.human_column("co2e_old") == "kg CO2e (old)"
    assert f.human_column("some_new_column") == "Some new column"


# ---------------------------------------------------------------------------
# Seeing it work
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The nav's active-section highlight
# ---------------------------------------------------------------------------

def test_the_scrollspy_watches_exactly_the_sections_it_was_given():
    """The nav and the highlight are built from one list, so they cannot drift."""
    html = c.scrollspy([("s-result", "Result"), ("s-export", "Export")])
    assert '["s-result", "s-export"]' in html
    assert "aria-current" in html


def test_the_scrollspy_gives_up_quietly_when_it_cannot_reach_the_page():
    """It is an enhancement, not a dependency.

    The script runs inside a components iframe and reaches its parent document.
    If a Streamlit upgrade sandboxes that away, the nav has to keep working with
    no highlight rather than throwing on every scroll, so the reach is inside a
    try/catch that returns.
    """
    html = c.scrollspy([("s-result", "Result")])
    assert "try { win = window.parent; doc = win.document; } catch (e) { return; }" in html


def test_the_scrollspy_holds_no_reference_to_a_node():
    """Streamlit replaces DOM nodes on rerun, so anything cached goes stale."""
    html = c.scrollspy([("s-result", "Result")])
    assert "doc.querySelectorAll('.subnav a')" in html, "links must be re-queried, not stored"
    assert "doc.getElementById(IDS[i])" in html, "sections must be re-queried, not stored"


def _demo():
    move = f.direction(-0.03913)
    print("A rendered table:\n")
    print(c.table(_frame(), caption="Biggest contributors", numeric_cols=["co2e_old", "co2e_new", "line_delta"]))
    print("\nThe verdict card:\n")
    print(
        c.verdict_card(
            "Product footprint",
            "2.344 to 2.305 kg CO2e",
            c.movement(-1.68, move["glyph"], move["word"], figure=f.signed_pct(-1.68)),
            note="Recomputed from the same bill of materials.",
        )
    )
    print("\nA hostile line item, escaped:\n")
    print(c.table(pd.DataFrame({"line_item": ["<script>alert(1)</script>"]}), caption="Set aside"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
