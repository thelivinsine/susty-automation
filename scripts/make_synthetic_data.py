"""
make_synthetic_data.py — generate CLEARLY-LABELLED SYNTHETIC data so the whole
pipeline runs end-to-end without the real (gov.uk) DEFRA files.

It writes, into data/synthetic/:
  - defra_2025.xlsx, defra_2026.xlsx  (DEFRA-shaped workbooks: title rows, a
    'Scope' header, forward-fill-able Level columns, a 'kg CO2e' column)
  - changes_2026.pdf                  (a 'major changes' report that explains
    SOME of the moved factors, not all — so the grounding trap test is real)
  - sample_bom.csv                    (a synthetic product bill-of-materials)

THESE NUMBERS ARE INVENTED. They are shaped like DEFRA data for testing only and
must never be presented as real emission factors. Drop real workbooks at
data/defra_2025.xlsx etc. to use genuine figures.
"""

from __future__ import annotations

import os
import csv
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "synthetic")

# (sheet, scope, level1, level2, level3, level4, column_text, unit, kg_2025, kg_2026)
FACTORS = [
    # Fuels — Scope 1
    ("Fuels", "Scope 1", "Gaseous fuels", "Natural gas", "", "", "", "kwh", 0.18320, 0.18210),
    ("Fuels", "Scope 1", "Liquid fuels", "Diesel (average biofuel blend)", "", "", "", "litre", 2.5100, 2.6620),  # +6.1% flagged
    ("Fuels", "Scope 1", "Liquid fuels", "Petrol (average biofuel blend)", "", "", "", "litre", 2.3400, 2.3490),
    # UK electricity — Scope 2
    ("UK electricity", "Scope 2", "UK electricity", "Electricity generated", "", "", "", "kwh", 0.20700, 0.22510),  # +8.7% flagged
    # Material use — Scope 3
    ("Material use", "Scope 3", "Metal", "Aluminium", "Primary material production", "", "", "tonne", 12500.0, 14200.0),  # +13.6% flagged
    ("Material use", "Scope 3", "Plastic", "Average plastics", "Primary material production", "", "", "tonne", 3120.0, 3450.0),  # +10.6% flagged (NO reason in PDF -> trap)
    ("Material use", "Scope 3", "Paper", "Board", "Primary material production", "", "", "tonne", 820.0, 900.0),  # +9.8% NOT flagged (<10%)
    ("Material use", "Scope 3", "Glass", "Glass", "Primary material production", "", "", "tonne", 850.0, 861.0),
    # Water supply — Scope 3
    ("Water supply", "Scope 3", "Water supply", "Water supply", "", "", "", "cubic metre", 0.17700, 0.14900),  # -15.8% flagged (NO reason -> gap)
    # Freighting goods — Scope 3
    ("Freighting goods", "Scope 3", "HGV (all diesel)", "Rigid (>7.5t-17t)", "50% laden", "", "", "tonne.km", 0.10700, 0.10850),
]

# Which moved factors the "major changes" report explains, and the stated reason.
CHANGE_REASONS = {
    "Electricity generated": (
        "The UK grid average electricity factor increased by around 9%. The 2026 "
        "update reflects a higher share of natural gas generation in the 2024 "
        "generation mix used as the basis for the factor, together with a "
        "methodology refresh aligning transmission and distribution losses with "
        "the latest DUKES data."
    ),
    "Diesel (average biofuel blend)": (
        "The diesel factor rose by about 6%. This reflects a reduction in the "
        "average biofuel content of forecourt diesel under the revised Renewable "
        "Transport Fuel Obligation blend for the reporting year, which raises the "
        "fossil carbon intensity per litre."
    ),
    "Aluminium": (
        "Primary aluminium increased by roughly 14% following an update to the "
        "upstream electricity intensity used for smelting in the underlying life "
        "cycle inventory, reflecting a less decarbonised assumed power mix."
    ),
    # NOTE: 'Average plastics' and 'Water supply' are deliberately NOT explained
    # here, so the AI grounding trap test has a real 'no reason found' case.
}


def _write_workbook(path: str, year_index: int) -> None:
    """year_index: 0 -> use kg_2025 column, 1 -> use kg_2026 column."""
    wb = Workbook()
    wb.remove(wb.active)

    # group factors by sheet
    sheets: dict[str, list] = {}
    for row in FACTORS:
        sheets.setdefault(row[0], []).append(row)

    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(title=sheet_name[:31])
        # DEFRA-style junk/title rows above the header
        ws.append([f"{sheet_name} — Government conversion factors (SYNTHETIC)"])
        ws.append([f"GHG Conversion Factors {2025 + year_index} — for testing only"])
        ws.append([])
        # header row (loader anchors on the 'Scope' cell)
        ws.append(
            ["Scope", "Level 1", "Level 2", "Level 3", "Level 4",
             "Column Text", "UOM", "kg CO2e"]
        )
        prev_scope = prev_l1 = None
        for (_s, scope, l1, l2, l3, l4, coltext, unit, kg25, kg26) in rows:
            kg = (kg25, kg26)[year_index]
            # forward-fill emulation: blank out repeated Scope / Level 1 cells
            scope_cell = "" if scope == prev_scope else scope
            l1_cell = "" if (l1 == prev_l1 and scope == prev_scope) else l1
            ws.append([scope_cell, l1_cell, l2, l3, l4, coltext, unit, kg])
            prev_scope, prev_l1 = scope, l1

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)


def _write_changes_pdf(path: str) -> None:
    """Write a small 'major changes' report PDF from the CHANGE_REASONS above."""
    # We build a minimal valid PDF by hand-writing text via reportlab if present,
    # else via a tiny raw-PDF fallback, so we don't add a heavy dependency.
    lines = [
        "DEFRA / DESNZ GHG Conversion Factors 2026",
        "Major changes report (SYNTHETIC — for testing only)",
        "",
        "This document summarises the most significant changes to conversion",
        "factors for the 2026 update relative to 2025.",
        "",
    ]
    for key, reason in CHANGE_REASONS.items():
        lines.append(f"Change: {key}")
        # wrap the reason to ~90 chars for readability
        words, cur = reason.split(), ""
        for w in words:
            if len(cur) + len(w) + 1 > 90:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            lines.append(cur)
        lines.append("")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 60
        for ln in lines:
            if y < 60:
                c.showPage()
                y = height - 60
            c.setFont("Helvetica", 11)
            c.drawString(50, y, ln[:110])
            y -= 16
        c.save()
    except Exception:
        _write_raw_pdf(path, lines)


def _write_raw_pdf(path: str, lines: list[str]) -> None:
    """Dependency-free minimal single-page PDF writer (text only)."""
    def esc(s: str) -> str:
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    text_ops = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for i, ln in enumerate(lines):
        text_ops.append(f"({esc(ln[:110])}) Tj")
        text_ops.append("T*")
    text_ops.append("ET")
    content = "\n".join(text_ops).encode("latin-1", "replace")

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objs.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n0 %d\n" % (len(objs) + 1)
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objs) + 1)
    pdf += b"startxref\n%d\n%%%%EOF" % xref_pos
    with open(path, "wb") as f:
        f.write(pdf)


def _write_sample_bom(path: str) -> None:
    """A synthetic product: a reusable aluminium water bottle (with packaging)."""
    rows = [
        ("line_item", "quantity", "unit"),
        ("Aluminium, primary production", 0.00025, "tonne"),   # -> Aluminium (flagged)
        ("Average plastics", 0.00010, "tonne"),                # -> Average plastics (flagged, NO reason -> trap)
        ("Paper and board", 0.00005, "tonne"),                 # -> Board (not flagged)
        ("Electricity generated, UK grid", 3.5, "kwh"),        # -> Electricity generated (flagged)
        ("Diesel, average biofuel blend", 0.40, "litre"),      # -> Diesel (flagged)
        ("Water supply", 0.02, "cubic metre"),                 # -> Water supply (flagged, NO reason)
        ("Proprietary sealant compound (custom)", 0.00002, "tonne"),  # -> UNMATCHED (needs_review)
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    _write_workbook(os.path.join(OUT, "defra_2025.xlsx"), year_index=0)
    _write_workbook(os.path.join(OUT, "defra_2026.xlsx"), year_index=1)
    _write_changes_pdf(os.path.join(OUT, "changes_2026.pdf"))
    _write_sample_bom(os.path.join(OUT, "sample_bom.csv"))
    print("Wrote synthetic data to", OUT)
    for name in sorted(os.listdir(OUT)):
        print("  -", name)


if __name__ == "__main__":
    main()
