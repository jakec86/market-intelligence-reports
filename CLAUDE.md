# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.9.6, `anthropic` 0.86.0, `streamlit` 1.50.0
- Claude Code authenticates via `claude.ai` login (run `/login`). No API key needed for the CLI.
- `ANTHROPIC_API_KEY` must be set for **Python scripts only** (`dealer_health.py`, `cowork.py`) — loaded from macOS Keychain via `.zshrc`

## MCP Server Health Check

At session start, verify required MCP servers are loaded (Tableau, Gmail, BigQuery, Confluence). If any show as disconnected or missing tools, immediately recommend `/mcp` check or session restart BEFORE starting workflow tasks. Never assume an MCP server will reconnect mid-workflow.

**If a server fails mid-workflow:**
- **Gmail fails:** Any in-progress drafts are not auto-saved — note where the workflow stopped and re-run from that step after reconnecting. Re-run is safe (draft creation is idempotent).
- **Tableau fails:** CSV/data pull must be re-run from scratch. Do not proceed with partial data.
- **Google Sheets fails:** Do not attempt manual sheet writes — re-run the full sheet population step after reconnect to avoid partial/corrupt rows.
- **Salesforce fails:** SF queries can be re-run safely; no write operations are performed in standard workflows.

## Pre-flight Checks for Workflow Commands

Before running any workflow that requires authentication (Price Badge Reports, ACA GM report, VPM report, etc.):

1. **Keychain TOTP** — verify the JumpCloud TOTP entry exists: `security find-generic-password -a jcrawley -s jumpcloud-totp -w`
2. **Tableau PAT** — confirm the PAT in `~/.claude.json` (tableau server env) is valid before any Tableau step
3. **Gmail MCP** — confirm it is connected AND tools are loaded (not just "connected"); if tools are missing, restart the MCP server before proceeding — do NOT kill the process mid-session
4. **MFA push failures** — if a JumpCloud push fails twice, fall back to TOTP immediately rather than retrying pushes indefinitely

If any check fails, stop and surface it before starting the workflow. Do not proceed with partial auth state.

## Available Skills

Custom slash commands defined in `~/.claude/commands/`. Plugin skills are namespaced (e.g., `carsdotcom-general:generate-pr`). If the user invokes a `/command` not in this list, suggest the closest match by name rather than running nothing.

**Cars Commerce internal plugin (`carsdotcom-general`) — invoke via `/carsdotcom-general:<skill>`:**
| Skill | What it does |
|---|---|
| `generate-pr` | Draft PR description from branch changes |
| `code-review` | Review code for quality, security, and best practices |
| `generate-tests` | Generate unit/integration tests for a function or module |
| `code-debug` | Systematic debugging workflow |
| `code-explain` | Explain a block of code clearly |
| `analyze-metrics` | Analyze Datadog or other metric data |
| `audit-repo` | Full repo quality, security, dependency, and performance audit |
| `audit-documentation` | Review and improve documentation |
| `workflow` | General workflow orchestration |
| `generate-claude-context` | Generate a CLAUDE.md for a codebase |
| `atomize-branch` | Split a large branch into smaller focused PRs |
| `create-cab-ticket` | Create a CAB change advisory ticket |

**Official plugin skills (also available):**
- `commit-commands`: `/commit`, `/commit-push-pr`, `/clean_gone` — git workflow helpers
- `code-review`: `/code-review` — multi-agent PR review with confidence scoring
- `security-guidance`: automatic security warnings when editing sensitive files

### Pre-Send Review Rule (ALL reporting workflows)

> **All Gmail drafts go to `jcrawley@cars.com` first.** Before any client-facing email is sent or finalized, create the draft addressed to Jake for review and format approval. Client recipients are set in the skill file but are not used until Jake explicitly approves the format and gives the go-ahead. This rule applies to every workflow below until further notice.

**Recurring reporting workflows:**
| Command | What it does | Cadence | Output |
|---|---|---|---|
| `/nalley-pb-report` | Nalley Automotive Price Badge Report — Tableau LEI pull + admin.cars.com Demand Signals → Google Sheet → Gmail draft | Weekly | Google Sheet (Nalley PB sheet) + Gmail draft to account team |
| `/hendricks-pb-report` | Hendrick Automotive Price Badge Report (same flow as Nalley) | Weekly | Google Sheet (Hendrick PB sheet) + Gmail draft to account team |
| `/herb-chambers-pb-report` | Herb Chambers GM monthly PB touchpoint — 6 active stores, parallel LEI + Demand Signals → per-store reports (used-only; $500 Honda / $1000 luxury) | Monthly (1st Wed, after approval) | 6 per-store Google Sheets + 6 Gmail drafts to GMs (gated to Jake until format approved) |
| `/sonic-monthly-report` | Sonic Automotive brand-segmented performance report (~101 stores, 18 brands; rotating luxury/volume focus) with per-brand Gmail drafts | Monthly | Per-brand Gmail drafts; data sourced from Tableau By Store view |
| `/sonic-billing` | Sonic & Hendrick billing reconciliation report | Monthly | Google Sheet + Gmail draft |
| `/aca-monthly-report` | Atlantic Coast Automotive monthly store report (~72 stores) → Google Sheet → email to Danielle McJunkins | Monthly | Google Sheet + Gmail draft to Danielle McJunkins |
| `/ecarone-vpm-report` | eCarOne VPM (Vehicle Performance Metrics) report | Monthly | Gmail draft |
| `/echopark-monthly-report` | EchoPark Automotive monthly performance report (17 used-car stores, no rotation) — store scorecard + investigation flags + single group email | Monthly | Google Sheet + Gmail draft to EchoPark contact (TBD) |
| `/asbury-monthly-report` | Asbury Group full-umbrella report (149 stores: Asbury + LHM + Koons + Herb Chambers) — per-sub-group emails + Umbrella Overview verification gate | Monthly | 4 sub-group Gmail drafts + Umbrella Overview; contacts TBD |
| `/ep-review-report` | EchoPark DealerRater review report | Monthly | Gmail draft |
| `/herb-chambers-employee-update` | Herb Chambers quarterly DealerRater employee profile audit (~24 stores: adds/removes/title fixes) | Quarterly | Change summary + Gmail draft |

**On-demand analysis:**
| Command | What it does |
|---|---|
| `/prep <dealer name or CCID>` | Pre-call briefing — SF account + Tableau metrics + investigation flags + DealerRater + 3 talking points in ~90 seconds |
| `/auto-research` | Automotive Research Analyst — Growth & Gains deep dive on a specified dealer or market |
| `/dealer-marketshareanalysis` | Dealer market share demand analysis for a specified ZIP/DMA or dealer radius |
| `/dr-employee-update` | Ad-hoc DealerRater employee roster update for any dealer — client provides staff list, skill handles removes/adds/title changes via DR admin (Playwright) |

**Unknown-command handling:** If the user types a `/command` that isn't listed above (e.g., `/ultraplan`, `/ultra-plan`, `/nalley-report`), do not silently fail. Suggest the closest match from this table and confirm before running it.

## Scheduled Tasks (Cowork Automation)

The following tasks are configured as scheduled/automated runs in Cowork. Avoid manually triggering these during their scheduled windows to prevent double-runs:

| Task | Cadence | Notes |
|---|---|---|
| Nalley PB Report | Weekly | Mirrors `/nalley-pb-report` workflow |
| Hendrick PB Report | Weekly | Mirrors `/hendricks-pb-report` workflow |
| Herb Chambers PB Report | Monthly (1st Wed 8 AM) | launchd `com.jcrawley.herb-chambers-pb-report` — NOT yet loaded; pending format approval + 6 Tableau custom views + 6 admin UUIDs |
| Sonic Monthly Report | Monthly | |
| ACA Monthly Report | Monthly | |

If a scheduled task fires during an interactive session, check whether it completed successfully before re-running manually.

## Python Apps

**Streamlit apps** (run with `python3 -m streamlit run`):
```bash
python3 -m streamlit run ~/Documents/scripts/chat_app.py                # simple chat UI
python3 -m streamlit run ~/Documents/scripts/cowork/cowork.py           # cowork assistant with streaming + sidebar context
python3 -m streamlit run ~/Documents/scripts/dealer_health.py           # dealer health dashboard (SF + admin.cars.com + Claude)
```

**Script testing**:
```bash
python3 ~/Documents/scripts/test_prompt.py                   # fill in project_context and user_request before running
```

**Market Intelligence report generator**:
```bash
python3 ~/Documents/scripts/generate_market_report.py        # outputs to ~/Documents/Reports/HamptonRoads/
# Tableau CSVs: save to ~/Documents/Tableau/
# Templates: ~/Documents/templates/
```

Install dependencies for the cowork app:
```bash
pip3 install -r ~/Documents/scripts/cowork/requirements.txt
```

## Connected MCP Services

The following MCP servers are configured in `~/.claude.json` (project scope; `bigquery` is top-level). **`settings.json` does NOT define MCP servers — Claude Code ignores that key.**

| Server | Purpose | Auth | Expiry / Rotation |
|--------|---------|------|---|
| `tableau` | Cars Commerce Tableau (us-west-2b, site: cars) | PAT "Claude" in `.claude.json` env (jcrawley's account; Viewer role; row-level security limits view exports to assigned AE's dealers) | Expires ~April 2027 — rotate in `.claude.json` env |
| `gmail` | jcrawley@cars.com Gmail | OAuth token at `~/.claude/tokens/gmail_jcrawley.json` | Access token expires hourly (auto-refreshed); refresh token is permanent |
| `google-calendar` | Google Calendar | OAuth via `~/gcp-oauth.keys.json` | Refresh as needed via Google OAuth flow |
| `google-tasks` | Google Tasks | Refresh token in `.claude.json` env | |
| `google-analytics-gafield` | GA property (gafield) | ADC at `~/.claude/ga_tokens/gafield_adc.json` | |
| `google-analytics-gafield1` | GA property (gafield1) | ADC at `~/.claude/ga_tokens/gafield1_adc.json` | |
| `atlassian` | Jira + Confluence (carscommerce.atlassian.net) | API token in `.claude.json` env | Rotate if 401s appear |
| `gdrive` | Google Drive | OAuth via `~/gcp-oauth.keys.json` + `~/.claude/tokens/gdrive_credentials.json` | |
| `salesforce` | Salesforce (Cars Commerce org) | SF CLI at `~/.npm-global/bin/sf` | Re-auth via `sf org login web` if session expires |
| ~~`slack`~~ | **DECOMMISSIONED 2026-06-16** per Enterprise security directive — config removed from `.claude.json`, npm package uninstalled. Do NOT re-enable or recreate. | n/a | — |
| `playwright` | Browser automation | Configured in `.claude.json` via `npx @playwright/mcp@latest` | |
| `google-sheets` | Read/write Google Sheets | OAuth via `~/gcp-oauth.keys.json` + `~/.claude/tokens/sheets_token.json` | |
| `google-docs` | Read/write Google Docs | OAuth credentials in `.claude.json` env | |
| `bigquery` | BigQuery queries (claude-integration project) | Service account key at `~/.claude/ga_tokens/bigquery_adc.json` | Service account key — rotate annually or if compromised |
| `github` | Personal GitHub | PAT in `.claude.json` env | Rotate if expired or revoked |
| `github-work` | Cars Commerce GitHub | Work PAT in `.claude.json` env | Rotate if expired or revoked |
| `chrome-devtools` | Chrome DevTools Protocol (desktop app connector) | Native desktop app — no local config needed | |
| `figma` | Figma designs (desktop app connector) | Native desktop app — no local config needed | |
| `cars-mcp` | Cars.com vehicle listings search | Native desktop app connector | |

**Token refresh — Gmail:** Access tokens expire every hour. The refresh token in `gmail_jcrawley.json` is permanent — the MCP server handles refresh automatically. If the token file's `access_token` is stale, refresh manually via the Google OAuth token endpoint.

## Salesforce

**Auth:** SF CLI (`~/.npm-global/bin/sf`). Re-authenticate with `sf org login web` if session expires.

**Key field mappings:**
- `CCID__c` — links Salesforce accounts to admin.cars.com dealer IDs (use for joining SF data to admin.cars.com UUID lookups)
- Standard account fields: `Name`, `Id`, `CCID__c`, `Account_Status__c`, `Products__c`

**Common query patterns:**
```bash
# Look up a dealer by name
sf data query --query "SELECT Id, Name, CCID__c, Account_Status__c FROM Account WHERE Name LIKE '%Dealer Name%'" --target-org <alias>

# Look up by CCID
sf data query --query "SELECT Id, Name, CCID__c FROM Account WHERE CCID__c = '12345'" --target-org <alias>
```

**Notes:**
- No write operations are performed in standard reporting workflows — SF queries are read-only
- `dealer_health.py` uses SF CLI via subprocess; ensure the CLI org alias is active before running

## App Architecture

**`chat_app.py`** — minimal Streamlit chat: session-state message history → `client.messages.create()` → display reply.

**`cowork/cowork.py`** — extended version with:
- Sidebar `project_context` text area injected into the system prompt at request time
- Streaming via `client.messages.stream()` with a `st.empty()` placeholder updated on each chunk
- "Clear conversation" button that resets `st.session_state.messages`

**`test_prompt.py`** — non-interactive script: fill `project_context` and `user_request` strings, runs a single `messages.create()` call with `temperature=1` and prints the result.

Both the Streamlit app and the test script use `claude-sonnet-4-6`.

**`dealer_health.py`** — self-serve dealer health snapshot:
- Sidebar: enter dealer name → pulls Salesforce account data (CCID, status, products) + admin.cars.com Performance Trends (inventory, VDPs, connections, badges)
- Claude streams a Dealer Growth Triangle analysis
- Data sources: SF CLI (`sf data query`), admin.cars.com (browser automation via CDP — requires active JumpCloud SSO session)
- admin.cars.com URL pattern: `/dealers/{UUID}/reports/performance_trends` — UUID obtained by searching `/dealers/all/reports?query={name}`
- Key SF field: `CCID__c` links Salesforce accounts to admin.cars.com dealer IDs
- **Status:** SF + Claude working; admin.cars.com scraper not yet integrated (WIP)

## admin.cars.com

- Auth: JumpCloud SSO (manual login, session persists in browser)
- Dealer search: `GET /dealers/all/reports?query={name_or_ccid}` → HTML with UUID links
- Reports per dealer: performance_trends, demand_signals, reputation_health, listings_optimizer, sales_attribution, dmv_market_share, connections_contact_details, walk_in_demand, vehicle_demand, roi_one_sheeter
- Performance Trends data (embedded Tableau from reports.cars.com): Avg Inventory, Under-Merchandised %, Connections, VDPs, Fair/Above Badges — all with MoM % changes
- Has "Download Crosstab" button for CSV export within the Tableau iframe

## Tableau API Access

**PAT:** "Claude" (in `.claude.json` env + MCP), Viewer role, expires ~April 2027.

### Dealer Health Metrics — By Store Table for Export
View ID `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`. Filter with `vf_Maj Cust Name`:
- Sonic=`Sonic` (120), Asbury=`Asbury` (79), ACA=`Atlantic Coast Automotive MA Group` (72)
- Hendrick=`Hendrick Automotive Group` (72), Greenway=`Greenway MA Group` (36), Herb Chambers=`Herb Chambers MA Group` (34)
- Larry Miller=`Larry Miller` (32), Doherty=`Doherty MA Group` (21), Jim Ellis=`Jim Ellis MA Group` (21)
- Koons=`Koons Automotive MA Group` (18), EchoPark=`EchoPark MA Group` (17)
- Indigo=`Indigo Auto MA Group` (25)
- Returns 48 metrics per store (CP/PP/Delta). **Omit `Accept: text/csv` header** (returns 406).

### Unrestricted Views (no RLS)
- **AE Insights Dashboard** (`a60dbfc3`) — 75K rows, all dealers: CCID, DMA, AE, products, MRR
- **Searches by Zip Code** (`39464986`) — 490K rows, all DMAs: ZIP-level search volume by quarter (**all-make only** — see limitations)

### Limitations
- Dealer-level views (Performance Trends, Demand Signals, Price Comparison) are RLS-locked to one default dealer — `vf_` filters silently ignored
- "All" filter value returns 0 via API (works in UI only)
- Direct datasource queries blocked (Viewer role)
- For per-dealer deep dives (Demand Signals, Market Comparison crosstab), use admin.cars.com instead
- **`vf_make` on view `39464986` is silently ignored.** Confirmed: Honda-filtered API download returns 190 rows vs 179 for no-filter; no `make` column in output. `generate_market_report.py` no longer passes this parameter. Reports are all-make; make label is cosmetic only. Quarter coverage is also uneven (47% of ZIPs have full history) — use `--quarters 4` or rely on `searches_avg_per_q` normalization.

## CSV Schema Validation

Before parsing any Tableau CSV export or admin.cars.com crosstab download:
- Read the header row and validate column names/order match the script's `EXPECTED_COLUMNS` or equivalent constant
- If columns have shifted, print the diff and stop — do not proceed with silent data errors (blank MMYT, missing PTM%, phantom callouts, wrong LEI values)
- Ask the user to confirm the mapping before continuing

## Email Formatting Conventions

- Always send HTML-formatted emails for briefings and reports — never fall back to plain text
- Use past-tense labels ("Added" / "Removed") rather than imperative ("To Add" / "To Remove") when describing actions already completed
- Before composing any morning briefing or time-sensitive email, verify the day-of-week in the subject/body matches the actual send date

## Price Badge Report Workflows

- Before running /hendrick-pb-report or /nalley-pb-report, confirm Tableau MCP is connected and JumpCloud MFA device is available.
- After CSV download, validate column order matches expected schema before populating sheets (CSV format has changed before and caused silent bad data).
- When sorting sheets, preserve the header row explicitly (previous runs sorted headers into the data).
- Never replace formulas during sheet cleanup steps — only clear values.

## Scheduling / Automation

### Caffeinate Reminder
When setting up cron/launchd jobs on this Mac, always remind the user to run `caffeinate` or configure the machine to stay awake — scheduled jobs will not fire if the computer is locked/asleep.
