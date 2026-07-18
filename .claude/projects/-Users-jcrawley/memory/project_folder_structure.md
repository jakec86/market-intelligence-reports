---
name: Folder Structure & Download Defaults
description: Organized folder structure for scripts, reports, Tableau downloads, credentials, and reference docs. Use when creating new files or telling user where to save things.
type: project
originSessionId: d3bf650a-7583-410d-9f5a-71c01b71b16e
---
**Desktop must stay clean — no files.** If a file lands on the Desktop, move it to the appropriate Documents subfolder immediately. Only pinned folders/aliases are acceptable on the Desktop.

## Structure

| Path | Purpose |
|------|---------|
| `~/Documents/scripts/` | All Python automation scripts (`chat_app.py`, `test_prompt.py`, `lei_report.py`, `generate_market_report.py`, `cowork/`) |
| `~/Documents/templates/` | HTML report templates (e.g. `market_intelligence_template.html`) |
| `~/Documents/Reports/HamptonRoads/` | Generated market intelligence HTML reports |
| `~/Documents/Tableau/` | Tableau CSV downloads (e.g. `SearchVolumeByZipCode.csv`) |
| `~/Documents/Reference/` | PDFs and reference docs (e.g. Holiday Schedule) |
| `~/Documents/Reference/screenshots/` | Archived work-session screenshots, organized by project subfolder |
| `~/.claude/` | Credentials and tokens (`google_credentials.json`, MCP tokens) |

## Why:
User wants an organized Desktop with no loose files. Downloads and outputs should land in named folders, not the Desktop root.

## How to apply:
- New scripts → `~/Documents/scripts/`
- New report templates → `~/Documents/templates/`
- Generated reports/HTML output → `~/Documents/Reports/<market-or-dealer-name>/`
- Tableau/data downloads → `~/Documents/Tableau/`
- Credentials → `~/.claude/`
- Reference PDFs → `~/Documents/Reference/`
- **Screenshots from Playwright/Chrome DevTools** → `~/Documents/Reference/screenshots/<project>/` (NOT `~` or Desktop)
  - When taking screenshots during work sessions, always specify the full path (e.g. `~/Documents/Reference/screenshots/nalley/step1.png`)
  - The default screenshot path for MCP tools is `~` — this is what caused the 230+ loose PNGs. Always override with an explicit path.
