---
name: project_pb_headless_oauth_401
description: Headless PB runs 401 when the claude.ai OAuth login expires; fix = /login; wrapper now auth-pre-flights
metadata: 
  node_type: memory
  type: project
  originSessionId: 44b4867b-9d56-4ab9-8a9d-c6197363644e
---

Scheduled Price Badge runs (`run-report.sh` → `claude -p`) authenticate via the **claude.ai OAuth login**, NOT an API key. The `anthropic-api-key` Keychain entry is **empty**, so line ~42's `export ANTHROPIC_API_KEY="$(security ... || true)"` is a no-op and the CLI falls back to OAuth. (Empty `ANTHROPIC_API_KEY` is treated as unset — verified.)

**Failure mode (2026-06-22):** the OAuth token expired/failed unattended refresh after the last good run (Jun 19). Every attempt logged `Failed to authenticate. API Error: 401 Invalid authentication credentials` and exited 1 *before reaching any workflow step* — all 6 Hendrick+Nalley attempts burned ~37 min each and only surfaced via the failure-alert email. This is distinct from the cold-start TIMEOUT/STALL failures (those exit 137, killed by the watchdog).

**Fix:** run `/login` in an interactive session to refresh the token. The headless path then works (the empty-key export is harmless). A 401 is NOT transient — re-login is the only fix.

**Wrapper hardening (2026-06-22):** `run-report.sh` now has (1) an **auth pre-flight** — a trivial `claude -p` ping with NO MCP servers (`mcp-config-empty.json` + `--strict-mcp-config`) before the retry loop; on a detected auth-fail regex it aborts (exit 3) with a distinct "AUTH EXPIRED — run /login" alert instead of burning 3 retries; and (2) an **in-loop 401 short-circuit** that breaks remaining retries if any attempt's log shows the auth regex. `notify_failure` takes an optional `FAIL_REASON` env var that flags AUTH failures and prints `/login` recovery steps. Verified: pre-flight returns rc=0/"OK" when auth is valid.

Related: [[project_pb_report_production]], [[feedback_auth_login_migration]], [[project_totp_fallback_paused]].
