# Recovery Agent: Gmail MCP Stale Process / Tools Missing

Invoked when Gmail draft creation fails, Gmail tools are missing from the session, or the `gmail-mcp` process is unresponsive.

**Autonomy level: FULL for token issues. PARTIAL for mid-session tool loss** — see Step 3.

---

## What This Failure Means

| Signal | Root Cause |
|--------|-----------|
| `gmail tools not found` / tools absent from MCP list | Server died or never bound in this session |
| Draft creation returns `401` or `invalid_grant` | Access token stale (auto-refresh failed) or refresh token revoked |
| `mcp__claude_ai_Gmail__create_draft` timeout | Gmail MCP process hung |
| `gmail-mcp` not in `ps aux` | Process exited — SessionStart hook didn't restart it |

---

## Recovery Steps

### Step 1 — Check current process state

```bash
pgrep -fl 'gmail-mcp'
```

- **Process running:** Skip to Step 2 (token issue, not process issue)
- **Process dead:** Go to Step 3

### Step 2 — Refresh access token

The access token expires every hour. The refresh token in `~/.gmail-mcp/credentials.json` is permanent.

Run the token refresh directly:

```bash
python3 - <<'EOF'
import json, urllib.request, urllib.parse, time
keys = json.load(open('/Users/jcrawley/.gmail-mcp/gcp-oauth.keys.json'))['installed']
token = json.load(open('/Users/jcrawley/.gmail-mcp/credentials.json'))
data = urllib.parse.urlencode({
    'client_id': keys['client_id'],
    'client_secret': keys['client_secret'],
    'refresh_token': token['refresh_token'],
    'grant_type': 'refresh_token'
}).encode()
resp = json.loads(urllib.request.urlopen(
    urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
).read())
token['access_token'] = resp['access_token']
token['expiry_date'] = int(time.time() * 1000) + resp.get('expires_in', 3599) * 1000
json.dump(token, open('/Users/jcrawley/.gmail-mcp/credentials.json', 'w'), indent=2)
print("✓ Token refreshed")
EOF
```

If this succeeds, retry the Gmail operation. If `invalid_grant` error: the refresh token was revoked — escalate (Step 4).

### Step 3 — Process dead: use Gmail API directly

**Do NOT restart the gmail-mcp process mid-session** — it will start but tools won't bind to the current session. 

Instead, create the draft using the Gmail API directly via Python (the same `create_gmail_draft()` function pattern used in `pb_report.py`):

```bash
python3 ~/Documents/scripts/pb_report.py --dealer <dealer> --stats-only
# pb_report.py uses Gmail API directly, not MCP — this will succeed even without the MCP server
```

Or for a standalone draft, use the `create_gmail_draft()` helper from `pb_report.py`:

```python
# Direct Gmail API — bypasses the MCP entirely
from pb_report import get_gmail_service, create_gmail_draft
service = get_gmail_service()
draft_id = create_gmail_draft(service, cfg, stats, dem_stats)
```

### Step 4 — Escalate: refresh token revoked

```
⚠️ ESCALATE: Gmail refresh token revoked
Action required:
  1. Run the Gmail OAuth flow: python3 ~/Documents/scripts/pb_report.py --reauth-gmail
     (or manually delete ~/.gmail-mcp/credentials.json and re-run the MCP OAuth flow)
  2. Restart Claude Code session
Workflow state saved — will resume from checkpoint after re-auth.
```

---

## Checkpoint Contract

On recovery via direct API: `cp.step("gmail_recovery", {"method": "direct_api", "draft_id": "<id>"})`

On escalation: `cp.fail("gmail_recovery", "Refresh token revoked — re-auth required", kind="gmail-reauth-required")`
