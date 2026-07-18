# Recovery Agent: CSV Schema Drift

Invoked when a script's `_validate_csv_headers()` or `_require_col()` detects that column names/positions don't match expected schema.

**Autonomy level: PARTIAL** — can auto-detect the mapping; human must confirm before data is written to any sheet.

---

## What This Failure Means

CSV schema drift happens when Tableau or admin.cars.com updates their export format without notice. Common causes:
- Column renamed (e.g., "Total SRP Imps" → "SRP Impressions")
- Column reordered (e.g., "Stock num" moved from position 2 to position 3)
- Column added or removed from the export
- Encoding change (UTF-8 vs UTF-16LE flip)

**This is a silent failure without the validation guards.** With them, the script aborts before writing bad data.

---

## Recovery Steps

### Step 1 — Read the actual CSV headers

```bash
python3 - <<'EOF'
import sys, codecs, csv, io

path = sys.argv[1] if len(sys.argv) > 1 else input("CSV path: ").strip()
raw = open(path, "rb").read(4)
if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
    text = codecs.open(path, encoding="utf-16").read()
else:
    text = open(path, encoding="utf-8-sig").read()
first = text.split("\n", 1)[0]
delim = "\t" if "\t" in first else ","
reader = csv.reader(io.StringIO(text), delimiter=delim)
header = next(reader)
for i, col in enumerate(header):
    print(f"  [{i}] {col!r}")
EOF
```

### Step 2 — Build the diff

Compare printed headers to the `EXPECTED_COLUMNS` constant in the failing script:

| Position | Expected | Actual | Match? |
|----------|----------|--------|--------|
| 0 | Dealer name | ... | ? |
| 1 | Dealer id | ... | ? |
| 2 | Stock num | ... | ? |

### Step 3 — Determine fix type

**Case A — Column renamed, same data:** Update the `_find_col` candidates list in the script. Example: add `"SRP Impressions"` to the candidates for `col_srps`. Then update `_LEI_EXPECTED` to match.

**Case B — Column reordered:** Check if `col_reorder` logic in `pb_report.py` needs updating, or if `_validate_csv_headers` `expected` list needs new ordering.

**Case C — Column missing:** The export no longer includes this metric. Decide: (a) skip this field with `""`, (b) source from a different report, or (c) halt and flag the gap.

### Step 4 — Confirm with user before proceeding

Output a summary table of the proposed mapping changes. Do NOT apply changes to the script or write to the sheet until the user confirms.

```
⚠️ CSV schema drift detected. Proposed mapping updates:
  pb_report.py: _LEI_EXPECTED[2] "Stock num" → "Stock Number"
  pb_report.py: _find_col col_srps — add candidate "SRP Impressions"

Confirm to apply and continue? (y/n)
```

### Step 5 — Apply and update constants

Once confirmed:
1. Edit the script to update `EXPECTED_COLUMNS` / `_find_col` candidates
2. Write the updated constants back
3. Resume from checkpoint at the CSV loading step

---

## Checkpoint Contract

On confirmed fix and resume: `cp.step("csv_schema_recovery", {"script": "<name>", "changes": [...]})`

On escalation (column truly missing): `cp.fail("csv_schema_recovery", "Column '<name>' removed from export — metric unavailable", kind="csv-column-missing")`
