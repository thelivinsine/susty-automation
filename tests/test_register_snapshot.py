"""
test_register_snapshot.py - the fast path around a 15 second cold start.

`pipeline.load_snapshot` is what lets section 1 paint in well under a second
instead of parsing two full-set DEFRA workbooks on every cold visit. Its one
job that matters more than speed: a snapshot that no longer matches the
workbooks on disk must NEVER be served as if it were current. Every failure
mode here (missing file, unreadable file, a changed workbook) has to come back
None, so the caller falls back to a live parse rather than showing a reader a
number that quietly went stale.

Run it on its own to SEE it round-trip:

    python tests/test_register_snapshot.py
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pipeline import compare_versions, load_snapshot, write_snapshot  # noqa: E402

SYNTH = os.path.join(ROOT, "data", "synthetic")
OLD = os.path.join(SYNTH, "defra_2025.xlsx")
NEW = os.path.join(SYNTH, "defra_2026.xlsx")


def test_round_trip_matches_a_fresh_parse(tmp_path):
    comparison = compare_versions(OLD, NEW, "2025", "2026")
    out_dir = write_snapshot(comparison, OLD, NEW, out_dir=str(tmp_path))
    assert out_dir == str(tmp_path)
    assert os.path.exists(os.path.join(tmp_path, "diff.parquet"))
    assert os.path.exists(os.path.join(tmp_path, "meta.json"))

    loaded = load_snapshot(OLD, NEW, snap_dir=str(tmp_path))
    assert loaded is not None
    assert loaded["diff_stats"] == comparison["diff_stats"]
    pd.testing.assert_frame_equal(
        loaded["diff_df"].reset_index(drop=True),
        comparison["diff_df"].reset_index(drop=True),
        check_like=True,
    )


def test_a_tampered_hash_is_refused_not_served_stale(tmp_path):
    comparison = compare_versions(OLD, NEW, "2025", "2026")
    write_snapshot(comparison, OLD, NEW, out_dir=str(tmp_path))

    meta_path = os.path.join(tmp_path, "meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta["new_sha256"] = "0" * 64  # the workbook on disk no longer matches this
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    assert load_snapshot(OLD, NEW, snap_dir=str(tmp_path)) is None


def test_a_workbook_that_moved_is_also_refused(tmp_path):
    # Same idea, the other direction: the recorded hash is right, but the file
    # load_snapshot is asked to check is a different one entirely.
    comparison = compare_versions(OLD, NEW, "2025", "2026")
    write_snapshot(comparison, OLD, NEW, out_dir=str(tmp_path))

    other_old = os.path.join(SYNTH, "defra_2026.xlsx")  # deliberately the wrong file
    assert load_snapshot(other_old, NEW, snap_dir=str(tmp_path)) is None


def test_missing_snapshot_directory_returns_none(tmp_path):
    empty_dir = os.path.join(str(tmp_path), "does-not-exist")
    assert load_snapshot(OLD, NEW, snap_dir=empty_dir) is None


def test_corrupt_meta_json_is_refused_not_raised(tmp_path):
    comparison = compare_versions(OLD, NEW, "2025", "2026")
    write_snapshot(comparison, OLD, NEW, out_dir=str(tmp_path))
    with open(os.path.join(tmp_path, "meta.json"), "w", encoding="utf-8") as f:
        f.write("not valid json{{{")
    assert load_snapshot(OLD, NEW, snap_dir=str(tmp_path)) is None


# ---- Guard on the COMMITTED snapshot ----------------------------------------
# If the real DEFRA workbooks and the committed snapshot both exist, the
# recorded hashes must still match them: a workbook update without rebuilding
# the snapshot (scripts/build_register_snapshot.py) would silently pin the app
# to a stale register. Hash comparison only, never a 15+ second recompute in
# the suite. Skips cleanly when the real workbooks aren't present (they are
# real DEFRA data, not committed to every checkout).
REAL_OLD = os.path.join(ROOT, "data", "ghg-conversion-factors-2025-full-set.xlsx")
REAL_NEW = os.path.join(ROOT, "data", "ghg-conversion-factors-2026-full-set.xlsx")


def test_the_committed_snapshot_matches_the_real_workbooks():
    if not (os.path.exists(REAL_OLD) and os.path.exists(REAL_NEW)):
        return  # no real workbooks in this checkout: nothing to guard
    from pipeline import snapshot_dir

    meta_path = os.path.join(snapshot_dir(), "meta.json")
    if not os.path.exists(meta_path):
        return  # snapshot not built yet: nothing to guard, not a failure

    loaded = load_snapshot(REAL_OLD, REAL_NEW)
    assert loaded is not None, (
        "data/register_snapshot/ no longer matches the real DEFRA workbooks. "
        "Run: python scripts/build_register_snapshot.py"
    )


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        test_round_trip_matches_a_fresh_parse(td)
        print("round trip: OK")
        test_a_tampered_hash_is_refused_not_served_stale(td + "/a")
        print("tampered hash refused: OK")
        test_a_workbook_that_moved_is_also_refused(td + "/b")
        print("wrong workbook refused: OK")
        test_missing_snapshot_directory_returns_none(td)
        print("missing directory: OK")
        test_corrupt_meta_json_is_refused_not_raised(td + "/c")
        print("corrupt meta.json refused: OK")
    test_the_committed_snapshot_matches_the_real_workbooks()
    print("committed snapshot guard: OK (or skipped, no real workbooks)")
    print("all checks passed")
