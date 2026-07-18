#!/usr/bin/env bash
# Deploy the ACA ReviewBuilder Tone-Picker Click Tracker web app via clasp.
# Safe to re-run: creates the project once, then pushes + re-deploys.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

TITLE="ACA ReviewBuilder Click Tracker"

if ! clasp show-authorized-user >/dev/null 2>&1; then
  cat <<'EOF'
❌ Not logged in to clasp. Two one-time steps, then re-run ./deploy.sh:
   1. Enable the Apps Script API:  ! open "https://script.google.com/home/usersettings"  → toggle ON
   2. clasp login
EOF
  exit 1
fi

if [ ! -f .clasp.json ]; then
  echo "▸ Creating remote Apps Script web app project…"
  cp Code.js .Code.js.keep
  cp appsscript.json .appsscript.json.keep
  # A web app is a STANDALONE script whose manifest carries the webapp block.
  clasp create-script --type standalone --title "$TITLE" --rootDir .
  mv -f .Code.js.keep Code.js
  mv -f .appsscript.json.keep appsscript.json
  if [ ! -f .clasp.json ]; then echo "❌ create failed (no .clasp.json written)"; exit 1; fi
fi

echo "▸ Pushing code…"
clasp push -f || { echo "push failed"; exit 1; }

echo "▸ Creating web app deployment…"
clasp create-deployment --description "ACA ReviewBuilder click tracker" || { echo "deploy failed"; exit 1; }

echo ""
echo "================= TRACKED LINK BASE ================="
DEP=$(clasp list-deployments 2>/dev/null | grep -v '@HEAD' | grep -oE 'AKfycb[A-Za-z0-9_-]+' | tail -1)
if [ -n "${DEP:-}" ]; then
  echo "https://script.google.com/macros/s/$DEP/exec"
else
  echo "Run:  clasp list-deployments   (URL = https://script.google.com/macros/s/<deploymentId>/exec)"
fi
echo "===================================================="
echo ""
echo "⚠  FINAL one-time step — authorize the mail + sheets scopes:"
echo "    clasp open-script   → in the editor: Run ▸ authorizeScopes → approve the Google consent"
echo "    (clasp can't trigger that consent; without it the link can't notify or log.)"
