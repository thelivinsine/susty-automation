"""
check_citations.py - SEE the memo show its work.

The memo used to print a green "Cited" tag with nothing behind it, so a reader
had no way to tell a correct grounding from a wrong one. This script runs the
real pipeline on the real workbooks and prints, for every flagged change:

  - the factor's own source (workbook, sheet, row a human can scroll to), and
  - the DEFRA passage the explanation was grounded in, quoted, with its section
    heading and which document it came from.

Then it renders the print-ready memo and confirms the same evidence reached the
page, because carrying provenance in a dataframe is not the same as showing it.

Run:  python scripts/check_citations.py
Prints "CITATIONS OK" if every cited explanation can show its evidence.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from explain import NO_REASON  # noqa: E402
from export import completeness_checklist, run_identity, to_print_html  # noqa: E402
from paths import resolve_paths  # noqa: E402
from pipeline import run_pipeline  # noqa: E402


def main():
    p = resolve_paths()
    print(f"Workbooks: {os.path.basename(p['defra_old'])} -> "
          f"{os.path.basename(p['defra_new'])}\n")

    results = run_pipeline(
        defra_old_path=p["defra_old"],
        defra_new_path=p["defra_new"],
        changes_pdf_path=p["changes_pdf"],
        bom_path_or_df=p["bom"],
        old_label=p["old_label"],
        new_label=p["new_label"],
    )

    explanations = results.get("explanations") or []
    if not explanations:
        print("No flagged, footprint-relevant changes in this run, so nothing to "
              "cite. Not a failure, but this check proves nothing today.")
        return 0

    cited = uncited = 0
    for e in explanations:
        cite = e.get("citation") or {}
        note = cite.get("note")
        is_cited = e["plain_english_reason"].strip() != NO_REASON

        print(f"{e['activity']} ({e['scope']})")
        row = cite.get("factor_source_row")
        if cite.get("factor_source_file") and row:
            print(f"  factor : {cite['factor_source_file']}, "
                  f"sheet {cite['factor_source_sheet']!r}, row {row}")
        else:
            print("  factor : source not recorded")

        if is_cited and note:
            quote = note["quote"]
            print(f"  section: {note['heading'] or '(untitled)'}")
            print(f"  source : {note['source']} ({note['source_file']})")
            print(f"  quote  : \"{quote[:120]}{'...' if len(quote) > 120 else ''}\"")
            cited += 1
        elif is_cited:
            print("  PROBLEM: tagged as cited, but no passage was carried through")
            uncited += 1
        else:
            print(f"  not explained: {NO_REASON}")
        print()

    identity = run_identity(results, client="Check", product="Check")
    checklist = completeness_checklist(results)
    html = to_print_html(results, identity, checklist)

    in_page = html.count('class="cite"')
    print(f"Rendered memo: {in_page} citation block(s) on the page, "
          f"{cited} cited explanation(s) in the data.")

    if uncited:
        print("\nCITATIONS FAILED: a cited explanation could not show its evidence.")
        return 1
    if cited and in_page < cited:
        print("\nCITATIONS FAILED: evidence exists in the data but did not reach "
              "the page.")
        return 1

    print("\nCITATIONS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
