"""
Golden-vector tests for the loader and diff.

The loader is the tool's foundation: it parses the fiddly real DEFRA layout
(scope read from sheet metadata, forward-filled descriptor columns, a skipped
"Year" column, repeated "kg CO2e" blocks expanded via a super-header, and
duplicate rows dropped). A silent regression there would corrupt every downstream
carbon number. These golden vectors pin the EXACT normalized output for a small,
hand-built fixture that exercises each of those behaviours, so any drift fails the
build.

The fixture is written here in code (not committed as an opaque binary) so a
non-developer can read exactly what is being tested. It is an INDEPENDENT oracle:
it lays out cells the way the real workbook does, without reusing the app's own
synthetic-data generator, so a bug in that generator cannot mask a loader bug.
"""

import os
import sys

import pandas as pd
import pytest
from openpyxl import Workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loader import load_defra  # noqa: E402
from diff import diff_versions  # noqa: E402


# --- The frozen fixture: two annual workbooks in the real DEFRA shape ----------
# Each sheet is a list of rows. None leaves a cell blank (an empty merged cell,
# which is how DEFRA represents a forward-filled descriptor). The layout mirrors
# the real one: a title line, a "Scope:" metadata cell, a blank line, an optional
# super-header row of sub-category labels, then the "Activity | ... | Unit | ... |
# kg CO2e" header, then data.

def _fuels_sheet(year_values):
    d, p, ng, coal, biogas = year_values
    rows = [
        ["Fuels: conversion factors (GOLDEN FIXTURE)"],
        ["Scope:", "Scope 1"],
        [],
        ["Guidance"],
        # Header carries a "Year" column between Unit and kg CO2e; it must be
        # ignored so the same factor still joins across years.
        ["Activity", "Fuel", "Unit", "Year", "kg CO2e"],
        ["Liquid fuels", "Diesel", "litres", 2000, d],
        [None, "Petrol", "litres", 2000, p],           # activity forward-filled
        ["Gaseous fuels", "Natural gas", "kWh", 2000, ng],
        ["Liquid fuels", "Diesel", "litres", 2000, 9.99],  # duplicate -> dropped
    ]
    if coal is not None:
        rows.append(["Solid fuels", "Coal", "kg", 2000, coal])
    if biogas is not None:
        rows.append(["Gaseous fuels", "Biogas", "kWh", 2000, biogas])
    return rows


def _materials_sheet(year_values):
    alu_primary, alu_closed = year_values
    return [
        ["Material use: conversion factors (GOLDEN FIXTURE)"],
        # A messy scope string must normalize to "Scope 3".
        ["Scope:", "Scope 3 (indirect)"],
        [],
        # Super-header: sub-category labels above each repeated kg CO2e column.
        [None, None, None, "Primary material production", "Closed-loop source"],
        ["Activity", "Material", "Unit", "kg CO2e", "kg CO2e"],
        ["Metal", "Aluminium", "tonnes", alu_primary, alu_closed],
    ]


# Frozen values per year. (diesel, petrol, natural_gas, coal, biogas)
FUELS_2025 = (2.5, 2.3, 0.18, 2.9, None)     # coal present, no biogas
FUELS_2026 = (2.65, 2.3, 0.175, None, 0.09)  # coal removed, biogas added
# (aluminium primary, aluminium closed-loop)
MATERIALS_2025 = (12000.0, 500.0)
MATERIALS_2026 = (13500.0, 520.0)


def _write_workbook(path, fuels_rows, materials_rows):
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in (("Fuels", fuels_rows), ("Material use", materials_rows)):
        ws = wb.create_sheet(title=title)
        for row in rows:
            ws.append(row)
    wb.save(path)


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    d = tmp_path_factory.mktemp("golden")
    old_path = os.path.join(d, "defra_2025.xlsx")
    new_path = os.path.join(d, "defra_2026.xlsx")
    _write_workbook(old_path, _fuels_sheet(FUELS_2025), _materials_sheet(MATERIALS_2025))
    _write_workbook(new_path, _fuels_sheet(FUELS_2026), _materials_sheet(MATERIALS_2026))
    return load_defra(old_path, "2025"), load_defra(new_path, "2026")


# --- Golden: exact loader output ----------------------------------------------
# (activity, unit, kg_co2e, scope, category). The duplicate diesel row is gone,
# the "Year" column is absent, units are normalized (litres->litre,
# tonnes->tonne), the Scope-3 sheet's messy scope is normalized, and the two
# kg CO2e blocks are expanded into distinct activities via the super-header.
EXPECTED_2025 = [
    ("Liquid fuels - Diesel", "litre", 2.5, "Scope 1", "Fuels"),
    ("Liquid fuels - Petrol", "litre", 2.3, "Scope 1", "Fuels"),
    ("Gaseous fuels - Natural gas", "kwh", 0.18, "Scope 1", "Fuels"),
    ("Solid fuels - Coal", "kg", 2.9, "Scope 1", "Fuels"),
    ("Metal - Aluminium - Primary material production", "tonne", 12000.0, "Scope 3", "Material use"),
    ("Metal - Aluminium - Closed-loop source", "tonne", 500.0, "Scope 3", "Material use"),
]


def test_loader_columns_are_exactly_the_contract(golden):
    old, _ = golden
    assert list(old.columns) == ["activity", "unit", "kg_co2e", "scope", "category", "version"]


def test_loader_output_matches_golden(golden):
    old, _ = golden
    # Exact row set and order (dedup keeps the first diesel; blanks forward-fill).
    assert len(old) == len(EXPECTED_2025)
    for got, exp in zip(old.itertuples(index=False), EXPECTED_2025):
        assert got.activity == exp[0]
        assert got.unit == exp[1]
        assert got.kg_co2e == pytest.approx(exp[2])
        assert got.scope == exp[3]
        assert got.category == exp[4]
        assert got.version == "2025"


def test_loader_drops_duplicate_activity_unit(golden):
    old, _ = golden
    diesel = old[old["activity"] == "Liquid fuels - Diesel"]
    assert len(diesel) == 1
    assert diesel.iloc[0]["kg_co2e"] == pytest.approx(2.5)  # first wins, not 9.99


# --- Golden: exact diff output ------------------------------------------------
# key -> (pct_change or None, status, flagged). Thresholds: >5% Scope 1/2,
# >10% Scope 3. NaN pct for added/removed.
EXPECTED_DIFF = {
    ("Liquid fuels - Diesel", "litre"): (6.0, "changed", True),        # S1 >5 -> flagged
    ("Liquid fuels - Petrol", "litre"): (0.0, "unchanged", False),     # equal -> unchanged
    ("Gaseous fuels - Natural gas", "kwh"): (-2.7778, "changed", False),
    ("Gaseous fuels - Biogas", "kwh"): (None, "added", False),
    ("Solid fuels - Coal", "kg"): (None, "removed", False),
    ("Metal - Aluminium - Primary material production", "tonne"): (12.5, "changed", True),  # S3 >10
    ("Metal - Aluminium - Closed-loop source", "tonne"): (4.0, "changed", False),           # S3 <10
}


def test_diff_output_matches_golden(golden):
    old, new = golden
    d = diff_versions(old, new)
    got = {
        (r["activity"], r["unit"]): (r["pct_change"], r["status"], bool(r["flagged"]))
        for _, r in d.iterrows()
    }
    assert set(got) == set(EXPECTED_DIFF)
    for key, (pct, status, flagged) in EXPECTED_DIFF.items():
        g_pct, g_status, g_flagged = got[key]
        assert g_status == status, key
        assert g_flagged == flagged, key
        if pct is None:
            assert pd.isna(g_pct), key
        else:
            assert g_pct == pytest.approx(pct, abs=1e-3), key
