#!/usr/bin/env python3
"""Pre-flight check for the Dealer Health Dashboard.

Run before launching Streamlit to verify all dependencies are ready.
Usage: python3 ~/Documents/scripts/preflight_dealer_health.py
"""

import os
import subprocess
import sys
import urllib.request
import urllib.error

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []


def check(label: str, ok: bool, detail: str = ""):
    icon = PASS if ok else FAIL
    msg = f"{icon}  {label}"
    if detail:
        msg += f"\n     {detail}"
    print(msg)
    results.append(ok)


# ── 1. Chrome CDP ─────────────────────────────────────────────────────────────
try:
    with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as r:
        check("Chrome CDP reachable (localhost:9222)", True)
except Exception as e:
    check("Chrome CDP reachable (localhost:9222)", False,
          "Start Chrome with: open -a 'Google Chrome' --args --remote-debugging-port=9222")

# ── 2. admin.cars.com session ─────────────────────────────────────────────────
try:
    sys.path.insert(0, os.path.dirname(__file__))
    import admin_cars
    ok = admin_cars.check_session()
    check("admin.cars.com JumpCloud session active", ok,
          "" if ok else "Log in via JumpCloud SSO in the open Chrome window")
except Exception as e:
    check("admin.cars.com JumpCloud session active", False, str(e))

# ── 3. Claude CLI auth ────────────────────────────────────────────────────────
try:
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    r = subprocess.run(
        ["claude", "-p", "reply with exactly: pong", "--output-format", "text"],
        capture_output=True, text=True, timeout=30, env=env,
    )
    ok = r.returncode == 0 and bool(r.stdout.strip())
    check("Claude CLI auth (OAuth login)", ok,
          r.stderr[:200] if not ok else f"response: {r.stdout.strip()[:60]}")
except FileNotFoundError:
    check("Claude CLI auth (OAuth login)", False, "claude not found — check PATH")
except subprocess.TimeoutExpired:
    check("Claude CLI auth (OAuth login)", False, "timed out after 30s")

# ── 4. Salesforce CLI ─────────────────────────────────────────────────────────
SF_CLI = "/Users/jcrawley/.npm-global/bin/sf"
try:
    r = subprocess.run(
        [SF_CLI, "data", "query", "--query", "SELECT Id FROM Account LIMIT 1",
         "--json"],
        capture_output=True, text=True, timeout=20,
    )
    ok = r.returncode == 0
    check("Salesforce CLI auth", ok,
          "" if ok else f"Re-auth: sf org login web\n     {r.stderr[:200]}")
except FileNotFoundError:
    check("Salesforce CLI auth", False, f"sf CLI not found at {SF_CLI}")
except subprocess.TimeoutExpired:
    check("Salesforce CLI auth", False, "timed out after 20s")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passed = sum(results)
total = len(results)
if passed == total:
    print(f"All {total} checks passed — ready to run the dashboard.")
    print("  python3 -m streamlit run ~/Documents/scripts/dealer_health.py")
else:
    print(f"{passed}/{total} checks passed — fix the {FAIL} items above before running.")
    sys.exit(1)
