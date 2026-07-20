#!/usr/bin/env bash
# Re-apply the gmail-mcp HTTP-daemon patch to @shinzolabs/gmail-mcp/dist/index.js.
#
# WHY: the persistent HTTP Gmail MCP daemon (launchd: com.jcrawley.gmail-mcp-http)
# needs two changes the upstream package doesn't offer, and `npm update`/reinstall
# reverts them:
#   1. app.listen(PORT, '127.0.0.1')  — bind loopback ONLY. The Smithery HTTP server
#      is UNAUTHENTICATED; binding all interfaces would expose the Gmail API to the LAN.
#   2. GMAIL_HTTP_ONLY=1 skips the stdio transport so the launchd daemon (stdin=/dev/null)
#      doesn't exit on stdin EOF and thrash KeepAlive.
#
# The patch is backward compatible: with GMAIL_HTTP_ONLY unset, stdio mode still works
# (and now also binds its HTTP side to loopback — a free hardening).
#
# Run this after any gmail-mcp upgrade, then: launchctl kickstart -k gui/$(id -u)/com.jcrawley.gmail-mcp-http

set -euo pipefail
F="$(npm root -g)/@shinzolabs/gmail-mcp/dist/index.js"
[ -f "$F" ] || { echo "ERROR: $F not found"; exit 1; }

if grep -q "GMAIL_HTTP_ONLY" "$F"; then
    echo "Already patched."
    exit 0
fi

cp -p "$F" "$F.prepatch-$(date +%Y%m%d-%H%M%S)"

python3 - "$F" <<'PY'
import sys
f = sys.argv[1]
s = open(f).read()
old = ("    const stdioServer = createServer({});\n"
       "    const transport = new StdioServerTransport();\n"
       "    await stdioServer.connect(transport);\n"
       "    // Streamable HTTP Server\n"
       "    const { app } = createStatefulServer(createServer);\n"
       "    app.listen(PORT);")
new = ("    if (process.env.GMAIL_HTTP_ONLY !== '1') {\n"
       "        const stdioServer = createServer({});\n"
       "        const transport = new StdioServerTransport();\n"
       "        await stdioServer.connect(transport);\n"
       "    }\n"
       "    // Streamable HTTP Server\n"
       "    const { app } = createStatefulServer(createServer);\n"
       "    app.listen(PORT, '127.0.0.1');")
if old not in s:
    print("ERROR: expected upstream block not found — package layout changed; patch manually.")
    sys.exit(1)
open(f, "w").write(s.replace(old, new, 1))
print("Patched:", f)
PY

node --check "$F" && echo "syntax OK"
