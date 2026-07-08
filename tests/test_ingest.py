"""
Tests for the forgiving inventory reader (src/ingest.py).

These pin the behaviour that turns the tool from "clean toy file only" into
"accepts a real client's messy spreadsheet": guess the columns from awkward
headers, confirm when unsure, and set aside bad rows instead of guessing.
"""

import os
import sys

import pandas as pd
import pytest
from openpyxl import Workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ingest import load_inventory, guess_mapping, read_table  # noqa: E402


def _write(path, rows, sheet="BOM"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_guesses_awkward_headers(tmp_path):
    path = tmp_path / "client.xlsx"
    _write(path, [
        ["Material", "Qty", "UoM", "Notes"],
        ["Aluminium, primary", "1,200", "tonne", "cans"],
        ["UK grid electricity", 4500, "KWh", "office"],
    ])
    clean_df, report = load_inventory(str(path))
    assert report["mapping"] == {"line_item": "Material", "quantity": "Qty", "unit": "UoM"}
    assert report["needs_confirmation"] is False
    assert report["rows_used"] == 2
    # "1,200" parses to 1200.0; the mixed-case unit is preserved for the matcher.
    assert clean_df.iloc[0]["quantity"] == pytest.approx(1200.0)
    assert clean_df.iloc[1]["unit"] == "KWh"


def test_sets_aside_bad_rows_not_guesses(tmp_path):
    path = tmp_path / "client.xlsx"
    _write(path, [
        ["Material", "Amount", "Unit"],
        ["Good row", 10, "kg"],
        ["Missing qty", "", "kg"],       # blank quantity -> set aside
        ["Garbled qty", "n/a", "kg"],    # non-numeric -> set aside
        ["", 5, "kg"],                    # no item name -> set aside
    ])
    clean_df, report = load_inventory(str(path))
    assert report["rows_used"] == 1
    reasons = {r["row_number"]: r["reason"] for r in report["rows_set_aside"]}
    assert reasons[3] == "missing or non-numeric quantity"
    assert reasons[4] == "missing or non-numeric quantity"
    assert reasons[5] == "no item name"


def test_flags_for_confirmation_when_a_column_is_unclear(tmp_path):
    path = tmp_path / "client.xlsx"
    # No column resembles "unit", so the tool must NOT guess one: it asks.
    _write(path, [
        ["Material", "Amount", "Colour"],
        ["Steel beam", 3, "grey"],
    ])
    _, report = load_inventory(str(path))
    assert "unit" in report["unmapped_required"]
    assert report["needs_confirmation"] is True
    # Without every required column it returns nothing rather than a wrong table.
    assert report["rows_used"] == 0


def test_user_supplied_mapping_is_trusted(tmp_path):
    path = tmp_path / "client.xlsx"
    _write(path, [
        ["thing", "howmuch", "measure"],   # headers the guesser would not know
        ["Diesel", 100, "litre"],
    ])
    mapping = {"line_item": "thing", "quantity": "howmuch", "unit": "measure"}
    clean_df, report = load_inventory(str(path), mapping=mapping)
    assert report["needs_confirmation"] is False
    assert report["rows_used"] == 1
    assert clean_df.iloc[0]["line_item"] == "Diesel"


def test_reads_csv_too(tmp_path):
    path = tmp_path / "client.csv"
    pd.DataFrame(
        {"Item": ["Coal"], "Quantity": [2.0], "Units": ["kg"]}
    ).to_csv(path, index=False)
    clean_df, report = load_inventory(str(path))
    assert report["mapping"]["line_item"] == "Item"
    assert clean_df.iloc[0]["unit"] == "kg"


def test_rejects_unsupported_file_type(tmp_path):
    path = tmp_path / "client.txt"
    path.write_text("not a spreadsheet")
    with pytest.raises(ValueError):
        read_table(str(path))
