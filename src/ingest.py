"""
ingest.py — the forgiving front door for a REAL user's inventory spreadsheet.

Today the pipeline only accepts a clean file with exactly three columns named
`line_item`, `quantity`, `unit`. A real client file never looks like that: its
columns are called "Material" or "Description", "Qty" or "Amount", "UoM", there
are extra columns, blank cells, and units in mixed case. This module widens that
front door WITHOUT breaking the core domain rule (never silently guess):

  - It reads .csv or .xlsx (openpyxl is already a dependency; no new one).
  - It looks at the column headers and makes a best guess at which column is the
    item, which is the quantity, and which is the unit, using a plain synonyms
    list (transparent and testable; no AI).
  - Crucially, it reports HOW SURE it is. If it is not confident, the caller (the
    app) must ask the user to confirm rather than run on a guess. A wrong column
    is as damaging as a wrong factor match, so it gets the same honesty.
  - Rows with a blank/garbled quantity, unit, or item are SET ASIDE with a
    reason, never silently dropped or defaulted to zero.

Public entry point:
    load_inventory(file, mapping=None) -> (clean_df, report)

`clean_df` has exactly the columns the rest of the pipeline expects
(`line_item`, `quantity`, `unit`). `report` is a plain dict describing the
column mapping, the tool's confidence, and every row it set aside, so the app
can show "we think your columns are X, Y, Z, correct?" and list the skipped rows.
"""

from __future__ import annotations

import os
import re
import pandas as pd
from rapidfuzz import fuzz

# The three fields the pipeline needs, and the header words that point to each.
# Seeded from common spreadsheet habits; refine these from real client files.
SYNONYMS = {
    "line_item": [
        "line item", "line_item", "item", "material", "materials", "description",
        "activity", "component", "product", "name", "ingredient", "input",
        "process", "flow",
    ],
    "quantity": [
        "quantity", "qty", "amount", "mass", "weight", "volume", "value",
        "number", "count", "usage", "consumption",
    ],
    "unit": [
        "unit", "units", "uom", "unit of measure", "measure", "u o m",
    ],
}

# Confidence bands (0-100). At or above STRONG: confident. Between WEAK and
# STRONG: a tentative guess the user should confirm. Below WEAK: not guessed
# (the user must pick the column). This mirrors the exact/fuzzy/needs_review
# ladder in matching.py.
STRONG = 90.0
WEAK = 60.0

REQUIRED_FIELDS = ("line_item", "quantity", "unit")


def _norm(text) -> str:
    """Lower-case, strip punctuation, collapse whitespace (same idea as matching.py)."""
    s = str(text).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def read_table(file) -> pd.DataFrame:
    """Read a .csv or .xlsx into a raw DataFrame (headers assumed on the first row).

    `file` may be a path string or a file-like object (e.g. a Streamlit upload,
    which carries a `.name`). We pick the reader from the extension.
    """
    name = getattr(file, "name", file)
    ext = os.path.splitext(str(name))[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(file, engine="openpyxl")
    if ext == ".csv" or ext == "":
        return pd.read_csv(file)
    raise ValueError(
        f"Unsupported file type '{ext}'. Please upload a .csv or .xlsx file."
    )


def _score_column(header_norm: str, field: str) -> float:
    """Best fuzzy score of one column header against a field's synonym list."""
    best = 0.0
    for word in SYNONYMS[field]:
        best = max(best, fuzz.token_set_ratio(header_norm, word))
    return best


def guess_mapping(columns) -> tuple[dict, dict]:
    """Guess which column feeds each field, greedily, best score first.

    Returns (mapping, confidence): mapping[field] is a column name or None;
    confidence[field] is the winning score (0-100). Each column is used at most
    once, so two fields can never claim the same column.
    """
    norm = {col: _norm(col) for col in columns}

    # Score every (field, column) pair.
    scored = []
    for field in REQUIRED_FIELDS:
        for col in columns:
            scored.append((_score_column(norm[col], field), field, col))
    # Assign highest scores first; skip a pair if the field or column is taken.
    scored.sort(key=lambda t: t[0], reverse=True)

    mapping = {f: None for f in REQUIRED_FIELDS}
    confidence = {f: 0.0 for f in REQUIRED_FIELDS}
    used_cols: set = set()
    for score, field, col in scored:
        if mapping[field] is not None or col in used_cols:
            continue
        if score < WEAK:
            continue  # below the bar: leave unmapped rather than guess
        mapping[field] = col
        confidence[field] = round(float(score), 1)
        used_cols.add(col)
    return mapping, confidence


def _coerce_quantity(value):
    """Parse a quantity cell into a float, tolerating '1,000' and stray spaces.

    Returns None if it is blank or not a number (the row is then set aside, not
    guessed at)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_inventory(raw_df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, list]:
    """Apply a column mapping to produce the clean 3-column table.

    Any row with a blank item, a blank/garbled quantity, or a blank unit is set
    aside (recorded in the returned list with a reason), never silently kept."""
    clean_rows = []
    set_aside = []
    col_item = mapping.get("line_item")
    col_qty = mapping.get("quantity")
    col_unit = mapping.get("unit")

    for pos, (_, row) in enumerate(raw_df.iterrows()):
        # Spreadsheet-style row number: header is row 1, so first data row is 2.
        row_number = pos + 2

        item = row[col_item] if col_item in raw_df.columns else None
        unit = row[col_unit] if col_unit in raw_df.columns else None
        qty = _coerce_quantity(row[col_qty]) if col_qty in raw_df.columns else None

        item_blank = item is None or str(item).strip() == "" or pd.isna(item)
        unit_blank = unit is None or str(unit).strip() == "" or pd.isna(unit)

        reasons = []
        if item_blank:
            reasons.append("no item name")
        if qty is None:
            reasons.append("missing or non-numeric quantity")
        if unit_blank:
            reasons.append("no unit")

        if reasons:
            set_aside.append(
                {
                    "row_number": row_number,
                    "reason": "; ".join(reasons),
                    "line_item": None if item_blank else str(item).strip(),
                }
            )
            continue

        clean_rows.append(
            {
                "line_item": str(item).strip(),
                "quantity": qty,
                "unit": str(unit).strip(),
            }
        )

    clean_df = pd.DataFrame(clean_rows, columns=["line_item", "quantity", "unit"])
    return clean_df, set_aside


def load_inventory(file, mapping: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Read a real inventory file and return (clean_df, report).

    If `mapping` is given (the user confirmed or overrode the columns in the app),
    it is used as-is. Otherwise the tool guesses and flags whether the guess needs
    the user's confirmation. `clean_df` always has exactly the pipeline's three
    columns; `report` explains what happened in plain terms.
    """
    raw_df = read_table(file)
    columns = list(raw_df.columns)

    if mapping is None:
        mapping, confidence = guess_mapping(columns)
    else:
        # A user-supplied mapping is trusted (they looked at it); confidence 100
        # for anything they set, 0 for anything they left blank.
        confidence = {
            f: 100.0 if mapping.get(f) else 0.0 for f in REQUIRED_FIELDS
        }

    unmapped = [f for f in REQUIRED_FIELDS if not mapping.get(f)]
    tentative = [
        f for f in REQUIRED_FIELDS
        if mapping.get(f) and confidence.get(f, 0.0) < STRONG
    ]
    needs_confirmation = bool(unmapped or tentative)

    if unmapped:
        # We cannot safely build the table without every required column, so
        # return an empty clean_df and let the app ask the user to map them.
        clean_df = pd.DataFrame(columns=["line_item", "quantity", "unit"])
        set_aside = []
    else:
        clean_df, set_aside = build_inventory(raw_df, mapping)

    report = {
        "columns_seen": columns,
        "mapping": mapping,
        "confidence": confidence,
        "unmapped_required": unmapped,
        "tentative_fields": tentative,
        "needs_confirmation": needs_confirmation,
        "rows_total": len(raw_df),
        "rows_used": len(clean_df),
        "rows_set_aside": set_aside,
    }
    return clean_df, report
