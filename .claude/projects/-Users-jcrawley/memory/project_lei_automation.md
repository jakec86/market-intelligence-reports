---
name: LEI Tableau Download Automation
description: Findings from automating Tableau LEI crosstab download — JS API sequence, URL filter params, SSO requirements
type: project
originSessionId: a381b1b2-dc17-49cc-aefd-c546ad1ffdff
---
## Tableau LEI-Local v2 Automation (tested 2026-04-10)

### What Works
- **URL filter params** work with exact field name casing: `?Maj%20dealer%20name=Hendricks`
- **Tableau JS API** via `tableau.VizManager.getVizs()[0]` works inside the iframe for programmatic filter changes
- `applyFilterAsync("DMA market name", [], tableau.FilterUpdateType.ALL)` successfully resets DMA to All
- `applyFilterAsync("Maj dealer name", ["Hendrick Automotive Group"], tableau.FilterUpdateType.REPLACE)` sets the major dealer filter
- REST API PAT auth works (200 OK) but **row-level security blocks Hendrick data** in API exports — web UI has broader access

### Reliable Automated Sequence
1. Navigate to LEI-Local v2 (requires active JumpCloud SSO session in MCP browser)
2. Revert view to defaults: `viz.revertAllAsync()`
3. JS API: Set DMA = All
4. Wait for viz to load (heavy query, may timeout CDP — use retry)
5. JS API: Set Maj dealer name = "Hendrick Automotive Group"
6. Wait for viz to process
7. JS API: Reset dependent filters to All (Grp dealer name, Dealer Name and ID)
8. Download crosstab via Download menu

### Key Gotchas
- **Cascading filters break**: Setting Maj dealer name causes Grp dealer name and Dealer Name and ID to cascade to "(None)" — must explicitly reset them to All after
- **CDP timeout**: Filter changes on large datasets (All DMAs) can timeout the protocol call — need retry/longer timeout
- **JumpCloud SSO**: Required once per MCP browser session — can't be automated (manual password entry)
- **Correct Maj dealer name value**: Use "Hendrick Automotive Group" (not "Hendricks" — that was the saved filter alias)

### Gmail OAuth
- Token at `~/.claude/tokens/gmail_jcrawley.json` now has `gmail.compose` + `gmail.modify` scopes (re-authed 2026-04-10)
- Draft creation works via Gmail API: search thread → build RFC 2822 with In-Reply-To/References → base64url encode → `drafts.create`

**Why:** Automates the most manual-intensive step of the weekly Price Badge Report workflow.

**How to apply:** When running `/hendricks-pb-report` or `/nalley-pb-report`, attempt the JS API sequence first. If SSO session is expired or CDP times out, fall back to manual CSV download from ~/Downloads/.

---

## VizQL Data API Path (pending permissions)

**Confirmed 2026-04-30:** `Cars Current Inventory PrvDay Detail` is the published datasource that powers the LEI-Local v2 view. If `VIZQL_DATA_API_ACCESS` is granted on this datasource (requires Tableau site admin), the entire Playwright/SSO/JS API sequence above becomes unnecessary.

**What to request from BI/Tableau admin:**
- `VIZQL_DATA_API_ACCESS` capability on the service account (or jcrawley's account)
- Query access to `Cars Current Inventory PrvDay Detail` (primary — eliminates LEI manual step)
- Query access to: Cars Dealer Activity 13Mo Detail, Cars Connections 13Mo Detail, Cars Value Delivery 13Mo Summary
- RLS bypass or all-dealer mapping on the service account

**How to apply:** Once granted, replace the Playwright LEI sequence with a direct VizQL Data API query filtered by dealer group and stock type — no SSO, no browser, fully automated.
