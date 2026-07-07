"""
make_synthetic_data.py — generate CLEARLY-LABELLED SYNTHETIC data, shaped like
the REAL DEFRA "full set" workbook, so the whole pipeline runs end-to-end without
the real (gov.uk) files.

It writes into data/synthetic/:
  - defra_2025.xlsx, defra_2026.xlsx  — DEFRA-shaped workbooks: title/metadata
    rows, a 'Scope:' metadata cell, guidance text, an
    'Activity | <descriptor> | Unit | kg CO2e' table with forward-fill-able
    descriptor columns, and a multi-block 'Material use' sheet with a super-header
    (Primary / Closed-loop) — so the loader is exercised the same way it is on the
    real file.
  - changes_2026.pdf  — a 'major changes' report explaining SOME movers, not all
    (so the AI grounding trap test is real).
  - sample_bom.csv    — a synthetic product bill-of-materials.

THESE NUMBERS ARE INVENTED. They are shaped like DEFRA data for testing only and
must never be presented as real emission factors.
"""

from __future__ import annotations

import os
import csv
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "synthetic")

# Each sheet: name, scope, descriptor column headers, super-header block labels
# (one per kg CO2e column), and rows. A row is:
#   (activity_level, descriptor2, unit, [value_2025_per_block], [value_2026_per_block])
SHEETS = [
    {
        "name": "Fuels",
        "scope": "Scope 1",
        "descriptors": ["Activity", "Fuel"],
        "blocks": [""],  # single kg CO2e column
        "rows": [
            ("Gaseous fuels", "Natural gas", "kwh", [0.18320], [0.18210]),
            ("Liquid fuels", "Diesel (average biofuel blend)", "litre", [2.5100], [2.6620]),  # +6.1% flagged S1
            ("Liquid fuels", "Petrol (average biofuel blend)", "litre", [2.3400], [2.3490]),
        ],
    },
    {
        "name": "UK electricity",
        "scope": "Scope 2",
        "descriptors": ["Activity", "Country"],
        "blocks": [""],
        "rows": [
            ("Electricity generated", "Electricity: UK", "kwh", [0.20700], [0.22510]),  # +8.7% flagged S2
        ],
    },
    {
        "name": "Material use",
        "scope": "Scope 3",
        "descriptors": ["Activity", "Material"],
        "blocks": ["Primary material production", "Closed-loop source"],  # two kg CO2e cols
        "rows": [
            ("Metal", "Aluminium", "tonne", [12500.0, 500.0], [14200.0, 520.0]),   # +13.6% flagged S3
            ("Plastic", "Average plastics", "tonne", [3120.0, 1500.0], [3450.0, 1520.0]),  # +10.6% flagged (NO reason -> trap)
            ("Paper", "Board", "tonne", [820.0, 700.0], [900.0, 720.0]),           # +9.8% NOT flagged (<10%)
            ("Glass", "Glass", "tonne", [850.0, 800.0], [861.0, 805.0]),
        ],
    },
    {
        "name": "Water supply",
        "scope": "Scope 3",
        "descriptors": ["Activity", "Type"],
        "blocks": [""],
        "rows": [
            ("Water supply", "", "cubic metre", [0.17700], [0.14900]),  # -15.8% flagged S3 (NO reason -> gap)
        ],
    },
]

# The changes report explains SOME movers; plastics and water are deliberately left
# unexplained so the grounding trap test has a real "no reason found" case.
CHANGE_REASONS = {
    "Electricity generated": (
        "The UK grid average electricity factor changed by around 9%. The 2026 "
        "update reflects a revised generation mix in the year used as the basis "
        "for the factor, together with a methodology refresh aligning "
        "transmission and distribution losses with the latest data."
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
}


def _write_workbook(path: str, year_index: int) -> None:
    """year_index: 0 -> 2025 values, 1 -> 2026 values."""
    wb = Workbook()
    wb.remove(wb.active)
    year = 2025 + year_index

    for sh in SHEETS:
        ws = wb.create_sheet(title=sh["name"][:31])
        # Title + metadata rows, mirroring the real workbook's preamble.
        ws.append([f"{sh['name']} — Government conversion factors (SYNTHETIC)"])
        ws.append([sh["name"]])
        ws.append(["Index"])
        ws.append([])
        ws.append(["Emissions source:", sh["name"], "Factor set:", "Full set"])
        ws.append(["Scope:", sh["scope"], "Version:", 1, "Year:", year])  # loader reads scope here
        ws.append([])
        ws.append([f"{sh['name']} conversion factors {year} — for testing only"])
        ws.append(["Guidance"])
        ws.append(["● Synthetic guidance line — not real DEFRA text."])
        ws.append([])

        descriptors = sh["descriptors"]
        blocks = sh["blocks"]
        n_desc = len(descriptors)

        # Super-header row (block labels above each kg CO2e column) — only when
        # there is more than one block, matching the real multi-block sheets.
        if len(blocks) > 1:
            super_row = [None] * (n_desc + 1) + list(blocks)
            ws.append(super_row)

        # Header row: Activity | <descriptors...> | Unit | kg CO2e (x n_blocks)
        header = list(descriptors) + ["Unit"] + ["kg CO2e"] * len(blocks)
        ws.append(header)

        # Data rows, with forward-fill emulation (blank the first descriptor when
        # it repeats, like the real merged cells).
        prev_activity = None
        for (activity, desc2, unit, vals25, vals26) in sh["rows"]:
            vals = (vals25, vals26)[year_index]
            act_cell = "" if activity == prev_activity else activity
            row = [act_cell, desc2, unit] + list(vals)
            ws.append(row)
            prev_activity = activity

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)


def _write_changes_pdf(path: str) -> None:
    """Write a small 'major changes' report PDF from CHANGE_REASONS."""
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
        _, height = A4
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
    for ln in lines:
        text_ops.append(f"({esc(ln[:110])}) Tj")
        text_ops.append("T*")
    text_ops.append("ET")
    content = "\n".join(text_ops).encode("latin-1", "replace")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
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
    """A synthetic product mirroring the real-data sample (aluminium canned drink)."""
    rows = [
        ("line_item", "quantity", "unit"),
        ("Aluminium, primary production", 0.00025, "tonne"),        # -> Metal - Aluminium (flagged)
        ("Average plastics, primary production", 0.00010, "tonne"),  # -> Plastic - Average plastics (flagged, NO reason -> trap)
        ("Board, primary production", 0.00005, "tonne"),            # -> Paper - Board (not flagged)
        ("Electricity generated, UK", 3.5, "kwh"),                  # -> Electricity generated (flagged)
        ("Diesel (average biofuel blend)", 0.40, "litre"),          # -> Diesel (flagged)
        ("Water supply", 0.02, "cubic metre"),                      # -> Water supply (flagged, NO reason)
        ("Proprietary sealant compound (custom)", 0.00002, "tonne"),  # -> UNMATCHED (needs_review)
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)


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
