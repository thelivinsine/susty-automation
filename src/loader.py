"""
loader.py — read a DEFRA/DESNZ GHG conversion-factor workbook and normalize it
into ONE tidy table:

    activity | unit | kg_co2e | scope | category | version

Why this is fiddly: the real DEFRA "Government conversion factors for company
reporting" workbook has many sheets, title rows, merged cells, a two-row header,
and category columns (Level 1..4) that are only filled on the first row of each
group. This loader inspects each sheet, finds the real header row, forward-fills
the category levels, and coerces the CO2e column to numbers.

Public function:  load_defra(path, version_label) -> pandas.DataFrame
"""

from __future__ import annotations

import re
import pandas as pd


# Column header keywords we look for (case-insensitive, punctuation-insensitive).
_LEVEL_KEYS = ["level 1", "level 2", "level 3", "level 4"]
_SCOPE_KEY = "scope"
_UNIT_KEYS = ["uom", "unit"]
_COLTEXT_KEY = "column text"
_CO2E_KEY = "co2e"  # matches "kg CO2e", "GHG Conversion Factor ... kg CO2e", etc.


def _clean(text) -> str:
    """Lower-case, collapse whitespace, drop punctuation — for header matching."""
    if text is None:
        return ""
    s = str(text).replace("\n", " ").strip().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _find_header_row(sheet: pd.DataFrame) -> int | None:
    """
    Find the row index that holds the column headers. We anchor on the cell that
    reads exactly "scope", which every DEFRA factor sheet has.
    """
    for i in range(min(len(sheet), 60)):  # header is always near the top
        row = [_clean(v) for v in sheet.iloc[i].tolist()]
        if _SCOPE_KEY in row:
            return i
    return None


def _build_column_map(header_cells: list[str], below_cells: list[str]) -> dict:
    """
    Map our logical column names to physical column indexes. DEFRA sometimes
    splits a header across two rows (year on top, "kg CO2e" below), so we check
    both the header row and the row just beneath it.
    """
    colmap: dict[str, int] = {}
    for idx, (top, below) in enumerate(zip(header_cells, below_cells)):
        combined = f"{top} {below}".strip()

        if top == _SCOPE_KEY and "scope" not in colmap:
            colmap["scope"] = idx
        for j, key in enumerate(_LEVEL_KEYS, start=1):
            if top == key:
                colmap[f"level_{j}"] = idx
        if top == _COLTEXT_KEY and "column_text" not in colmap:
            colmap["column_text"] = idx
        if top in _UNIT_KEYS and "unit" not in colmap:
            colmap["unit"] = idx
        # The first column that mentions CO2e is the total kg CO2e per unit.
        if _CO2E_KEY in combined and "kg_co2e" not in colmap:
            colmap["kg_co2e"] = idx
    return colmap


def _parse_sheet(sheet: pd.DataFrame) -> pd.DataFrame | None:
    """Turn one raw sheet into normalized rows, or None if it isn't a factor sheet."""
    header_row = _find_header_row(sheet)
    if header_row is None:
        return None

    header_cells = [_clean(v) for v in sheet.iloc[header_row].tolist()]
    below_idx = header_row + 1
    below_cells = (
        [_clean(v) for v in sheet.iloc[below_idx].tolist()]
        if below_idx < len(sheet)
        else [""] * len(header_cells)
    )
    colmap = _build_column_map(header_cells, below_cells)

    # A usable factor sheet needs at least a CO2e column and one category level.
    has_level = any(k.startswith("level_") for k in colmap)
    if "kg_co2e" not in colmap or not has_level:
        return None

    # Data starts after the header (and after the sub-header row if it looked like
    # part of the header rather than data).
    data_start = header_row + 1
    if "kg co2e" in " ".join(below_cells) or "co2e" in " ".join(below_cells):
        # the row directly below is a continuation of the header, skip it too
        if not _looks_like_data(sheet.iloc[below_idx], colmap):
            data_start = header_row + 2

    body = sheet.iloc[data_start:].copy()

    # Forward-fill the category levels and scope (only filled on group's first row).
    fill_cols = [colmap[k] for k in colmap if k.startswith("level_") or k == "scope"]
    for c in fill_cols:
        body[c] = body[c].ffill()

    records = []
    for _, row in body.iterrows():
        activity = _make_activity(row, colmap)
        if not activity:
            continue
        kg = _to_number(row.iloc[colmap["kg_co2e"]])
        if kg is None:
            continue  # rows without a numeric factor are headings / notes
        unit = str(row.iloc[colmap["unit"]]).strip() if "unit" in colmap else ""
        scope = _scope_label(row.iloc[colmap["scope"]]) if "scope" in colmap else ""
        category = (
            str(row.iloc[colmap["level_1"]]).strip() if "level_1" in colmap else ""
        )
        records.append(
            {
                "activity": activity,
                "unit": _clean_unit(unit),
                "kg_co2e": kg,
                "scope": scope,
                "category": category,
            }
        )
    if not records:
        return None
    return pd.DataFrame.from_records(records)


def _looks_like_data(row: pd.Series, colmap: dict) -> bool:
    """True if this row already contains a numeric factor (i.e. it's data)."""
    return _to_number(row.iloc[colmap["kg_co2e"]]) is not None


def _make_activity(row: pd.Series, colmap: dict) -> str:
    """Join the non-empty Level 1..4 (and Column Text) into one activity name."""
    parts = []
    for j in range(1, 5):
        key = f"level_{j}"
        if key in colmap:
            val = row.iloc[colmap[key]]
            if pd.notna(val) and str(val).strip():
                parts.append(str(val).strip())
    if "column_text" in colmap:
        val = row.iloc[colmap["column_text"]]
        if pd.notna(val) and str(val).strip() and str(val).strip().lower() != "nan":
            parts.append(str(val).strip())
    # De-duplicate consecutive repeats (DEFRA repeats Level names sometimes).
    cleaned = []
    for p in parts:
        if not cleaned or cleaned[-1].lower() != p.lower():
            cleaned.append(p)
    return " - ".join(cleaned).strip(" -")


def _to_number(val):
    """Coerce a cell to a float, or None if it isn't a real number."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    if s == "" or s.lower() in {"nan", "n/a", "na", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _scope_label(val) -> str:
    """Normalize scope to 'Scope 1' / 'Scope 2' / 'Scope 3' where possible."""
    s = _clean(val)
    m = re.search(r"scope\s*([123])", s)
    if m:
        return f"Scope {m.group(1)}"
    m = re.fullmatch(r"([123])", s)
    if m:
        return f"Scope {m.group(1)}"
    return str(val).strip() if val is not None else ""


def _clean_unit(unit: str) -> str:
    """Light normalization of the unit string for later joining."""
    u = unit.strip().lower()
    u = u.replace("tonnes", "tonne").replace("litres", "litre").replace("kg ", "kg")
    return u


def load_defra(path: str, version_label: str) -> pd.DataFrame:
    """
    Load a DEFRA GHG conversion-factor workbook and return a normalized table:
        activity | unit | kg_co2e | scope | category | version

    `version_label` is a free-text tag (e.g. "2025") stamped on every row so two
    loaded years can be diffed later.
    """
    sheets = pd.read_excel(path, sheet_name=None, header=None, engine="openpyxl")
    frames = []
    for name, sheet in sheets.items():
        parsed = _parse_sheet(sheet)
        if parsed is not None and not parsed.empty:
            # Fall back to the sheet name for category if Level 1 was blank.
            parsed["category"] = parsed["category"].replace("", name).fillna(name)
            frames.append(parsed)

    if not frames:
        raise ValueError(
            f"No factor tables found in {path}. Is this a DEFRA conversion-factor "
            "workbook? (Expected sheets with a 'Scope' header and a 'kg CO2e' column.)"
        )

    df = pd.concat(frames, ignore_index=True)
    df["version"] = str(version_label)

    # Drop exact duplicate activity+unit rows, keeping the first.
    df = df.drop_duplicates(subset=["activity", "unit"], keep="first").reset_index(
        drop=True
    )
    return df[["activity", "unit", "kg_co2e", "scope", "category", "version"]]
