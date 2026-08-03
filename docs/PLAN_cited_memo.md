# Plan: put the citations into the memo (VISION move #3, second half)

Design session output. Read this before building. The build session should be
able to execute from this doc without re-deriving anything.

Companion docs: `docs/VISION.md` (why this is the move), `docs/DECISIONS.md`
(D2 and D11 are the rules this must not break), `docs/PLAN_design_system.md`
(shipped the memo this plan writes into).

## What changed since this was first planned

VISION move #3 was "a dated, cited, printable memo". **The dated, printable memo
shipped** in D20's export pack (`src/export.py`, `to_print_html`): run id, generated
timestamp, client, product, operator, factor versions, mapping fingerprint,
coverage, and an unresolved-items checklist on the first page. That is real
provenance, and it is the harder half of "auditable a year later".

**The cited half did not ship.** This plan is only that half. It is smaller than
the original scope because the document, the design system, and the export
plumbing already exist.

## The problem in one sentence

The memo tells the client a change is "Cited" but never shows the citation, so
the one claim the reader most needs to check is the one they cannot.

## The specific gap

`_explanations_html` in `src/export.py` renders each flagged change with a green
**Cited** tag whenever `plain_english_reason` is not the verbatim `NO_REASON`
sentence, then prints the reason, the methodology note, and the target-impact
flag. It never prints what the reason was grounded in.

So the memo asserts groundedness without evidence. For a document a consultant
files under their own name, that is the wrong way round: the tag is the tool's
claim, and the quote is what makes the claim checkable. A reader cannot tell a
correctly grounded explanation from a wrongly grounded one, which matters
precisely because D11 exists to stop a wrong grounding, and D11's own gold set
proves wrong groundings were possible.

There is a second, quieter gap. Nothing in the memo says where a FACTOR came
from: which workbook, which sheet, which row. The consultant re-opening this in a
year has the mapping fingerprint (did the mapping change?) but no way to jump to
the source line.

## What "done" looks like

Every flagged change in the memo carries, next to its reason:

- The DEFRA wording it was grounded in, quoted verbatim, under its section
  heading, with the document it came from named ("Major Changes PDF" or the new
  workbook's "What's new" sheet).
- The factor's own source: workbook file, sheet, and row.
- Where a field genuinely does not exist, a plain statement that it does not,
  never a blank.

The existing "Not explained" path is untouched: `NO_REASON` stays verbatim and
still renders as the grey tag with no quote, because there is nothing to quote.

## The finding that shapes the build

**Most of the provenance a citation needs is not in the data.** This is not a
rendering job. Of the six fields:

| Field | Status today | Where it goes missing |
|---|---|---|
| Sheet name | **Have it** | `loader.py` keeps it as `category` |
| Source workbook file | Missing | `load_defra(path, ...)` knows the path but records nothing per row |
| Row number | Missing | `_parse_sheet` never records the row index it read |
| Verbatim DEFRA note | **Retrieved, then discarded** | `retrieve_passage` returns the text; `explain._finalize` returns three fields and drops it |
| Which document the note came from | Missing | `load_change_chunks` silently prefers the PDF, then the workbook sheet, and never records which won |
| DEFRA publication date | Missing | Nowhere in the pipeline |

A smaller defect blocks a clean citation too: `retrieve_passage` returns
`f"{title} {text}"` as one mashed string, so a citation cannot separate the
section heading from the quote.

## Why this respects the core rule (never silently guess)

A citation is a factual claim about a source, so D2 applies to it exactly as it
applies to a factor match:

- **Never construct a citation we did not read.** Every field is carried from the
  parse, never reconstructed or inferred downstream.
- **A missing field is stated, not omitted.** If the publication date is not in
  the source file, the memo prints that it is not stated, rather than dropping the
  line or filling in the version year.
- **The quote is verbatim or absent.** No summarizing, no ellipsis-trimming to
  fit the layout. If it is too long for the page, the print CSS handles it.
- **Retrieval date is the tool's own claim** (when we read the source) and is
  labelled as such, so it is never mistaken for DEFRA's publication date.

## The build, in 5 small steps

### Step 1: carry provenance out of the loader (`src/loader.py`)

Add three columns to the tidy table: `source_file` (basename, not the local
path), `source_sheet` (the sheet name, currently only duplicated into `category`),
and `source_row` (1-based spreadsheet row, so a human can open the file and land
on it).

For the builder: `_parse_sheet` already has the row index in hand when it appends
each record and simply does not record it. `drop_duplicates(keep="first")` runs
later and keeps whole rows, so a recorded row number stays correct.

Check it works: load a real workbook, print one row per sheet, open the xlsx at
that row and confirm it is the same activity. `tests/test_golden_loader.py` (D12)
pins the normalized output, so it will fail on the new columns and its fixture
needs updating in the same commit. That is the golden vector doing its job.

### Step 2: return the citation, not just the passage (`src/changes_pdf.py`)

Tag each chunk at build time with its `source` ("Major Changes PDF" or "What's new
sheet") and the file it came from, then have `retrieve_passage` return the chunk
(heading, body, source, score) instead of one concatenated string.

**Do not touch the matching logic.** D11 is locked: keyword overlap gates the
title fuzz, because letting title fuzz fire alone grounds a change in the WRONG
note. This step changes what is returned, never what is chosen.

Check it works: `scripts/eval_retrieval.py` still passes with no WRONG verdicts.

### Step 3: keep the quote through the explainer (`src/explain.py`)

`_finalize` returns three fields and drops `retrieved_text`. Add the citation to
the returned dict, passed straight through.

The grounding safety net stays exactly where it is: empty retrieved text still
forces the verbatim `NO_REASON`. This step must not touch that branch, and the
grounding trap test proves it did not.

### Step 4: render the citation (`src/export.py`, `src/ui/memo.css`)

In `_explanations_html`, add a citation block under the reason: the quoted DEFRA
wording, its section heading, the source document, and the factor's workbook,
sheet, and row. The "Cited" tag then labels something the reader can check.

Follow D20's rules rather than inventing styling: hue encodes epistemic status, so
a quote block is presentation, not a new colour meaning. Add the print styling to
`src/ui/memo.css` so it survives print-to-PDF, which is the whole delivery path.

The same citation should reach the `.json` artifact (it is the machine-readable
copy of the same run) and the `.xlsx` method sheet. The `.md` report can carry it
too, but that is the lowest-value surface and can follow.

### Step 5: extend the export-pack test (`tests/test_export_pack.py`)

Pin the citation into the rendered artifacts, in the spirit of D12: the test must
fail if a provenance field silently disappears, which is the exact regression that
would quietly turn a cited memo back into an uncited one wearing a green tag.

Two cases, minimum:
1. A change WITH a retrieved note renders the verbatim quote, its heading, and its
   source document.
2. A change with NO retrievable note renders the verbatim `NO_REASON` sentence,
   the grey tag, and no quote block at all.

## The publication-date question, decided

DEFRA's workbooks carry no clean machine-readable publication date. The decision,
in keeping with D2: read it only if the workbook states it in a cell we already
parse, and otherwise print that the source file does not state it. We do NOT infer
it from the version year, the filename, or the file's modification time. An
inferred date on a document a consultant files under their own name is exactly the
confident-looking guess this project exists to avoid.

## What we are deliberately NOT doing (so this stays small)

- No new memo, no new module, no second document. This writes into the memo D20
  shipped.
- No changes to the footprint maths, the matching, the diff, or the retrieval
  ranking. Steps 2 and 3 change what is RETURNED, never what is CHOSEN.
- No new AI call. Every field here already exists at some point in the run; the
  work is carrying it, not generating it.
- No PDF-generation library, for the reasons already settled in `src/export.py`.
- No per-line citation for BOM rows. The factor's source is the claim that needs
  backing; the user's own spreadsheet is not ours to cite.

## Order and effort

Steps 1 to 3 are the plumbing, best done together since they share one test run.
Step 4 is the visible work and is now much smaller than it would have been before
D20. Step 5 locks it. Heavy tier, one session.

The risk sits in step 1: real workbooks are irregular, and the row number has to
survive the super-header expansion, the forward-filled activity columns, and the
multi-block sheets.

## The one thing to validate first

Before touching any HTML, prove step 1 on a real workbook: pick five activities
across five different sheets, print their recorded file, sheet, and row, then open
the actual xlsx and confirm all five land on the right line. If the row numbers do
not survive the loader's parsing, that is the real work of this build, and it is
better to find it in the first hour than after the citation block is written.
