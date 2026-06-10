#!/usr/bin/env python3
"""
Price Badge Report — parallel runner.

Downloads for all dealers must happen before this script (via Playwright, one dealer at a time).
This script runs pb_report.py for each dealer simultaneously and aggregates a coordinator brief.

Usage:
    python3 ~/.claude/scripts/pb_parallel.py \
        --dealer hendrick --lei ~/.playwright-mcp/hendrick_lei.csv \
        --dealer nalley   --lei ~/.playwright-mcp/nalley_lei.csv --dem ~/.playwright-mcp/Pricing.csv \
        [--dealer dyer    --lei ~/.playwright-mcp/dyer_lei.csv --dem ~/.playwright-mcp/dyer_dem.csv] \
        [--no-draft] [--dry-run]

Options:
    --dry-run       True dry run: CSV parse + validate + stats + local email HTML.
                    Zero remote calls — no sheet writes, no drafts, no sends.
    --no-draft      Skip Gmail draft creation for all dealers
    --max-workers N Max parallel workers (default: number of dealers, capped at 4)
"""

import argparse, json, os, subprocess, sys, time, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = str(Path.home() / "Documents" / "scripts" / "pb_report.py")
VALIDATE = str(Path.home() / ".claude" / "scripts" / "validate_csv_schema.py")
STATE_DIR = Path.home() / ".claude" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

ANSI = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
    "cyan":   "\033[96m",
    "gray":   "\033[90m",
}

def c(color, text):
    return f"{ANSI[color]}{text}{ANSI['reset']}"


def validate_csv(schema: str, csv_path: str, dealer: str) -> bool:
    """Run validate_csv_schema.py. Returns True if schema OK."""
    result = subprocess.run(
        [sys.executable, VALIDATE, "--schema", schema, "--csv", csv_path,
         "--dealer", dealer, "--update-manifest"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, result.stdout + result.stderr
    return True, result.stdout


def run_dealer(dealer: str, lei_path: str, dem_path,
               no_draft: bool, dry_run: bool, stats_file: str) -> dict:
    """Run pb_report.py for one dealer. Returns a result dict."""
    t_start = time.monotonic()
    prefix = f"[{dealer.upper()}]"

    print(c("cyan", f"{prefix} Starting..."))

    # ── Validate CSVs before touching sheets ─────────────────────────────────
    print(c("gray", f"{prefix} Validating LEI CSV schema..."))
    ok, msg = validate_csv("lei_local_v2", lei_path, dealer)
    if not ok:
        elapsed = time.monotonic() - t_start
        print(c("red", f"{prefix} ✗ LEI schema validation failed ({elapsed:.1f}s)"))
        print(msg)
        return {
            "dealer": dealer, "ok": False,
            "error": "LEI schema mismatch — see output above",
            "elapsed": elapsed
        }
    print(c("green", f"{prefix} ✓ LEI schema OK"))

    if dem_path:
        ok, msg = validate_csv("dem_signal_price_comp", dem_path, dealer)
        if not ok:
            elapsed = time.monotonic() - t_start
            print(c("red", f"{prefix} ✗ Dem Signal schema validation failed ({elapsed:.1f}s)"))
            print(msg)
            return {
                "dealer": dealer, "ok": False,
                "error": "Dem Signal schema mismatch — see output above",
                "elapsed": elapsed
            }
        print(c("green", f"{prefix} ✓ Dem Signal schema OK"))

    # ── Build pb_report.py command ────────────────────────────────────────────
    cmd = [sys.executable, SCRIPT, "--dealer", dealer,
           "--lei", lei_path, "--json-stats", stats_file]
    if dem_path:
        cmd += ["--dem", dem_path]
    if no_draft:
        cmd.append("--no-draft")
    if dry_run:
        cmd.append("--dry-run")

    print(c("gray", f"{prefix} Running pb_report.py..."))

    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - t_start

    if result.returncode != 0:
        print(c("red", f"{prefix} ✗ pb_report.py failed ({elapsed:.1f}s)"))
        # Print last 20 lines of stdout+stderr for context
        output = (result.stdout + result.stderr).strip().splitlines()
        for line in output[-20:]:
            print(f"  {line}")
        return {"dealer": dealer, "ok": False, "error": "pb_report.py exited non-zero",
                "elapsed": elapsed, "stdout": result.stdout, "stderr": result.stderr}

    # Extract stats from JSON file
    stats = {}
    if os.path.exists(stats_file):
        try:
            stats = json.loads(open(stats_file).read())
        except Exception:
            pass

    print(c("green", f"{prefix} ✓ Complete ({elapsed:.1f}s)"))
    return {"dealer": dealer, "ok": True, "elapsed": elapsed, "stats": stats,
            "stdout": result.stdout}


def coordinator_brief(results: list, total_wall_clock: float, sequential_estimate: float):
    """Print a consolidated executive summary across all dealers."""
    print()
    print(c("bold", "━" * 64))
    print(c("bold", "  PRICE BADGE REPORT — COORDINATOR BRIEF"))
    print(c("bold", f"  {datetime.now().strftime('%A, %B %-d, %Y')}"))
    print(c("bold", "━" * 64))
    print()

    successful = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    # ── Per-dealer summary ────────────────────────────────────────────────────
    for r in results:
        dealer = r["dealer"].upper()
        if not r["ok"]:
            print(c("red", f"  ✗ {dealer}: FAILED — {r.get('error', 'unknown error')}"))
            continue

        s = r.get("stats", {})
        pct   = s.get("pct", "?")
        within = s.get("within_count", "?")
        total  = s.get("total", "?")
        great  = s.get("already_great", 0)
        draft  = s.get("draft_id", None)
        url    = s.get("sheet_url", "")

        print(c("green", f"  ✓ {dealer}") + f"  {pct} within badge range "
              f"({within}/{total} vehicles, {great} already Great)")
        if draft:
            print(c("gray", f"      Draft: {draft}"))
        if url:
            print(c("gray", f"      Sheet: {url}"))

        dem = s.get("dem_stats")
        if dem:
            print(c("gray", f"      Dem Signal: {dem['at_market_pct']}% At / "
                            f"{dem['above_market_pct']}% Above / "
                            f"{dem['under_market_pct']}% Under"))
        print()

    # ── Timing ───────────────────────────────────────────────────────────────
    print(c("bold", "  Timing:"))
    for r in results:
        status = c("green", "✓") if r["ok"] else c("red", "✗")
        print(f"    {status} {r['dealer']:<12} {r['elapsed']:.1f}s")
    print()
    print(f"  Wall clock (parallel):   {total_wall_clock:.1f}s")
    print(f"  Estimated sequential:    {sequential_estimate:.1f}s")
    savings = max(0, sequential_estimate - total_wall_clock)
    print(c("green" if savings > 0 else "gray",
            f"  Time saved:              {savings:.1f}s "
            f"({savings/sequential_estimate*100:.0f}%)" if sequential_estimate > 0 else ""))
    print()

    if failed:
        print(c("red", f"  ⚠ {len(failed)} dealer(s) failed — re-run individually to retry:"))
        for r in failed:
            print(c("red", f"    python3 ~/Documents/scripts/pb_report.py --dealer {r['dealer']} ..."))
        print()

    print(c("bold", "━" * 64))
    print()


# ── CLI ────────────────────────────────────────────────────────────────────────

class DealerAction(argparse.Action):
    """Collect (dealer, lei, dem) tuples from repeated --dealer/--lei/--dem flags."""
    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "dealers_raw") or namespace.dealers_raw is None:
            namespace.dealers_raw = []
        if option_string == "--dealer":
            namespace.dealers_raw.append({"name": values, "lei": None, "dem": None})
        elif option_string == "--lei":
            if not namespace.dealers_raw:
                parser.error("--lei must follow --dealer")
            namespace.dealers_raw[-1]["lei"] = values
        elif option_string == "--dem":
            if not namespace.dealers_raw:
                parser.error("--dem must follow --dealer")
            namespace.dealers_raw[-1]["dem"] = values


def main():
    p = argparse.ArgumentParser(
        description="Run Price Badge Report for multiple dealers in parallel"
    )
    p.add_argument("--dealer", action=DealerAction, metavar="NAME",
                   help="Dealer name (hendrick|nalley|dyer). Repeat for each dealer.")
    p.add_argument("--lei",   action=DealerAction, metavar="PATH",
                   help="LEI CSV path for the preceding --dealer")
    p.add_argument("--dem",   action=DealerAction, metavar="PATH",
                   help="Dem Signal CSV path for the preceding --dealer (optional)")
    p.add_argument("--no-draft", action="store_true")
    p.add_argument("--dry-run",  action="store_true",
                   help="True dry run — zero remote calls (no sheet writes, no drafts/sends)")
    p.add_argument("--max-workers", type=int, default=0,
                   help="Max parallel threads (default: one per dealer, capped at 4)")
    args = p.parse_args()

    dealers = getattr(args, "dealers_raw", None) or []
    if not dealers:
        p.print_help()
        sys.exit(1)

    for d in dealers:
        if not d["lei"]:
            p.error(f"--lei required for dealer '{d['name']}' (dry-run parses the CSV too)")

    max_workers = args.max_workers or min(len(dealers), 4)

    print()
    print(c("bold", f"Price Badge Report — Parallel Run — {len(dealers)} dealers"))
    print(c("gray", f"Workers: {max_workers}  |  Mode: {'dry-run' if args.dry_run else 'live'}"))
    print()

    # ── Create per-dealer temp files for JSON stats output ────────────────────
    stats_files = {d["name"]: tempfile.mktemp(suffix=f"_{d['name']}_stats.json")
                   for d in dealers}

    t_parallel_start = time.monotonic()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                run_dealer,
                d["name"],
                os.path.expanduser(d["lei"] or ""),
                os.path.expanduser(d["dem"]) if d["dem"] else None,
                args.no_draft,
                args.dry_run,
                stats_files[d["name"]],
            ): d["name"]
            for d in dealers
        }
        for future in as_completed(futures):
            results.append(future.result())

    total_elapsed = time.monotonic() - t_parallel_start

    # Clean up temp stats files
    for f in stats_files.values():
        if os.path.exists(f):
            os.unlink(f)

    # Sequential time estimate: sum of individual elapsed times
    sequential_estimate = sum(r["elapsed"] for r in results)

    # Save parallel run record to checkpoint
    run_record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dealers": [r["dealer"] for r in results],
        "results": results,
        "wall_clock": total_elapsed,
        "sequential_estimate": sequential_estimate,
    }
    run_path = STATE_DIR / "pb_parallel_last_run.json"
    run_path.write_text(json.dumps(run_record, indent=2, default=str))

    coordinator_brief(results, total_elapsed, sequential_estimate)

    # Exit non-zero if any dealer failed
    if any(not r["ok"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
