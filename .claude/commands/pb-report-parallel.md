# Price Badge Report — Parallel Multi-Dealer Workflow

Runs the full Price Badge Report for Hendrick, Nalley, and Dyer simultaneously.
The browser download phase is sequential (one Playwright session); the sheet import
+ sort + email phase runs in parallel via `pb_parallel.py`.

**Typical wall-clock: ~12–15 min total vs. ~22–28 min sequential.**

---

## Architecture

```
Phase 1 — Sequential (you + Claude, ~10–12 min)
  ├── Download Hendrick LEI CSV (Playwright)
  ├── Download Nalley LEI + Dem Signal CSVs (Playwright + admin.cars.com)
  └── Download Dyer LEI + Dem Signal CSVs (Playwright + admin.cars.com)

Phase 2 — Parallel (pb_parallel.py, ~2–3 min)
  ├── [Thread 1] Hendrick: validate → import → sort → stats → email
  ├── [Thread 2] Nalley:   validate → import → sort → stats → email
  └── [Thread 3] Dyer:     validate → import → sort → stats → email

Phase 3 — Coordinator Brief (instant)
  └── Aggregated stats table + timing comparison
```

---

## Step-by-Step

### Step 0 — Pre-flight

```bash
bash ~/.claude/scripts/check-totp-keychain.sh
bash ~/.claude/scripts/check-tableau-pat.sh
bash ~/.claude/scripts/verify-gmail-mcp.sh
```

Abort on any warning.

---

### Step 1 — Download: Hendrick LEI

Navigate: `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2`

- **DMA filter:** ALL
- **Maj Dealer Name filter:** Hendrick Automotive Group
- **Download → Crosstab → CSV**
- File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`
- Rename immediately: `mv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv ~/.playwright-mcp/hendrick_lei.csv`

---

### Step 2 — Download: Nalley LEI

Same Tableau URL, different filter:

- **Dealer Name filter:** Nalley Lexus Galleria - 109754 (see `/nalley-pb-report` for filter sequence)
- **Download → Crosstab → CSV**
- Rename: `mv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv ~/.playwright-mcp/nalley_lei.csv`

Then Demand Signals:
- Navigate: `https://admin.cars.com/dealers/156f9bb7-3c44-549c-b16b-0c3af73fdb1f/reports/demand_signals`
- Price Comparison tab → Download Crosstab → CSV
- File: `~/.playwright-mcp/Pricing.csv` → rename: `mv ~/.playwright-mcp/Pricing.csv ~/.playwright-mcp/nalley_dem.csv`

---

### Step 3 — Download: Dyer (if running)

Same Tableau LEI pattern for Dyer & Dyer Volvo Cars filter.
Rename to `~/.playwright-mcp/dyer_lei.csv` and `~/.playwright-mcp/dyer_dem.csv`.

---

### Step 4 — Validate CSVs (all dealers)

Run the schema validator for each CSV before starting the parallel phase.
If any fail, fix the drift before proceeding — do not pass bad CSVs to the parallel runner.

```bash
python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema lei_local_v2 --csv ~/.playwright-mcp/hendrick_lei.csv --dealer hendrick --update-manifest

python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema lei_local_v2 --csv ~/.playwright-mcp/nalley_lei.csv --dealer nalley --update-manifest

python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema dem_signal_price_comp --csv ~/.playwright-mcp/nalley_dem.csv --dealer nalley --update-manifest
```

On any exit code 1: review the diff, apply the proposed patch if correct, re-validate.

---

### Step 5 — Parallel run (Hendrick + Nalley)

```bash
python3 ~/.claude/scripts/pb_parallel.py \
    --dealer hendrick --lei ~/.playwright-mcp/hendrick_lei.csv \
    --dealer nalley   --lei ~/.playwright-mcp/nalley_lei.csv --dem ~/.playwright-mcp/nalley_dem.csv
```

Adding Dyer:

```bash
python3 ~/.claude/scripts/pb_parallel.py \
    --dealer hendrick --lei ~/.playwright-mcp/hendrick_lei.csv \
    --dealer nalley   --lei ~/.playwright-mcp/nalley_lei.csv --dem ~/.playwright-mcp/nalley_dem.csv \
    --dealer dyer     --lei ~/.playwright-mcp/dyer_lei.csv   --dem ~/.playwright-mcp/dyer_dem.csv
```

Dry-run — true zero-remote-calls verification (CSV parse + validate + stats +
email HTML written locally to `~/Documents/Reports/pb_dryrun_*.html`; no Google
auth, no sheet writes, no drafts, no sends):

```bash
python3 ~/.claude/scripts/pb_parallel.py \
    --dealer hendrick --lei ~/.playwright-mcp/hendrick_lei.csv \
    --dealer nalley   --lei ~/.playwright-mcp/nalley_lei.csv --dem ~/.playwright-mcp/nalley_dem.csv \
    --dry-run
```

> ⚠️ Do not confuse `--dry-run` with pb_report.py's `--stats-only`: stats-only
> still **mutates the live sheet** (rename, sort, hide tabs) and creates a Gmail
> draft. Dry-run stats are CSV-derived and may differ slightly from the live
> sheet's J1 formula.

---

### Step 6 — Review coordinator brief

The parallel runner prints a consolidated brief on completion:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PRICE BADGE REPORT — COORDINATOR BRIEF
  Monday, May 12, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ HENDRICK    62% within $500 of next badge (58/94 vehicles, 12 already Great)
      Draft: r8149203847
      Sheet: https://docs.google.com/...

  ✓ NALLEY      47% within $1,000 of next badge (24/51 vehicles, 8 already Great)
      Draft: r9203847182
      Dem Signal: 34% At / 22% Above / 44% Under
      Sheet: https://docs.google.com/...

  Timing:
    ✓ hendrick       142.3s
    ✓ nalley         168.7s

  Wall clock (parallel):   169.4s
  Estimated sequential:    311.0s
  Time saved:              141.6s (46%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step 7 — Review and send drafts

Open Gmail, locate each draft (IDs shown in brief), review, and send.

Nalley draft: add recipients per `/nalley-pb-report` Step 5 before sending.

---

## Failure Recovery

If one dealer fails in the parallel phase:

```bash
# Re-run just the failed dealer
python3 ~/Documents/scripts/pb_report.py \
    --dealer nalley \
    --lei ~/.playwright-mcp/nalley_lei.csv \
    --dem ~/.playwright-mcp/nalley_dem.csv
```

The other dealers are already complete — their drafts and sheet updates are unaffected.

---

## Timing Estimates

| Scenario | Time |
|---|---|
| 2 dealers, sequential | 22–28 min |
| 2 dealers, parallel (Phase 2 only) | 14–18 min |
| 3 dealers, sequential | 32–42 min |
| 3 dealers, parallel (Phase 2 only) | 16–20 min |

Phase 1 (browser downloads) is always sequential — the speedup is entirely in Phase 2.
The parallel run record is saved to `~/.claude/state/pb_parallel_last_run.json`.

---

## Manifest Updates

After three clean runs, the manifest will have accumulated real observed column sets.
Compare manifests vs. script constants with:

```bash
python3 -c "
import json
m = json.load(open('$(echo ~/.claude/state/csv-schema-manifest.json)'))
for schema, s in m['schemas'].items():
    print(f'{schema}: {len(s[\"runs\"])} runs on record')
    if s['runs']:
        print(f'  last: {s[\"runs\"][-1][\"date\"]} — {s[\"runs\"][-1][\"row_count\"]} rows')
"
```
