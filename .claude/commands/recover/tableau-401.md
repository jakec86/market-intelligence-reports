# Recovery Agent: Tableau 401 / Auth Failure

Invoked when any Tableau operation returns HTTP 401, 403, or a `tableau MCP not available` error.

**Autonomy level: FULL** — no human intervention required. This agent resolves automatically by falling back to Playwright.

---

## What This Failure Means

| Signal | Root Cause |
|--------|-----------|
| Tableau MCP returns `401 Unauthorized` | PAT expired, OR row-level security (RLS) blocking the specific view |
| Tableau MCP returns `403 Forbidden` | RLS — the PAT's Viewer role is rejected for this dealer/view combo |
| `tableau MCP not available` or tools missing | Server failed to start this session — tools not bound |
| Tableau MCP returns data with 0 rows | RLS silently filtered everything — treat as a logic-level 401 |

**Important:** For dealer-level views (LEI, Price Comparison, Demand Signals), the RLS issue is permanent — the Viewer PAT will always be rejected for non-default dealers. Playwright is the correct path, not a fallback.

---

## Recovery Steps

### Step 1 — Determine if PAT is valid at all

Run `bash ~/.claude/scripts/check-tableau-pat.sh`. 

- **If it exits with a warning:** The PAT is expired/invalid. Proceed to Step 2.
- **If it exits silently (valid):** The PAT is fine — this is an RLS 401. Skip to Step 3.

### Step 2 — PAT expired: attempt rotation

The PAT in `~/.claude/settings.json` → `mcpServers.tableau.env.PAT_VALUE` has expired. 

**Automated rotation is not possible** (Tableau PAT rotation requires a browser session at `us-west-2b.online.tableau.com → Account Settings`). Output this escalation and stop:

```
⚠️ ESCALATE: Tableau PAT expired
Action required: Log into Tableau Cloud → Account icon → My Account Settings → Personal Access Tokens
  1. Delete the expired "Claude" token
  2. Create a new PAT named "Claude"
  3. Update PAT_VALUE in ~/.claude/settings.json → mcpServers.tableau.env.PAT_VALUE
  4. Restart Claude Code session
Workflow state saved — will resume from checkpoint after token rotation.
```

### Step 3 — RLS 401: pivot to Playwright (automatic)

This is the standard path for all dealer-level Tableau views. No escalation needed.

1. Set workflow context: `TABLEAU_MODE=playwright`
2. Navigate to the Tableau portal URL using `mcp__playwright__browser_navigate`:
   ```
   https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2
   ```
3. If redirected to `sso.jumpcloud.com`: invoke the JumpCloud MFA Sub-procedure (defined in the calling workflow's skill file)
4. Apply filters and download the crosstab as described in the calling workflow's Tableau step
5. Validate the downloaded CSV exists at `~/.playwright-mcp/`
6. Return `RECOVERED: tableau-playwright-mode` to the supervisor

### Step 4 — Tableau MCP tools not bound

If `claude mcp list` shows `tableau: ✗` or tools are absent:

1. Do NOT kill the MCP process (severing tool binding mid-session)
2. Output: `⚠️ Tableau MCP is not bound in this session — proceeding with Playwright only`
3. Proceed directly to Step 3

---

## Checkpoint Contract

On success, write: `cp.step("tableau_recovery", {"mode": "playwright", "url": "<download_path>"})`

On escalation (expired PAT), write: `cp.fail("tableau_recovery", "PAT expired — human rotation required", kind="tableau-pat-expired")`
