#!/usr/bin/env python3
"""
Skill hardening loop.

Runs pytest, finds failing skill-compliance tests, patches the offending
.md files, auto-commits, and repeats until all tests pass or MAX_ITERATIONS
is reached. Python unit test failures are reported as UNFIXABLE (require
manual intervention) and do not block the loop.

Usage:
    cd ~/Documents/scripts
    python3 harden_skills.py [--max-iterations N] [--dry-run]
"""

import argparse, json, re, subprocess, sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILLS_DIR  = Path.home() / ".claude/commands"
REPORT_FILE = SCRIPTS_DIR / ".harden_report.json"

# Skill test name -> patch spec
# Each patch spec has: skill_files, checks (test fn + patch fn + description)
SKILL_PATCHES = {
    "test_pb_skill_says_sort_range_not_sort_sheet": {
        "files": ["nalley-pb-report.md", "hendricks-pb-report.md"],
        "checks": [
            {
                "test":  lambda t: "sort range" in t.lower(),
                "patch": lambda t: t + "\n\n> **Sort range only** — never Sort sheet (moves header into data).\n",
                "desc":  "add sort-range guardrail",
            },
            {
                "test":  lambda t: "sort sheet" not in t.lower(),
                "patch": lambda t: re.sub(r"(?i)sort sheet", "Sort range", t),
                "desc":  "replace 'sort sheet' with 'Sort range'",
            },
        ],
    },
    "test_email_skill_specifies_html_not_plain_text": {
        "files": [
            "nalley-pb-report.md", "hendricks-pb-report.md",
            "sonic-monthly-report.md", "aca-monthly-report.md",
            "ep-review-report.md",
        ],
        "checks": [
            {
                "test":  lambda t: "html" in t.lower(),
                "patch": lambda t: t + "\n\n> **Email format:** Always use Content-Type: text/html.\n",
                "desc":  "add HTML email guardrail",
            },
            {
                "test":  lambda t: "plain text" not in t.lower(),
                "patch": lambda t: re.sub(r"(?i)plain text", "HTML", t),
                "desc":  "replace 'plain text' with 'HTML'",
            },
        ],
    },
}


def run_tests() -> dict:
    """Run full pytest suite and return the JSON report."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short",
            "--json-report", f"--json-report-file={REPORT_FILE}",
        ],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if not REPORT_FILE.exists():
        print("ERROR: pytest-json-report did not produce a report file.", file=sys.stderr)
        sys.exit(1)
    return json.loads(REPORT_FILE.read_text())


def get_failures(report: dict) -> list:
    return [t for t in report.get("tests", []) if t.get("outcome") == "failed"]


def parse_skill_file_from_nodeid(nodeid: str):
    """Extract parametrize value from nodeid like test_foo[nalley-pb-report.md]."""
    m = re.search(r'\[(.+\.md)\]', nodeid)
    return m.group(1) if m else None


def patch_skill_file(skill_file: str, patch_spec: dict, dry_run: bool) -> list:
    """Apply all failing patches to a skill .md file. Returns list of applied descriptions."""
    path = SKILLS_DIR / skill_file
    if not path.exists():
        print(f"  SKIP: {skill_file} not found at {path}")
        return []

    text = path.read_text()
    applied = []
    for check in patch_spec["checks"]:
        if not check["test"](text):
            if dry_run:
                print(f"  [dry-run] Would apply: {check['desc']} -> {skill_file}")
            else:
                text = check["patch"](text)
                applied.append(check["desc"])
                print(f"  Applied: {check['desc']} -> {skill_file}")

    if applied and not dry_run:
        path.write_text(text)

    return applied


def git_commit(files: list, message: str) -> bool:
    """Stage and commit a list of files. Returns True on success."""
    add = subprocess.run(["git", "add"] + [str(f) for f in files], capture_output=True)
    if add.returncode != 0:
        print(f"  git add failed: {add.stderr.decode()}")
        return False
    commit = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if commit.returncode != 0:
        print(f"  git commit failed: {commit.stderr}")
        return False
    print(f"  Committed: {message}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Skill hardening loop")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show proposed patches without applying them")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Skill Hardening Loop — max {args.max_iterations} iterations")
    if args.dry_run:
        print("DRY RUN — no files will be changed")
    print(f"{'='*60}\n")

    iteration_trace = []

    for iteration in range(1, args.max_iterations + 1):
        print(f"\n-- Iteration {iteration}/{args.max_iterations} --")

        report = run_tests()
        failures = get_failures(report)

        if not failures:
            print(f"\nAll tests pass after {iteration - 1} iteration(s).")
            break

        print(f"\n{len(failures)} failure(s):")
        patched_files = []
        commit_messages = []
        unfixable = []

        for failure in failures:
            nodeid = failure["nodeid"]
            test_name = nodeid.split("::")[-1].split("[")[0]
            skill_file = parse_skill_file_from_nodeid(nodeid)

            print(f"\n  FAIL: {nodeid}")

            if test_name in SKILL_PATCHES:
                spec = SKILL_PATCHES[test_name]
                files_to_patch = [skill_file] if skill_file else spec["files"]
                for fname in files_to_patch:
                    applied = patch_skill_file(fname, spec, args.dry_run)
                    if applied and not args.dry_run:
                        patched_files.append(SKILLS_DIR / fname)
                        commit_messages.append(f"fix(harness): {test_name} -> {fname}")
                        iteration_trace.append({
                            "iteration": iteration,
                            "test": nodeid,
                            "patches": applied,
                            "file": fname,
                        })
            else:
                msg = (
                    f"  UNFIXABLE by loop — Python unit test failure requires manual fix.\n"
                    f"  Run: python3 -m pytest '{nodeid}' -v  for details."
                )
                print(msg)
                unfixable.append(nodeid)
                iteration_trace.append({
                    "iteration": iteration,
                    "test": nodeid,
                    "patches": [],
                    "unfixable": True,
                })

        if patched_files and not args.dry_run:
            verify = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_skills_compliance.py", "-q"],
                cwd=SCRIPTS_DIR, capture_output=True, text=True,
            )
            if verify.returncode == 0:
                git_commit(patched_files, "; ".join(commit_messages))
            else:
                print("  Patches did not fix the tests — manual review needed.")
                print(verify.stdout)
                unfixable.extend([
                    f["test"] for f in iteration_trace
                    if f.get("iteration") == iteration and not f.get("unfixable")
                ])

        if not patched_files and unfixable:
            print(f"\nLoop cannot progress — {len(unfixable)} unfixable failure(s) remain.")
            break

        if args.dry_run:
            break

    else:
        print(f"\nReached max iterations ({args.max_iterations}) — some tests still failing.")

    print(f"\n{'='*60}")
    print("Iteration Trace")
    print(f"{'='*60}")
    for entry in iteration_trace:
        status = "UNFIXABLE" if entry.get("unfixable") else f"patched: {', '.join(entry['patches'])}"
        print(f"[{entry['iteration']}] {entry['test']}\n     -> {status}")


if __name__ == "__main__":
    main()
