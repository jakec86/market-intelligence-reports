# validate-csv-schema — Reusable CSV Validation Skill

Validates a downloaded Tableau or admin.cars.com CSV against the stored schema manifest,
records the run, and proposes an auto-patch to pb_report.py if column drift is detected.

Invoke this before any Google Sheet write. It is a hard gate — do not proceed on failure.

---

## Quick Reference

```bash
# Validate LEI CSV
python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema lei_local_v2 \
    --csv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv \
    --dealer hendrick \
    --update-manifest     # records this run in the manifest on success

# Validate Demand Signal CSV
python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema dem_signal_price_comp \
    --csv ~/.playwright-mcp/Pricing.csv \
    --dealer nalley \
    --update-manifest

# Apply an auto-patch to pb_report.py after reviewing the proposed change
python3 ~/.claude/scripts/validate_csv_schema.py \
    --schema lei_local_v2 \
    --csv ~/.playwright-mcp/file.csv \
    --apply-patch
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Schema matches — safe to proceed with sheet import |
| 1 | Schema mismatch — ABORT. Review diff, confirm patch, then re-run |

---

## Drift Handling

On exit code 1, the script prints:
1. Which required columns are missing
2. Which critical positions are wrong
3. Any new/removed columns detected
4. A proposed `_LEI_EXPECTED` or `_DEM_EXPECTED` patch for `pb_report.py`

**Do not auto-apply the patch without reviewing it.** The patch shows the `--apply-patch` command — run that manually after confirming the mapping is correct.

---

## Manifest Location

`~/.claude/state/csv-schema-manifest.json`

The manifest tracks:
- `expected_columns` — what we expect from each export
- `minimum_required` — columns that must be present (hard stop if missing)
- `critical_positions` — specific index positions that must match (e.g., col[2] = "Stock num")
- `runs[]` — last 10 successful validations with observed columns + row counts

To view recent run history:
```bash
python3 -c "import json; m=json.load(open('~/.claude/state/csv-schema-manifest.json'.replace('~', __import__('os').path.expanduser('~'))));
[print(r) for r in m['schemas']['lei_local_v2']['runs'][-3:]]"
```

---

## Integration Points

This skill is called by:
- `/pb-report-parallel` — runs it for each dealer before any sheet write
- `/hendricks-pb-report` — calls it at Step 1, CSV schema validation section
- `/nalley-pb-report` — calls it for both LEI and Dem Signal CSVs
- `pb_parallel.py` — calls it automatically before spawning pb_report.py workers
