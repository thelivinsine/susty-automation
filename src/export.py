"""
export.py - the four artifacts a consultant actually hands over.

One run produces four files, all stamped with the SAME run id:

    .xlsx   movers, the full mapping, the review log, and a method sheet
    .json   the whole result, for a machine or next year's diff
    .md     the existing Markdown report, with a provenance header
    .html   a print-ready memo, which is how a client-ready PDF ships

WHY HTML AND NOT PDF. The audit asked for a PDF. pdfplumber only READS PDFs, and
CLAUDE.md rules out anything heavyweight, which is reportlab and weasyprint both.
docs/VISION.md settled it: a print-ready HTML memo that the user prints to PDF
from the browser. That respects the no-heavy-dependencies rule and still puts a
real document in the client folder. A generated PDF binary would be a new
dependency decision, to be taken on its own merits.

NOTHING IS PERSISTED. run_identity() builds a dict in memory and hands it to the
formatters. There is no database, no run history and no file written by this
module, so the no-database rule holds.

THE CHECKLIST IS THE POINT. completeness_checklist() lists what is still
unresolved, and every artifact carries the unresolved items in its front matter.
The consultant can always ship. They can never ship silently: if three lines were
held for review, the client's copy says so on its first page.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

import pandas as pd

from explain import NO_REASON
from report import build_markdown_report
from ui import stylesheet_text
from ui.components import esc
from ui.format import direction, sig_figs, signed, signed_pct

# Coverage at or above this is treated as a complete answer. Kept here as well as
# in app.py so an export is judged by the same bar the screen used.
COVERAGE_BAR = 95.0


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def mapping_hash(matched_df):
    """A stable fingerprint of "which BOM line became which DEFRA activity".

    This is the thing worth comparing between years. If the hash is unchanged,
    last year's mapping decisions still stand and only the factors moved. If it
    changed, someone re-matched something and the comparison needs a second look.
    """
    pairs = sorted(
        f"{row['line_item']}=>{row['matched_activity'] or ''}"
        for _, row in matched_df.iterrows()
    )
    return hashlib.sha256("\n".join(pairs).encode("utf-8")).hexdigest()[:12]


def run_identity(results, client=None, product=None, operator=None, generated_utc=None):
    """Describe this run well enough that someone could audit it a year later.

    The run id is hashed from the INPUTS, not from the clock, so re-running the
    same analysis over the same data gives the same id. That is deliberate: it
    means a changed id is evidence that something about the run actually changed.
    """
    summary = results["summary"]
    labels = results["labels"]
    stats = results.get("diff_stats") or {}
    fingerprint = mapping_hash(results["matched_df"])

    seed = "|".join(str(part) for part in [
        labels["old"],
        labels["new"],
        fingerprint,
        stats.get("factors_old"),
        stats.get("factors_new"),
        summary["total_old"],
        summary["total_new"],
        client or "",
        product or "",
    ])
    run_id = "RUN-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8].upper()

    stamp = generated_utc or datetime.now(timezone.utc)
    review = results["matched_df"]["needs_review"]

    return {
        "run_id": run_id,
        "generated_utc": stamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "client": client or "not stated",
        "product": product or "not stated",
        "operator": operator or "not stated",
        "version_old": labels["old"],
        "version_new": labels["new"],
        "factors_old": stats.get("factors_old"),
        "factors_new": stats.get("factors_new"),
        "factors_in_both_years": stats.get("joined"),
        "flagged_movers": stats.get("flagged"),
        "mapping_hash": fingerprint,
        "coverage_pct": summary["coverage_pct"],
        "lines_total": summary["lines_total"],
        "lines_included": summary["lines_included"],
        "unresolved_review": int(review.sum()),
        "total_old": summary["total_old"],
        "total_new": summary["total_new"],
        "pct_delta": summary["pct_delta"],
    }


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------

def completeness_checklist(results, set_aside=None):
    """What is still open, in the words a reviewer would use.

    Every item is either resolved or it is written into the front matter of all
    four artifacts. There is no way to export a clean-looking document over an
    unresolved run.
    """
    matched = results["matched_df"]
    review = matched[matched["needs_review"]]
    aside = list(set_aside or [])
    coverage = results["summary"]["coverage_pct"]
    unexplained = [
        e for e in results.get("explanations") or []
        if e["plain_english_reason"].strip() == NO_REASON
    ]

    return [
        {
            "key": "every_line_matched",
            "label": "Every inventory line matched a DEFRA activity",
            "resolved": review.empty,
            "detail": (
                "All lines matched with confidence."
                if review.empty
                else f"{len(review)} line(s) held for review and excluded from the totals: "
                     + ", ".join(str(x) for x in review["line_item"].head(5))
            ),
        },
        {
            "key": "no_rows_set_aside",
            "label": "Every row of the uploaded file was readable",
            "resolved": not aside,
            "detail": (
                "No rows were set aside."
                if not aside
                else f"{len(aside)} row(s) skipped before matching, for a missing "
                     "item name, unit or quantity."
            ),
        },
        {
            "key": "coverage_at_bar",
            "label": f"Coverage reached the {COVERAGE_BAR:.0f}% bar",
            "resolved": coverage >= COVERAGE_BAR,
            "detail": f"Coverage {coverage}% of inventory lines.",
        },
        {
            "key": "changes_are_cited",
            "label": "Every explained change cites the DEFRA notes",
            "resolved": not unexplained,
            "detail": (
                "Every change carries an official reason."
                if not unexplained
                else f"{len(unexplained)} change(s) have no reason in the DEFRA notes, "
                     "and say so rather than guessing."
            ),
        },
    ]


def unresolved(checklist):
    """Just the open items, which is what the front matter carries."""
    return [item for item in checklist if not item["resolved"]]


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def to_json(results, identity, checklist):
    """The whole result as JSON, for a machine or for next year's comparison."""
    payload = {
        "run": identity,
        "completeness": checklist,
        "unresolved": [item["label"] for item in unresolved(checklist)],
        "summary": results["summary"],
        "diff_stats": results.get("diff_stats"),
        "explanations": results.get("explanations"),
        "relabel_explanations": results.get("relabel_explanations"),
        "movers": _records(results.get("top_delta")),
        "mapping": _records(results["matched_df"]),
        "review": _records(results["matched_df"][results["matched_df"]["needs_review"]]),
    }
    return json.dumps(payload, indent=2, default=str)


def to_markdown(results, identity, checklist):
    """The existing Markdown report, with provenance in front of it."""
    open_items = unresolved(checklist)
    lines = [
        f"<!-- {identity['run_id']} -->",
        "",
        f"**Run {identity['run_id']}**, generated {identity['generated_utc']}.",
        "",
        f"- Client: {identity['client']}",
        f"- Product: {identity['product']}",
        f"- Prepared by: {identity['operator']}",
        f"- Factor versions: {identity['version_old']} to {identity['version_new']}",
        f"- Mapping fingerprint: `{identity['mapping_hash']}`",
        f"- Coverage: {identity['coverage_pct']}% "
        f"({identity['lines_included']} of {identity['lines_total']} lines)",
        "",
    ]
    if open_items:
        lines.append("**Unresolved at export:**")
        lines.append("")
        for item in open_items:
            lines.append(f"- {item['label']}. {item['detail']}")
        lines.append("")
    else:
        lines.append("**Nothing was left unresolved at export.**")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + build_markdown_report(results)


def to_xlsx(results, identity, checklist):
    """A workbook: movers, the full mapping, the review log, and the method.

    Every sheet carries the run id in its first row, so a sheet that gets copied
    out of the workbook still says which run it came from.
    """
    matched = results["matched_df"]
    review = matched[matched["needs_review"]]

    method_rows = [{"Field": key.replace("_", " ").capitalize(), "Value": value}
                   for key, value in identity.items()]
    method_rows.append({"Field": "", "Value": ""})
    for item in checklist:
        method_rows.append({
            "Field": ("RESOLVED: " if item["resolved"] else "UNRESOLVED: ") + item["label"],
            "Value": item["detail"],
        })

    sheets = {
        "Movers": _frame(results.get("top_delta")),
        "Mapping": _frame(matched),
        "Review": _frame(review),
        "Method": pd.DataFrame(method_rows),
    }

    buffer = io.BytesIO()
    stamp = f"{identity['run_id']} generated {identity['generated_utc']}"
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False, startrow=2)
            writer.sheets[name].cell(row=1, column=1, value=stamp)
    return buffer.getvalue()


def to_print_html(results, identity, checklist):
    """A standalone, print-ready memo. No Streamlit, no external requests.

    Everything is expanded: a printed report has to contain the reasoning, not a
    row of closed drawers. Fonts are the system stack and the CSS is inlined, so
    the file makes zero network requests, which matters for a document holding a
    client's confidential inventory.
    """
    css = stylesheet_text(["tokens.css", "memo.css"])
    summary = results["summary"]
    labels = results["labels"]
    absolute = (summary["total_new"] or 0) - (summary["total_old"] or 0)
    way = direction(absolute)
    partial = summary["coverage_pct"] < COVERAGE_BAR

    parts = [
        "<!doctype html>",
        '<html lang="en" data-theme="auto"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>EF version memo {esc(identity['run_id'])}</title>",
        f"<style>{css}</style></head><body><main>",
        "<h1>Emission-factor version memo</h1>",
        _provenance_html(identity, checklist),
        _result_html(summary, labels, absolute, way, partial),
        _movers_html(results),
        _explanations_html(results),
        _review_html(results),
        "<footer>Generated by EF Version Explainer. Explanations are grounded "
        "strictly in the official DEFRA change notes. Where the notes are silent, "
        "the tool says so rather than inventing a reason. Factor matches below the "
        "confidence threshold are held for review and excluded from the totals, "
        "never guessed.</footer>",
        "</main></body></html>",
    ]
    return "".join(parts)


def export_pack(results, identity, checklist):
    """All four artifacts, keyed by file name, all carrying the same run id."""
    stem = f"ef_version_{identity['run_id'].lower().replace('-', '_')}"
    return {
        f"{stem}.md": to_markdown(results, identity, checklist),
        f"{stem}.json": to_json(results, identity, checklist),
        f"{stem}.html": to_print_html(results, identity, checklist),
        f"{stem}.xlsx": to_xlsx(results, identity, checklist),
    }


def to_zip(pack):
    """The pack as one download, because it is one action."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(pack.items()):
            archive.writestr(name, content)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# HTML pieces
# ---------------------------------------------------------------------------

def _provenance_html(identity, checklist):
    fields = [
        ("Run", identity["run_id"]),
        ("Generated", identity["generated_utc"]),
        ("Client", identity["client"]),
        ("Product", identity["product"]),
        ("Prepared by", identity["operator"]),
        ("Factor versions", f"{identity['version_old']} to {identity['version_new']}"),
        ("Mapping fingerprint", identity["mapping_hash"]),
        ("Coverage",
         f"{identity['coverage_pct']}% "
         f"({identity['lines_included']} of {identity['lines_total']} lines)"),
    ]
    rows = "".join(
        f"<dt>{esc(key)}</dt><dd>{esc(value)}</dd>" for key, value in fields
    )

    open_items = unresolved(checklist)
    if open_items:
        items = "".join(
            f"<li><strong>{esc(item['label'])}.</strong> {esc(item['detail'])}</li>"
            for item in open_items
        )
        tail = (
            '<div class="unresolved">'
            '<span class="tag yellow">Unresolved at export</span>'
            f"<ul>{items}</ul></div>"
        )
    else:
        tail = (
            '<div class="unresolved">'
            '<span class="tag green">Complete</span> '
            "Nothing was left unresolved at export.</div>"
        )
    return f'<div class="provenance"><dl>{rows}</dl>{tail}</div>'


def _result_html(summary, labels, absolute, way, partial):
    pct = summary["pct_delta"]
    if pct is None:
        words = "The change could not be computed."
    elif absolute:
        heavier = "heavier" if absolute > 0 else "lighter"
        words = (
            f"{way['word'].capitalize()} {abs(pct):.2f}%, "
            f"{sig_figs(abs(absolute), 3)} kg {heavier}."
        )
    else:
        words = "No change between the two versions."

    coverage_words = (
        f"Coverage {summary['coverage_pct']}%, below the {COVERAGE_BAR:.0f}% bar, "
        "so this total is incomplete and should be read as a partial answer."
        if partial
        else f"Coverage {summary['coverage_pct']}%, at or above the {COVERAGE_BAR:.0f}% bar."
    )

    glyph = (
        f'<span class="dir" aria-hidden="true">{way["glyph"]}</span> '
        if way["glyph"] else ""
    )
    return (
        '<div class="section"><div class="h2wrap"><h2>Result</h2></div>'
        f'<div class="panel{" panel--partial" if partial else ""}">'
        '<div class="lab">Product footprint</div>'
        f'<div class="fig tnum">{esc(sig_figs(summary["total_old"]))} to '
        f'{esc(sig_figs(summary["total_new"]))}</div>'
        f'<div class="sub">kg CO2e &nbsp; <span class="move tnum">{glyph}'
        # Two decimals so the headline figure and the sentence underneath agree.
        f'{esc(signed_pct(pct, 2) if pct is not None else "")}'
        f'<span class="visually-hidden">, {esc(way["word"])}</span></span></div>'
        f'<div class="base">{esc(words)} {esc(coverage_words)}</div></div>'
        f'<p class="caption">Recomputed from the same bill of materials under '
        f'{esc(labels["old"])} and {esc(labels["new"])}.</p></div>'
    )


def _movers_html(results):
    top = results.get("top_delta")
    if top is None or top.empty:
        return (
            '<div class="section"><div class="h2wrap"><h2>Movers</h2></div>'
            '<p class="empty">No computable movers.</p></div>'
        )

    head = (
        '<tr><th scope="col">Line item</th>'
        '<th scope="col" class="num">Factor (old)</th>'
        '<th scope="col" class="num">Factor (new)</th>'
        '<th scope="col" class="num">kg CO2e (old)</th>'
        '<th scope="col" class="num">kg CO2e (new)</th>'
        '<th scope="col" class="num">Change</th></tr>'
    )
    rows = []
    for _, row in top.iterrows():
        way = direction(row["line_delta"])
        glyph = (
            f'<span class="dir" aria-hidden="true">{way["glyph"]}</span> '
            if way["glyph"] else ""
        )
        rows.append(
            f'<tr><td>{esc(row["line_item"])}</td>'
            f'<td class="num">{esc(sig_figs(row["factor_old"]))}</td>'
            f'<td class="num">{esc(sig_figs(row["factor_new"]))}</td>'
            f'<td class="num">{esc(sig_figs(row["co2e_old"]))}</td>'
            f'<td class="num">{esc(sig_figs(row["co2e_new"]))}</td>'
            f'<td class="num">{glyph}{esc(signed(row["line_delta"]))}'
            f'<span class="visually-hidden">, {esc(way["word"])}</span></td></tr>'
        )
    return (
        '<div class="section"><div class="h2wrap"><h2>Movers</h2></div>'
        '<div class="table-scroll"><table>'
        "<caption>Your inventory lines, largest change first</caption>"
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div></div>"
    )


def _explanations_html(results):
    explanations = results.get("explanations") or []
    if not explanations:
        return (
            '<div class="section"><div class="h2wrap"><h2>Explanations</h2></div>'
            '<p class="empty">No flagged, footprint-relevant factor changes.</p></div>'
        )

    blocks = []
    for e in explanations:
        cited = e["plain_english_reason"].strip() != NO_REASON
        tag = (
            '<span class="tag green">Cited</span>'
            if cited
            else '<span class="tag grey">Not explained</span>'
        )
        impact = e.get("footprint_impact")
        rows = []
        if impact is not None:
            share = e.get("footprint_impact_pct")
            share_txt = f" ({share:+.1f}% of the total change)" if share is not None else ""
            rows.append(("Impact on your footprint",
                         f"{esc(signed(impact))} kg CO2e{esc(share_txt)}."))
        rows += [
            ("Why it changed", f"{tag} {esc(e['plain_english_reason'])}"),
            ("Methodology note", esc(e["methodology_note"])),
            ("Target impact", esc(e["target_impact_flag"])),
        ]
        body = "".join(
            f'<div class="row"><div class="key">{esc(key)}</div>'
            f'<div class="val">{value}</div></div>'
            for key, value in rows
        )
        blocks.append(
            f"<h3>{esc(e['activity'])} ({esc(e['scope'])}): "
            f"{esc(sig_figs(e['kg_co2e_old']))} to {esc(sig_figs(e['kg_co2e_new']))}, "
            f"{esc(signed_pct(e['pct_change']))}</h3>"
            f'<div class="kv">{body}</div>'
        )
    return (
        '<div class="section"><div class="h2wrap"><h2>Explanations</h2></div>'
        '<p class="caption">Ordered by how much each change moved this product\'s '
        "footprint. Grounded strictly in the DEFRA change notes.</p>"
        f"{''.join(blocks)}</div>"
    )


def _review_html(results):
    matched = results["matched_df"]
    review = matched[matched["needs_review"]]
    if review.empty:
        return (
            '<div class="section"><div class="h2wrap"><h2>Held for review</h2></div>'
            '<p class="empty">Every line matched with confidence.</p></div>'
        )

    rows = "".join(
        f'<tr><td>{esc(row["line_item"])}</td><td>{esc(row["unit"])}</td>'
        f'<td class="num">{esc(sig_figs(row["match_score"], 3))}</td></tr>'
        for _, row in review.iterrows()
    )
    return (
        '<div class="section"><div class="h2wrap"><h2>Held for review</h2></div>'
        '<p class="caption"><span class="tag yellow">Never guessed</span> '
        "These lines fell below the confidence threshold for an automatic match "
        "and are excluded from the totals. Guessing an emission factor would risk "
        "a wrong number, so the tool holds them for a human instead.</p>"
        '<div class="table-scroll"><table>'
        "<caption>Inventory lines held for review</caption>"
        '<thead><tr><th scope="col">Line item</th><th scope="col">Unit</th>'
        '<th scope="col" class="num">Best score</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div></div>"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frame(df):
    """A DataFrame that is safe to write, even when the source is None or empty."""
    if df is None:
        return pd.DataFrame()
    return df.copy()


def _records(df):
    if df is None or len(df) == 0:
        return []
    return json.loads(df.to_json(orient="records"))
