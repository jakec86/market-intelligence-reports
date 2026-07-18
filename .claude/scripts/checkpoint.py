#!/usr/bin/env python3
"""
Workflow checkpoint manager.

Usage (from Python):
    from checkpoint import Checkpoint
    cp = Checkpoint("hendrick-pb-report")
    cp.step("preflight", {"totp": True, "pat": True, "gmail": True})
    cp.step("lei_downloaded", {"path": "/Users/jcrawley/.playwright-mcp/lei.csv", "rows": 82})
    cp.fail("sheet_import", "Tableau 401 — RLS rejected PAT", kind="tableau-401")
    last = cp.last_good()

Usage (from shell — for hooks/scripts):
    python3 ~/.claude/scripts/checkpoint.py read hendrick-pb-report
    python3 ~/.claude/scripts/checkpoint.py clear hendrick-pb-report
"""

import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATE_DIR = Path.home() / ".claude" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


class Checkpoint:
    def __init__(self, workflow: str):
        self.workflow = workflow
        self.path = STATE_DIR / f"{workflow}.json"
        self._data = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except json.JSONDecodeError:
                pass
        return {"workflow": self.workflow, "steps": [], "status": "fresh", "started_at": _now()}

    def _save(self):
        self.path.write_text(json.dumps(self._data, indent=2))

    def step(self, name: str, data: dict = None):
        """Record a successfully completed step."""
        self._data["steps"].append({
            "name": name,
            "status": "ok",
            "ts": _now(),
            "data": data or {},
        })
        self._data["status"] = "in_progress"
        self._data["last_good"] = name
        self._save()
        return self

    def fail(self, name: str, message: str, kind: str = "unknown"):
        """Record a step failure with error classification."""
        self._data["steps"].append({
            "name": name,
            "status": "failed",
            "ts": _now(),
            "error": message,
            "kind": kind,
        })
        self._data["status"] = "failed"
        self._data["last_failure"] = {"step": name, "error": message, "kind": kind}
        self._save()
        return self

    def complete(self):
        """Mark the workflow as successfully completed."""
        self._data["status"] = "complete"
        self._data["completed_at"] = _now()
        self._save()
        return self

    def last_good(self) -> Optional[str]:
        """Return the name of the last successfully completed step."""
        return self._data.get("last_good")

    def last_failure(self) -> Optional[dict]:
        return self._data.get("last_failure")

    def get_step_data(self, step_name: str) -> dict:
        """Return data dict from a named step, or empty dict if not found."""
        for s in reversed(self._data.get("steps", [])):
            if s["name"] == step_name and s["status"] == "ok":
                return s.get("data", {})
        return {}

    def is_complete(self) -> bool:
        return self._data.get("status") == "complete"

    def clear(self):
        if self.path.exists():
            self.path.unlink()

    def summary(self) -> str:
        steps = self._data.get("steps", [])
        good = [s["name"] for s in steps if s["status"] == "ok"]
        bad = [s for s in steps if s["status"] == "failed"]
        lines = [
            f"Workflow:  {self.workflow}",
            f"Status:    {self._data.get('status')}",
            f"Started:   {self._data.get('started_at', '?')}",
            f"Completed: {', '.join(good) or 'none'}",
        ]
        if bad:
            lines.append(f"Failed:    {bad[-1]['name']} — {bad[-1]['error']}")
        return "\n".join(lines)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: checkpoint.py <read|clear|list> <workflow>")
        sys.exit(1)
    cmd, workflow = sys.argv[1], sys.argv[2]
    cp = Checkpoint(workflow)
    if cmd == "read":
        print(cp.summary())
    elif cmd == "clear":
        cp.clear()
        print(f"Cleared checkpoint for {workflow}")
    elif cmd == "list":
        for f in sorted(STATE_DIR.glob("*.json")):
            c = Checkpoint(f.stem)
            print(c.summary())
            print()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
