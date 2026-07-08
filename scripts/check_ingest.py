"""
check_ingest.py — SEE the forgiving inventory reader work on a deliberately messy
spreadsheet, the kind a real client would send (weird headers, extra columns,
mixed-case units, a blank quantity, and a stray total row).

Run:  python scripts/check_ingest.py
Prints the guessed column mapping, the rows it used, the rows it set aside (and
why), and "INGEST OK" if it behaved.
"""

import os
import sys

import pandas as pd
from openpyxl import Workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ingest import load_inventory  # noqa: E402


def _write_messy_file(path):
    """A realistic messy client inventory: awkward headers, an extra 'Notes'
    column, a mixed-case unit, one row with no quantity, and a 'Total' row with
    no item name. None of this should crash or be silently miscounted."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Client BOM"
    ws.append(["Material", "Qty", "UoM", "Notes"])                 # awkward headers + extra col
    ws.append(["Aluminium, primary production", "1,200", "tonne", "cans"])  # comma in number
    ws.append(["UK grid electricity", 4500, "KWh", "office"])      # mixed-case unit
    ws.append(["Cardboard packaging", 30, "kg", ""])
    ws.append(["Mystery input", "", "kg", "supplier TBC"])         # blank quantity -> set aside
    ws.append(["", 5730, "tonne", "TOTAL"])                        # no item name -> set aside
    wb.save(path)


def main():
    tmp = os.path.join(ROOT, "data", "synthetic")
    os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, "_messy_inventory_demo.xlsx")
    _write_messy_file(path)

    clean_df, report = load_inventory(path)

    print("Columns the file actually had:", report["columns_seen"])
    print()
    print("What the tool guessed (and how sure, 0-100):")
    for field in ("line_item", "quantity", "unit"):
        col = report["mapping"][field]
        conf = report["confidence"][field]
        print(f"  {field:10s} <- {str(col):22s}  (confidence {conf})")
    print()
    print(f"Needs the user to confirm? {report['needs_confirmation']}")
    print()
    print(f"Rows used ({report['rows_used']} of {report['rows_total']}):")
    print(clean_df.to_string(index=False))
    print()
    print(f"Rows set aside ({len(report['rows_set_aside'])}):")
    for r in report["rows_set_aside"]:
        print(f"  row {r['row_number']}: {r['reason']} (item: {r['line_item']!r})")
    print()

    # A few sanity checks so this is a real check, not just a print.
    assert report["mapping"]["line_item"] == "Material"
    assert report["mapping"]["quantity"] == "Qty"
    assert report["mapping"]["unit"] == "UoM"
    assert report["rows_used"] == 3, "the 3 good rows should be used"
    assert len(report["rows_set_aside"]) == 2, "blank-qty and no-item rows set aside"
    assert clean_df.iloc[0]["quantity"] == 1200.0, "'1,200' should parse to 1200"
    os.remove(path)
    print("INGEST OK")


if __name__ == "__main__":
    main()
