"""
format.py - how numbers and directions are written down.

Two jobs, both of them corrections the front-end audit asked for.

FIGURES. A raw pandas render puts 1199.7254 and 0.0634 in the same column and
lets the reader work out which end is which. Significant figures by magnitude
fixes that: every cell in a column carries the same number of meaningful digits,
so the column scans. Full precision is not lost, it moves to the export, where a
reviewer who needs the last decimal can find it.

DIRECTION. This module is where the load-bearing rule is actually enforced:

    Hue encodes epistemic status. Direction is carried by glyph, sign and word.

`direction()` returns a glyph AND a word for exactly that reason. A footprint
that falls is not "good news" and a footprint that rises is not an error, so
neither gets a colour. The word is also what a screen reader reads out, and what
survives a greyscale print, which a red-versus-green convention does not.
"""

from __future__ import annotations

import math

NOT_AVAILABLE = "n/a"

# Column names the pipeline uses internally, and what a reader should see.
# Anything not listed falls back to a de-underscored, sentence-cased version.
COLUMN_NAMES = {
    "activity": "Activity",
    "line_item": "Line item",
    "unit": "Unit",
    "units": "Units",
    "quantity": "Quantity",
    "scope": "Scope",
    "category": "Category",
    "factor_old": "Factor (old)",
    "factor_new": "Factor (new)",
    "kg_co2e_old": "Factor (old)",
    "kg_co2e_new": "Factor (new)",
    "co2e_old": "kg CO2e (old)",
    "co2e_new": "kg CO2e (new)",
    "line_delta": "Change (kg CO2e)",
    "pct_change": "Change",
    "match_score": "Match score",
    "match_method": "How it matched",
    "needs_review": "Needs review",
    "row_number": "Row",
    "reason": "Why it was set aside",
    "old_name": "Was called",
    "new_name": "Now called",
    "n_variants": "Variants",
    "n_material": "Past threshold",
    "movement": "Value movement",
    "footprint_impact": "Impact (kg CO2e)",
    "retrieval_score": "Retrieval score",
}


def _is_missing(value):
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def sig_figs(value, figures=4):
    """Format a number to a fixed number of significant figures.

    The point is column legibility, not precision: 1199.7254 becomes 1,200 and
    0.06345 stays 0.06345, so both read as four meaningful digits rather than as
    one long number and one short one. Trailing zeros are kept (0.1770), because
    dropping them breaks the alignment that makes a column scannable.
    """
    if _is_missing(value):
        return NOT_AVAILABLE
    number = float(value)
    if number == 0:
        return "0"
    exponent = math.floor(math.log10(abs(number)))
    decimals = min(max(0, figures - 1 - exponent), 10)
    return f"{round(number, decimals):,.{decimals}f}"


def signed(value, figures=4):
    """Same as sig_figs, but always carrying an explicit + or -."""
    if _is_missing(value):
        return NOT_AVAILABLE
    number = float(value)
    text = sig_figs(abs(number), figures)
    if number > 0:
        return f"+{text}"
    if number < 0:
        return f"-{text}"
    return text


def signed_pct(value, decimals=1):
    """A percentage with an explicit sign, for example +45.3% or -26.0%."""
    if _is_missing(value):
        return NOT_AVAILABLE
    return f"{float(value):+.{decimals}f}%"


def kg(value, figures=4, unit="kg CO2e"):
    """A mass with its unit, for example 2.344 kg CO2e."""
    if _is_missing(value):
        return NOT_AVAILABLE
    return f"{sig_figs(value, figures)} {unit}"


def direction(value, rose="rose", fell="fell", flat="did not change"):
    """Describe which way a number moved, without using colour.

    Returns a dict with:
      glyph  a triangle, decorative only, always hidden from screen readers
      word   the same fact in words, which is what is actually read out
      sign   "up", "down" or "flat", for picking a neutral CSS class

    There is deliberately no colour in this return value. The whole A-01 defect
    was a decrease painted red beside a green panel reporting the same fact
    positively, and it came from treating direction as a hue.
    """
    if _is_missing(value):
        return {"glyph": "", "word": NOT_AVAILABLE, "sign": "flat"}
    number = float(value)
    if number > 0:
        return {"glyph": "▲", "word": rose, "sign": "up"}
    if number < 0:
        return {"glyph": "▼", "word": fell, "sign": "down"}
    return {"glyph": "", "word": flat, "sign": "flat"}


def human_column(name):
    """Turn an internal column name into a heading a reader can understand."""
    key = str(name)
    if key in COLUMN_NAMES:
        return COLUMN_NAMES[key]
    words = key.replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else key


def plural(count, word, many=None):
    """"1 line" but "3 lines", so the copy never says "line(s)".

    Small, and worth having in one place: a parenthesised plural is the tell of
    a string that was assembled rather than written.
    """
    return f"{count} {word if count == 1 else (many or word + 's')}"
