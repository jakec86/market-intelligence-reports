---
name: investigation-workflow
description: "Investigation triggers module + unified workflow skills built May 2026 — detection engine, Sonic/ACA wiring, prep brief, and investigate-stores unified command"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7d3fa2fd-5355-4a29-bab2-b9c230bc415a
---

# Investigation Workflow — May 2026

**Why:** Jake wanted playbook investigation scenarios (Drop in Connections, VDP Decrease, Demand Mismatch, etc.) auto-detected from Tableau data across all dealer groups, not just run manually per report.

**How to apply:** Use `/investigate-stores` as the front door for any scope. `/prep` for single-store pre-call briefs. Both feed from the same detection engine.

## Core Module

**`~/Documents/scripts/investigation_triggers.py`**
- Detects 5 playbook scenarios from Tableau CP/PP data
- Handles both Sonic (long-format, decimal deltas) and ACA (wide-format, percentage deltas) automatically — computes deltas from CP/PP to avoid format ambiguity
- `investigate_stores(stores_list)` → `{high, medium, bright_spots, clean}`
- `format_triage_report(results, title)` → printable triage
- CLI: `python3 investigation_triggers.py --group sonic`, `--ccids`, `--csv`

## Scenario Detection

| Scenario | Trigger |
|---|---|
| 1 — Drop in Connections | delta ≤ −10% HIGH, ≤ −5% MEDIUM |
| 2 — Best Match / Merch | under-merchandised % > 25% (i.e., minimally merch'd < 75%) |
| 3 — VDP Decrease | delta ≤ −10% HIGH, ≤ −5% MEDIUM |
| 4 — Demand Mismatch | inventory up ≥5% while VDPs down ≥5% |
| 5 — Cost/Lead outlier | > 1.5× group median HIGH, > 1.25× MEDIUM |

**Merch column direction:** "Avg Daily Pct Minimally Merchandised" = % of vehicles that DO have proper photos/content (high = good). Threshold fires when this is LOW.

## Skills Built

| Skill | What changed |
|---|---|
| `/sonic-monthly-report` Step 2 | Pivot now stores `Customer Name` + `Legacy Id` as canonical keys |
| `/sonic-monthly-report` Step 5 | Replaced manual weighted scoring with `investigate_stores()` call |
| `/sonic-monthly-report` Step 5b | Added Investigation Flags column to per-brand rollup |
| `/sonic-monthly-report` Step 6 | Deep dive now leads with scenario flags instead of re-diagnosing |
| `/aca-monthly-report` Step 4b | New step runs triage after CSV processing |
| `/aca-monthly-report` Step 6 | Email template adds Watch List + Standouts sections |
| `/prep` | New — 90-sec pre-call brief for any store: SF + Tableau + flags + DealerRater + 3 talking points |
| `/investigate-stores` | New — unified front door: any scope + --brief/--report/--triage/--export/--focus/--since |

## Key Paths

- Export dir: `~/Documents/Reports/InvestigationScans/`
- Prep briefs: `~/Documents/Reports/PrepBriefs/`
- Module: `~/Documents/scripts/investigation_triggers.py`
