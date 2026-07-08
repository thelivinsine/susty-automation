# Plan: make the tool work on a real user's spreadsheet

This is the one build that turns the tool from an impressive demo into something a
consultant opens every June (see `docs/VISION.md`, move #2). Written in plain
English, in small steps, each with a way to SEE it work, per the house rules.

## The problem in one sentence

Today the tool only accepts a perfectly clean file with exactly three columns
named `line_item`, `quantity`, `unit` (see `src/pipeline.py`, the
`pd.read_csv(bom_path)` line). A real client spreadsheet has weird column names
("Material", "Description", "Qty", "Amount", "UoM"), extra columns, blank cells,
and mixed-case units. Hand it today's tool and it either crashes or reads the
wrong column. So the differentiating value (working on YOUR real data) is exactly
what is missing.

## What "done" looks like

A consultant uploads their client's actual Excel or CSV file. The tool says "I
think your item column is 'Material', your quantity is 'Qty', your unit is 'UoM',
is that right?" with dropdowns they can correct. Nothing is guessed silently. Then
the rest of the pipeline (which already works) runs on their real data, and the
report leads with the changes that moved THEIR number the most.

## Why this respects the core rule (never silently guess)

The tool already refuses to guess an emission-factor match. We extend the same
honesty one step earlier, to the columns: if the tool is not confident which
column is which, it asks instead of guessing. A wrong column is just as damaging
as a wrong factor match, so it gets the same treatment.

---

## The build, in 4 small steps

### Step 1: a forgiving file reader (`src/ingest.py`, new)

A new function `load_inventory(file)` that:
- Reads either `.csv` or `.xlsx` (openpyxl is already installed, so no new
  dependency).
- Looks at the column headers and makes a best guess at which column is the item
  name, which is the quantity, and which is the unit, using a plain synonyms list
  (for example: "material", "item", "description", "activity", "component" all
  point to the item column; "qty", "quantity", "amount", "mass", "volume" point to
  quantity; "unit", "units", "uom" point to unit).
- Returns two things: the cleaned three-column table, AND a short "here is what I
  guessed and how sure I am" report.
- Rows with a blank quantity or a blank unit are flagged and set aside, never
  silently dropped or defaulted to zero.

**SEE it work:** a tiny script that loads a deliberately messy sample file and
prints "I mapped Material to item, Qty to quantity, UoM to unit" plus any rows it
set aside. Prints "INGEST OK".

### Step 2: a confirm-your-columns step in the app (`app.py`)

After the user uploads, before anything runs, the app shows three dropdowns
pre-filled with the tool's guesses:
- Item column: [Material ▾]
- Quantity column: [Qty ▾]
- Unit column: [UoM ▾]

The user glances, corrects if needed, clicks "Use these columns". This is the
"forgiving" part: it turns any messy file into the clean shape the existing
pipeline already handles. If the tool was confident, this is a one-second confirm;
if it was unsure, the dropdowns are empty and the user must choose.

**SEE it work:** launch the app, upload a messy file, see the guessed mapping,
correct one, and watch the report generate on the corrected data.

### Step 3: rank changes by impact on THIS user's footprint

Right now the report explains flagged factors in DEFRA's generic order. We already
compute each line's contribution to the footprint change (`line_delta` in
`src/recompute.py`). We connect the two: the report leads with the factor changes
that moved the user's OWN total the most, and shows an "impact on your footprint"
figure next to each one. A 3% move on the factor that is 60% of their footprint
matters more than a 40% move on something that is 0.1% of it. This is cheap once
Steps 1 to 2 exist, and it is the thing that makes the output feel like it is about
THEIR number, not a generic DEFRA changelog.

**SEE it work:** the demo report's top section now reads "Biggest impacts on your
footprint" ordered by real contribution, with a kg CO2e impact next to each.

### Step 4: a test with a deliberately messy file

A frozen test fixture: a small spreadsheet with awkward headers, a mixed-case unit
("KWh"), and one row with a missing quantity. The test asserts the tool maps the
columns correctly and sets the bad row aside rather than inventing a value. This
locks the behaviour so a future change cannot quietly break it.

**SEE it work:** `pytest` stays green and gains one test that proves the messy-file
path.

---

## What we are deliberately NOT doing (so this stays small)

- Not parsing BOMs out of PDFs or Word files. CSV and Excel only.
- Not auto-guessing a column mapping and running silently on it. Low confidence
  always asks the user.
- Not adding AI to the column-guessing. A plain synonyms list is enough and keeps
  it transparent and testable.
- Not touching the footprint maths or the no-guess factor matching. Those already
  work; this change only widens the front door.

## Order and effort

Step 1 is the real work (a focused session). Steps 2 to 4 are quick once Step 1
exists. Suggested to build Step 1, prove it on one real (or realistic) messy file,
then do 2 to 4 together. The dated printable memo (VISION move #3) is a separate,
later plan.

## The one thing to validate first

Before building any of this, get one real (anonymised) client inventory file from
a consultant you know, and look at its actual columns. The synonyms list in Step 1
should be seeded from real header names, not guessed. Ten minutes of looking at a
real file will make Step 1 correct the first time.
</content>
