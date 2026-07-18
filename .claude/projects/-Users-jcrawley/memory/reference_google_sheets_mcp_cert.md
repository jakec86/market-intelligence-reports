---
name: reference_google_sheets_mcp_cert
description: google-sheets MCP broken on self-signed-cert error; Sheets REST API fallback via OAuth token
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5c5fb9c4-3d2a-40e2-a674-4914462060d8
---

**WORKING as of 2026-06-22 — MCP is healthy, REST fallback no longer required for by-ID ops.** Verified live: `list_sheets`/`get_sheet_data`/`update_cells`/`batch_update_cells` (all by spreadsheet ID) succeed. Cert fix is holding (Node TLS to `sheets.googleapis.com` returns OK).

**One remaining limitation:** `list_spreadsheets` fails with `Request had insufficient authentication scopes` because it uses the **Drive API** to enumerate files, but the OAuth token (`~/.claude/tokens/sheets_token.json`) is scoped to **`https://www.googleapis.com/auth/spreadsheets` only** (confirmed via tokeninfo — no Drive scope). All reporting workflows operate by sheet ID, so this doesn't matter in practice. To enable `list_spreadsheets`, re-run OAuth consent adding `drive.metadata.readonly` (or `drive.readonly`) and regenerate the token — interactive login required.

**Original cert root cause (FIXED 2026-06-16):** `sheets.googleapis.com` is TLS-intercepted by **Cloudflare Gateway / Zero Trust** — chain root is a self-signed `Gateway CA - Cloudflare Managed G2`. macOS keychain trusts it (so system Python works), but the MCP runs on **Node** (`~/.npm-global/bin/mcp-google-sheets`, `#!/usr/bin/env node`, node v24) which uses its **own bundled CA store** → `SELF_SIGNED_CERT_IN_CHAIN`. `/mcp` "Reconnected" does NOT fix it (process keeps old env).

**Fix applied:** exported macOS system roots (incl. Cloudflare Gateway CA) to `~/.claude/certs/node-extra-ca.pem` via `security find-certificate -a -p` (SystemRootCertificates + System keychains), and set `NODE_EXTRA_CA_CERTS=/Users/jcrawley/.claude/certs/node-extra-ca.pem` in the `google-sheets` server `env` in `~/.claude.json` (backup `~/.claude.json.bak-sheetscert-*`). Proven: `NODE_EXTRA_CA_CERTS=... node -e "https.get('https://sheets.googleapis.com/...')"` → TLS OK (vs `SELF_SIGNED_CERT_IN_CHAIN` without). **Restart Claude Code / reconnect the MCP to activate.** Regenerate the PEM if the Gateway CA rotates. Same env var fixes any other Node MCP hitting intercepted Google hosts (could set globally in `~/.zshrc`).

(Original symptom, for reference: every call failed with `self-signed certificate in certificate chain`.)

**Working fallback — Sheets REST API directly:** OAuth token at `~/.claude/tokens/sheets_token.json` has `client_id/client_secret/refresh_token/token_uri` and scope `https://www.googleapis.com/auth/spreadsheets` (read+write). Refresh → `GET/PUT https://sheets.googleapis.com/v4/spreadsheets/{id}[/values/{range}|:batchUpdate]`. Pattern script: `~/Documents/Reports/DealerRater-Testimonials/_write_notes.py` (refresh token, resolve tab title by gid, **match rows by column-A name not row number**, `values:batchUpdate` RAW). Same token-refresh approach works for Gmail (`~/.gmail-mcp/`). Related: [[reference_port3000_fix]], [[project_dealerinspire_testimonial_updates]].
