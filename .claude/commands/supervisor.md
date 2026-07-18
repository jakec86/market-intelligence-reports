# Supervisor — Workflow Orchestration with Recovery

This skill wraps any recurring workflow (PB Report, VPM, ACA GM, Sonic Billing) with:
- Step-level checkpointing (survives session compaction / restarts)
- Error classification → recovery sub-agent dispatch
- Checkpoint-based resume (skip already-completed steps)
- Structured escalation when recovery fails

Invoke this skill at the START of any workflow that has a corresponding `~/.claude/commands/` skill file.

---

## How to Use

Instead of running `/hendricks-pb-report` directly, run:
```
/supervisor hendricks-pb-report
```

The supervisor wraps the workflow steps, adding checkpointing and recovery. For single-step operations or ad-hoc queries, use the workflow skill directly — the supervisor overhead isn't worth it.

---

## Error Classification Map

The supervisor classifies failures before dispatching. Match on the first pattern that fits:

| Error Signal | Classification | Recovery Agent |
|---|---|---|
| Tableau MCP returns 401/403 | `tableau-401` | `/recover/tableau-401` |
| Tableau MCP `tools not found` | `tableau-401` | `/recover/tableau-401` |
| Tableau returns 0 rows (RLS silent) | `tableau-401` | `/recover/tableau-401` |
| `gmail: ✗` or draft creation fails | `gmail-mcp` | `/recover/gmail-mcp` |
| `_validate_csv_headers` abort / `_require_col` abort | `csv-schema` | `/recover/csv-schema` |
| `sso.jumpcloud.com` redirect / push timeout / TOTP reject | `mfa-timeout` | `/recover/mfa-timeout` |
| Python script exits non-zero | Inspect stderr: re-classify above | — |
| Unknown / not classifiable | `unknown` | Escalate directly |

---

## Supervisor Execution Protocol

### Phase 0 — Check for existing checkpoint

```python
from checkpoint import Checkpoint
cp = Checkpoint("<workflow-name>")
last_good = cp.last_good()
```

- **No checkpoint (fresh run):** proceed from Step 1
- **Checkpoint exists, status=complete:** report completion, ask if re-run is intended
- **Checkpoint exists, status=failed:** print last failure summary, ask to resume or start fresh
- **Checkpoint exists, status=in_progress:** resume from `last_good` step (skip already-completed steps)

### Phase 1 — Pre-flight (always run, even on resume)

Run the three pre-flight checks even when resuming — auth state may have changed:
1. `bash ~/.claude/scripts/check-totp-keychain.sh`
2. `bash ~/.claude/scripts/check-tableau-pat.sh`
3. `bash ~/.claude/scripts/verify-gmail-mcp.sh`

If any check emits a `systemMessage`, surface it and wait for confirmation before proceeding.

Write checkpoint: `cp.step("preflight", {"totp": <bool>, "pat": <bool>, "gmail": <bool>})`

### Phase 2 — Execute workflow steps

For each step in the workflow:

```
TRY:
  Execute the step
  cp.step("<step_name>", {<relevant data>})
  Continue to next step

CATCH any failure:
  error_kind = classify_error(error_message)
  cp.fail("<step_name>", error_message, kind=error_kind)
  
  IF error_kind == "tableau-401":
      result = Agent(recover/tableau-401)
  ELIF error_kind == "gmail-mcp":
      result = Agent(recover/gmail-mcp)
  ELIF error_kind == "csv-schema":
      result = Agent(recover/csv-schema)
  ELIF error_kind == "mfa-timeout":
      result = Agent(recover/mfa-timeout)
  ELSE:
      ESCALATE (Phase 3)
  
  IF result == "RECOVERED":
      cp.step("<step_name>_recovery", {"agent": error_kind})
      Retry the failed step from checkpoint data
  ELSE (recovery agent escalated):
      ESCALATE (Phase 3)
```

### Phase 3 — Escalation

When a recovery agent cannot resolve the issue, output the full context package:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW HALTED: <workflow-name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failed step:    <step_name>
Error kind:     <classification>
Error message:  <verbatim error>

Recovery tried: <what was attempted>
Recovery result: <what blocked it>

Completed steps (will NOT need to redo):
  ✓ preflight
  ✓ <step_2>
  ✗ <step_3>  ← failed here

Checkpoint file: ~/.claude/state/<workflow>.json
Resume command:  /supervisor <workflow>  (after fixing the issue)

Action required: <specific human action — e.g. "approve JumpCloud push", "rotate Tableau PAT">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Phase 4 — Completion

On success: `cp.complete()` and print a clean summary of all steps + any metrics.

---

## Workflow Step Maps

Reference for checkpoint step names used by each workflow:

### hendricks-pb-report
```
preflight → tableau_download → csv_validation → sheet_import →
sheet_sort → read_stats → email_draft → complete
```

### nalley-pb-report
```
preflight → tableau_download → dem_signal_download → csv_validation →
sheet_import → sheet_sort → read_stats → email_draft → complete
```

### ecarone-vpm-report
```
preflight → tableau_vdp → tableau_leads → sheet_update →
row_format → complete
```

### aca-gm-report
```
preflight → download_market_opp → download_sales_attr →
download_reviews → csv_validation → send_emails → complete
```

### sonic-billing
```
preflight → tableau_data → sheet_build → hide_source_tabs →
email_draft → complete
```

---

## Checkpoint Resume Behavior by Step

| If last_good is... | Resume at... |
|---|---|
| `preflight` | `tableau_download` |
| `tableau_download` | `csv_validation` (use saved CSV path from checkpoint) |
| `csv_validation` | `sheet_import` |
| `sheet_import` | `sheet_sort` |
| `sheet_sort` | `read_stats` |
| `read_stats` | `email_draft` |
| `email_draft` | `complete` (already done — just print draft ID) |

On resume, retrieve saved data from the checkpoint:
```python
csv_path = cp.get_step_data("tableau_download").get("path")
```
