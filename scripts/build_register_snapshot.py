"""
build_register_snapshot.py - rebuild the committed front-door snapshot.

Section 1 of the app (the interactive comparison) used to parse two full-set
DEFRA workbooks on every cold visit: 15.3 seconds, measured, before a first-time
reader saw anything. This script does that parse ONCE, offline, and writes the
joined diff plus its provenance (which two workbook files, by hash) to
data/register_snapshot/. The app then loads that in well under a second and
falls back to a live parse only if the workbooks on disk no longer match the
hashes recorded here (pipeline.load_snapshot never serves a stale answer).

Run this whenever the DEFRA workbooks in data/ change (a new annual release, a
corrected file):

    python scripts/build_register_snapshot.py

Commit the two files it writes (data/register_snapshot/diff.parquet and
meta.json) alongside the workbooks.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from paths import resolve_paths                          # noqa: E402
from pipeline import compare_versions, write_snapshot     # noqa: E402


def main():
    p = resolve_paths()
    print(f"Workbooks: {os.path.basename(p['defra_old'])} -> "
          f"{os.path.basename(p['defra_new'])}"
          + ("" if p["using_real_data"] else "  (SYNTHETIC demo data)"))

    t0 = time.time()
    comparison = compare_versions(
        p["defra_old"], p["defra_new"], p["old_label"], p["new_label"]
    )
    parse_s = time.time() - t0

    t1 = time.time()
    out_dir = write_snapshot(comparison, p["defra_old"], p["defra_new"])
    write_s = time.time() - t1

    stats = comparison["diff_stats"]
    print(f"\nParsed and diffed in {parse_s:.1f}s, wrote snapshot in {write_s:.2f}s")
    print(f"  {out_dir}")
    print(f"  {stats['factors_old']:,} factors ({p['old_label']}), "
          f"{stats['factors_new']:,} ({p['new_label']}), "
          f"{stats['flagged']:,} past threshold, "
          f"{stats['relabels']:,} paired renames")
    print("\nSNAPSHOT BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
