#!/usr/bin/env python3
"""
CSV schema validator — checks a downloaded CSV against the schema manifest
and proposes a patch to pb_report.py if drift is detected.

Usage:
    python3 validate_csv_schema.py --schema lei_local_v2 --csv /path/to/file.csv
    python3 validate_csv_schema.py --schema dem_signal_price_comp --csv /path/to/Pricing.csv
    python3 validate_csv_schema.py --update-manifest --schema lei_local_v2 --csv /path/to/file.csv --dealer hendrick
"""

import argparse, codecs, csv, io, json, sys, os
from datetime import date, datetime, timezone
from pathlib import Path

MANIFEST_PATH = Path.home() / ".claude" / "state" / "csv-schema-manifest.json"
SCRIPT_PATH   = Path.home() / "Documents" / "scripts" / "pb_report.py"


def read_csv_auto(path: str) -> list:
    raw = open(path, "rb").read(4)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = codecs.open(path, encoding="utf-16").read()
    else:
        text = open(path, encoding="utf-8-sig").read()
    first_line = text.split("\n", 1)[0]
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"✗ Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict):
    manifest["last_updated"] = date.today().isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def validate(schema_name: str, csv_path: str, verbose: bool = True) -> dict:
    manifest = load_manifest()
    if schema_name not in manifest["schemas"]:
        print(f"✗ Unknown schema '{schema_name}'. Available: {list(manifest['schemas'].keys())}")
        sys.exit(1)

    schema = manifest["schemas"][schema_name]
    rows = read_csv_auto(csv_path)

    if not rows:
        return {"ok": False, "error": "CSV is empty", "actual": [], "missing": [], "new_cols": []}

    actual = [str(c).strip() for c in rows[0]]
    expected = schema["expected_columns"]
    required = schema["minimum_required"]
    critical = schema.get("critical_positions", {})

    missing_required = [c for c in required if c not in actual]
    new_cols = [c for c in actual if c not in expected]
    removed_cols = [c for c in expected if c not in actual]

    position_errors = []
    for pos_str, col_name in critical.items():
        pos = int(pos_str)
        actual_at_pos = actual[pos] if pos < len(actual) else "<missing>"
        if actual_at_pos.strip() != col_name:
            position_errors.append({
                "position": pos,
                "expected": col_name,
                "actual": actual_at_pos,
            })

    ok = len(missing_required) == 0 and len(position_errors) == 0

    result = {
        "ok": ok,
        "schema": schema_name,
        "csv_path": csv_path,
        "row_count": len(rows) - 1,
        "actual_columns": actual,
        "expected_columns": expected,
        "missing_required": missing_required,
        "new_cols": new_cols,
        "removed_cols": removed_cols,
        "position_errors": position_errors,
    }

    if verbose:
        _print_report(result, schema)

    return result


def _print_report(result: dict, schema: dict):
    print(f"\n{'─'*60}")
    print(f"Schema validation: {result['schema']}")
    print(f"CSV: {result['csv_path']}")
    print(f"Rows: {result['row_count']}")
    print(f"{'─'*60}")

    if result["ok"]:
        print(f"✓ Schema OK — all required columns present")
        _record_run(result, schema)
    else:
        print(f"✗ Schema mismatch detected")
        if result["missing_required"]:
            print(f"\n  MISSING REQUIRED columns:")
            for c in result["missing_required"]:
                print(f"    - {c!r}")
        if result["position_errors"]:
            print(f"\n  WRONG POSITION:")
            for e in result["position_errors"]:
                print(f"    col[{e['position']}]: expected {e['expected']!r}, got {e['actual']!r}")

    if result["new_cols"]:
        print(f"\n  NEW columns (not in manifest):")
        for c in result["new_cols"]:
            print(f"    + {c!r}")

    if result["removed_cols"]:
        print(f"\n  REMOVED columns (were in manifest, gone now):")
        for c in result["removed_cols"]:
            print(f"    - {c!r}")

    if not result["ok"]:
        _propose_patch(result)


def _propose_patch(result: dict):
    """Print a proposed pb_report.py patch for the observed schema drift."""
    print(f"\n{'─'*60}")
    print(f"PROPOSED PATCH for pb_report.py")
    print(f"{'─'*60}")

    schema_name = result["schema"]

    if schema_name == "lei_local_v2":
        cols = result["actual_columns"]
        print(f"  Update _LEI_EXPECTED to match observed columns:")
        print(f"  Old: _LEI_EXPECTED = {[c for c in result['expected_columns'][:5]]}")
        print(f"  New: _LEI_EXPECTED = {cols[:5]}")
        if result["position_errors"]:
            print(f"\n  ⚠ Critical position mismatch — check col_reorder logic in DEALERS config")

    elif schema_name == "dem_signal_price_comp":
        cols = result["actual_columns"]
        print(f"  Update _DEM_EXPECTED to match observed columns:")
        print(f"  Old: _DEM_EXPECTED = {result['expected_columns']}")
        print(f"  New: _DEM_EXPECTED = {cols}")

    print(f"\n  Apply with: python3 validate_csv_schema.py --apply-patch --schema {schema_name} --csv {result['csv_path']}")
    print(f"{'─'*60}\n")


def apply_patch(schema_name: str, actual_columns: list):
    """Write the updated EXPECTED constants back to pb_report.py."""
    if not SCRIPT_PATH.exists():
        print(f"✗ pb_report.py not found at {SCRIPT_PATH}")
        sys.exit(1)

    source = SCRIPT_PATH.read_text()

    if schema_name == "lei_local_v2":
        old_line = next((l for l in source.splitlines() if l.startswith("_LEI_EXPECTED")), None)
        if old_line is None:
            print("✗ Could not find _LEI_EXPECTED in pb_report.py")
            sys.exit(1)
        new_line = f'_LEI_EXPECTED = {actual_columns[:5]}'
        new_source = source.replace(old_line, new_line, 1)

    elif schema_name == "dem_signal_price_comp":
        old_lines = []
        in_block = False
        for line in source.splitlines():
            if line.startswith("_DEM_EXPECTED"):
                in_block = True
            if in_block:
                old_lines.append(line)
                if line.endswith("]") or "]" in line:
                    break
        old_block = "\n".join(old_lines)
        new_block = f'_DEM_EXPECTED = {actual_columns}'
        new_source = source.replace(old_block, new_block, 1)

    else:
        print(f"✗ No patch logic defined for schema '{schema_name}'")
        sys.exit(1)

    SCRIPT_PATH.write_text(new_source)
    print(f"✓ Patched {SCRIPT_PATH}")

    # Update manifest
    manifest = load_manifest()
    manifest["schemas"][schema_name]["expected_columns"] = actual_columns
    manifest["patch_history"].append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "schema": schema_name,
        "new_columns": actual_columns,
    })
    save_manifest(manifest)
    print(f"✓ Manifest updated")


def _record_run(result: dict, schema: dict):
    """Record a successful run in the manifest's runs history (keeps last 10)."""
    manifest = load_manifest()
    runs = manifest["schemas"][result["schema"]].setdefault("runs", [])
    runs.append({
        "date": date.today().isoformat(),
        "row_count": result["row_count"],
        "columns_observed": result["actual_columns"],
        "source": "validation_pass",
    })
    manifest["schemas"][result["schema"]]["runs"] = runs[-10:]  # keep last 10
    save_manifest(manifest)


def update_manifest_from_run(schema_name: str, csv_path: str, dealer: str):
    """Record a new run in the manifest from a freshly downloaded CSV."""
    result = validate(schema_name, csv_path, verbose=True)
    if result["ok"]:
        manifest = load_manifest()
        runs = manifest["schemas"][schema_name].setdefault("runs", [])
        runs.append({
            "date": date.today().isoformat(),
            "dealer": dealer,
            "row_count": result["row_count"],
            "columns_observed": result["actual_columns"],
            "source": "manual_update",
        })
        manifest["schemas"][schema_name]["runs"] = runs[-10:]
        save_manifest(manifest)
        print(f"✓ Manifest updated with run from {dealer}")
    else:
        print(f"✗ Schema mismatch — manifest NOT updated. Fix drift first.")
        sys.exit(1)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Validate PB Report CSVs against the schema manifest")
    p.add_argument("--schema", required=True, choices=["lei_local_v2", "dem_signal_price_comp"],
                   help="Schema to validate against")
    p.add_argument("--csv", required=True, help="Path to the CSV file to validate")
    p.add_argument("--dealer", default="unknown", help="Dealer name (for manifest recording)")
    p.add_argument("--update-manifest", action="store_true",
                   help="Record this run in the manifest (only on validation pass)")
    p.add_argument("--apply-patch", action="store_true",
                   help="Apply the proposed patch to pb_report.py (requires --schema and --csv)")
    args = p.parse_args()

    if args.apply_patch:
        result = validate(args.schema, args.csv, verbose=False)
        apply_patch(args.schema, result["actual_columns"])
    elif args.update_manifest:
        update_manifest_from_run(args.schema, args.csv, args.dealer)
    else:
        result = validate(args.schema, args.csv)
        sys.exit(0 if result["ok"] else 1)
