#!/bin/bash
# Validate the Tableau PAT in settings.json by attempting a sign-in.
# Uses Python for the HTTP call to avoid shell escaping issues with the PAT value.
# Exits silently on success; emits a systemMessage warning on failure.

python3 - <<'PYEOF'
import json, sys, urllib.request, urllib.error

SETTINGS = "/Users/jcrawley/.claude/settings.json"
try:
    s = json.load(open(SETTINGS))
    env = s["mcpServers"]["tableau"]["env"]
    server, site, pat_name, pat_val = env["SERVER"], env["SITE_NAME"], env["PAT_NAME"], env["PAT_VALUE"]
except Exception as e:
    print(json.dumps({"systemMessage": f"⚠️ Tableau PAT config unreadable in settings.json: {e}"}))
    sys.exit(0)

payload = json.dumps({
    "credentials": {
        "personalAccessTokenName": pat_name,
        "personalAccessTokenSecret": pat_val,
        "site": {"contentUrl": site}
    }
}).encode()

try:
    req = urllib.request.Request(
        f"{server}/api/3.21/auth/signin",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        if resp.status == 200:
            sys.exit(0)  # Valid — sign out token embedded in response, ignore it
        print(json.dumps({"systemMessage": f"⚠️ Tableau PAT check returned HTTP {resp.status} — verify PAT in ~/.claude/settings.json."}))
except urllib.error.HTTPError as e:
    if e.code in (401, 403):
        print(json.dumps({"systemMessage": "⚠️ Tableau PAT is invalid or expired — rotate it in ~/.claude/settings.json before running Tableau workflows."}))
    else:
        print(json.dumps({"systemMessage": f"⚠️ Tableau PAT check returned HTTP {e.code} — verify PAT in ~/.claude/settings.json."}))
except Exception as e:
    print(json.dumps({"systemMessage": f"⚠️ Tableau PAT check failed ({e}) — network issue or server unavailable."}))
PYEOF
