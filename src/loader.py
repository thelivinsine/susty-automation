"""
loader.py — read a DEFRA/DESNZ GHG conversion-factor workbook and normalize it
into ONE tidy table:

    activity | unit | kg_co2e | scope | category | version

This is written against the REAL "Government conversion factors for company
reporting — full set" workbook, whose layout is fiddly:

- Each factor sheet carries its SCOPE as metadata near the top
  (a "Scope:" cell with the value beside it), not as a column.
- A block of guidance/example text sits above the real table.
- The table header is:  Activity | <descriptor cols…> | Unit | kg CO2e | <gas breakdowns…>
  The descriptor columns (Fuel / Type / Material / Country / Haul / Class …) are
  forward-filled — only the first row of each group is populated.
- Some sheets repeat the "kg CO2e" column several times, one per sub-category
  (e.g. Material use: Primary / Re-used / Open-loop / Closed-loop). Those
  sub-category labels live in a SUPER-HEADER row just above the header. We expand
  each block into its own activity so nothing is silently merged.
- A "Year" column sometimes sits between Unit and kg CO2e; we ignore it so the
  same factor still joins across two release years.

Public function:  load_defra(path, version_label) -> pandas.DataFrame
"""

from __future__ import annotations

import re
import pandas as pd


def _clean(text) -> str:
    """Lower-case, collapse whitespace, drop punctuation — for header matching."""
    if text is None:
        return ""
    s = str(text).replace("\n", " ").strip().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _to_number(val):
    """Coerce a cell to a float, or None if it isn't a real number."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, bool):
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


def _find_scope(sheet: pd.DataFrame) -> str:
    """Scope is sheet metadata: find a 'Scope:' cell and read the value beside it."""
    for i in range(min(len(sheet), 15)):
        row = sheet.iloc[i].tolist()
        for j, cell in enumerate(row):
            if _clean(cell) == "scope":
                for k in range(j + 1, len(row)):
                    if row[k] is not None and str(row[k]).strip():
                        return str(row[k]).strip()
    return ""


def _find_header_row(sheet: pd.DataFrame) -> int | None:
    """The real table header row: col 0 == 'Activity' and a 'Unit' cell present."""
    for i in range(min(len(sheet), 45)):
        row = [_clean(v) for v in sheet.iloc[i].tolist()]
        if row and row[0] == "activity" and "unit" in row:
            return i
    return None


def _scope_label(scope_raw: str) -> str:
    """Normalize 'Scope 1'/'Scope 2'/'Scope 3' where possible; pass through else."""
    m = re.search(r"scope\s*([123])", _clean(scope_raw))
    return f"Scope {m.group(1)}" if m else str(scope_raw).strip()


def _join_activity(parts: list[str]) -> str:
    """Join non-empty descriptor parts, dropping consecutive duplicates."""
    cleaned = []
    for p in parts:
        p = str(p).strip()
        if not p or p.lower() == "nan":
            continue
        if not cleaned or cleaned[-1].lower() != p.lower():
            cleaned.append(p)
    return " - ".join(cleaned).strip(" -")


def _clean_unit(unit) -> str:
    """Light unit normalization for later joining."""
    u = _clean(unit)
    u = (
        u.replace("tonnes", "tonne")
        .replace("litres", "litre")
        .replace("cubic metres", "cubic metre")
    )
    return u


def _parse_sheet(sheet: pd.DataFrame, sheet_name: str) -> pd.DataFrame | None:
    """Turn one raw sheet into normalized rows, or None if it isn't a factor sheet."""
    header_row = _find_header_row(sheet)
    if header_row is None:
        return None

    header = [_clean(v) for v in sheet.iloc[header_row].tolist()]
    try:
        unit_idx = header.index("unit")
    except ValueError:
        return None

    # The total-factor columns are every "kg CO2e" header to the RIGHT of Unit
    # (this skips any "Year" column and the gas-breakdown columns after them).
    total_cols = [c for c in range(unit_idx + 1, len(header)) if header[c] == "kg co2e"]
    if not total_cols:
        return None

    # Super-header (row above) holds sub-category labels for repeated kg CO2e blocks.
    super_row = (
        sheet.iloc[header_row - 1].tolist() if header_row - 1 >= 0 else [None] * len(header)
    )
    descriptor_idxs = list(range(0, unit_idx))
    scope = _scope_label(_find_scope(sheet))

    records = []
    ffill = {c: None for c in descriptor_idxs}
    started = False
    blank_streak = 0

    for i in range(header_row + 1, len(sheet)):
        row = sheet.iloc[i].tolist()
        is_blank = all(v is None or str(v).strip() == "" for v in row)
        if is_blank:
            blank_streak += 1
            if started and blank_streak >= 2:
                break
            continue

        # Guidance/footer text (e.g. "FAQs", "Guidance") ends the table.
        head_cell = _clean(row[0]) if row else ""
        if head_cell in {"faqs", "guidance"} and started:
            break

        # Update forward-filled descriptor state. Note: pandas represents empty
        # merged cells as float NaN, and str(NaN) == "nan" (truthy) — so we must
        # gate on pd.notna, or the descriptor level gets overwritten with "nan".
        for c in descriptor_idxs:
            if c < len(row) and pd.notna(row[c]) and str(row[c]).strip():
                ffill[c] = str(row[c]).strip()

        unit = row[unit_idx] if (unit_idx < len(row) and pd.notna(row[unit_idx])) else ""
        base_parts = [ffill[c] for c in descriptor_idxs if ffill[c]]

        row_had_value = False
        for c in total_cols:
            val = _to_number(row[c]) if c < len(row) else None
            if val is None:
                continue
            row_had_value = True
            label = ""
            if c < len(super_row) and super_row[c] is not None:
                lbl = str(super_row[c]).strip()
                if lbl and _clean(lbl) != "kg co2e":
                    label = lbl
            activity = _join_activity(base_parts + ([label] if label else []))
            if not activity:
                continue
            records.append(
                {
                    "activity": activity,
                    "unit": _clean_unit(unit),
                    "kg_co2e": val,
                    "scope": scope,
                    "category": sheet_name,
                }
            )

        if row_had_value:
            started = True
            blank_streak = 0

    if not records:
        return None
    return pd.DataFrame.from_records(records)


def load_defra(path: str, version_label: str) -> pd.DataFrame:
    """
    Load a DEFRA GHG conversion-factor workbook and return a normalized table:
        activity | unit | kg_co2e | scope | category | version

    `version_label` (e.g. "2025") is stamped on every row so two years can be
    diffed later.
    """
    sheets = pd.read_excel(path, sheet_name=None, header=None, engine="openpyxl")
    frames = []
    for name, sheet in sheets.items():
        parsed = _parse_sheet(sheet, name)
        if parsed is not None and not parsed.empty:
            frames.append(parsed)

    if not frames:
        raise ValueError(
            f"No factor tables found in {path}. Is this a DEFRA conversion-factor "
            "workbook? (Expected sheets with an 'Activity' header and a 'kg CO2e' column.)"
        )

    df = pd.concat(frames, ignore_index=True)
    df["version"] = str(version_label)

    # Drop exact duplicate (activity, unit) rows, keeping the first occurrence.
    df = df.drop_duplicates(subset=["activity", "unit"], keep="first").reset_index(
        drop=True
    )
    return df[["activity", "unit", "kg_co2e", "scope", "category", "version"]]
