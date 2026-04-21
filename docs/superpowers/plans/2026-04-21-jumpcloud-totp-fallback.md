# JumpCloud TOTP Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add unattended JumpCloud MFA handling to `/hendricks-pb-report` and `/nalley-pb-report` so launchd-scheduled runs don't stall on push-notification timeouts. Retrieve a current 6-digit TOTP code from the macOS Keychain via `oathtool`, and submit it into the JumpCloud SSO page via Playwright.

**Architecture:** Three components. (1) One-time attended setup stores the TOTP seed in the login Keychain and installs `oathtool`. (2) A 6-line shell helper at `~/.claude/scripts/jumpcloud-totp.sh` reads the seed and prints the current code. (3) Both skill files gain a Step 0 pre-flight check (oathtool + Keychain) and a shared "JumpCloud MFA Sub-procedure" that detects the SSO page, calls the helper, fills the TOTP input, and retries once on rejection.

**Tech Stack:** bash, macOS Keychain (`security` CLI), `oath-toolkit` (Homebrew), Playwright MCP, existing launchd user agents.

**Spec:** `/Users/jcrawley/docs/superpowers/specs/2026-04-21-jumpcloud-totp-fallback-design.md`

**Note on version control:** `~/.claude/` is intentionally untracked in git. For rollback safety, tasks back up modified files to `/tmp/totp-backups/` before editing rather than using git commits. The plan and spec documents themselves live under the tracked `~/docs/` tree and will be committed.

---

## File Structure

**New files:**

| Path | Responsibility |
|---|---|
| `~/.claude/scripts/jumpcloud-totp.sh` | Read seed from Keychain, emit current 6-digit TOTP code, or exit 2/3 with actionable error |

**Modified files:**

| Path | Change |
|---|---|
| `~/.claude/commands/hendricks-pb-report.md` | Expand Step 0 TOTP check; add "## JumpCloud MFA Sub-procedure" section; reference sub-procedure from Step 1 Tableau |
| `~/.claude/commands/nalley-pb-report.md` | Expand Step 0 TOTP check; add "## JumpCloud MFA Sub-procedure" section; reference sub-procedure from Step 1 Tableau and Step 2 admin.cars.com |

**Not modified (per spec):**

- `~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist`
- `~/Library/LaunchAgents/com.jcrawley.nalley-pb-report.plist`

---

### Task 0: User Prerequisites (attended, manual)

**Purpose:** Install `oathtool`, reset TOTP at JumpCloud, store the base32 seed in the login Keychain. Must complete before any later task can be verified.

**Files:**
- No code changes in this task. User executes the listed commands in Terminal.

- [ ] **Step 1: Install oathtool via Homebrew**

Run:
```bash
brew install oath-toolkit
```

Expected output: installation completes successfully. If `brew` is not installed, follow https://brew.sh first.

- [ ] **Step 2: Verify oathtool is on PATH**

Run:
```bash
command -v oathtool && oathtool --version | head -1
```

Expected output: a path like `/opt/homebrew/bin/oathtool` (or `/usr/local/bin/oathtool` on Intel Macs) followed by a version string.

- [ ] **Step 3: Reset TOTP at JumpCloud and capture base32 seed**

Navigate in a browser to https://console.jumpcloud.com/userconsole, open Security → Multi-Factor Authentication. Next to "Authenticator App", click **Reset**. A QR code appears.

Click the "Can't scan?" or "Show secret key" link. Copy the base32 seed (typically a 26- or 32-character string of A–Z and 2–7). Also scan the QR into the 1Password app and/or your phone authenticator for redundancy — the same seed produces identical codes everywhere.

- [ ] **Step 4: Store the seed in the login Keychain**

Run (replace `<BASE32_SEED>` with the string from Step 3):
```bash
security add-generic-password -s jumpcloud-totp -a jcrawley -w '<BASE32_SEED>' -U
```

The `-U` flag updates an existing entry if one already exists, so this command is idempotent.

- [ ] **Step 5: Verify the Keychain entry**

Run:
```bash
security find-generic-password -s jumpcloud-totp -a jcrawley >/dev/null && echo "OK: entry found"
```

Expected output: `OK: entry found`

- [ ] **Step 6: Confirm the seed produces valid codes**

Run:
```bash
seed=$(security find-generic-password -s jumpcloud-totp -a jcrawley -w) && oathtool --totp -b "$seed"
```

Expected output: a single line of exactly 6 digits (e.g. `482190`). If `oathtool` complains about the seed format (`Bad base32`), re-check Step 3 for copy-paste errors — base32 uses A-Z and 2-7 only, no lowercase, no `0`, `1`, `8`, `9`.

- [ ] **Step 7: Confirm the code is currently accepted by JumpCloud**

While a Terminal window is showing the current code, log into any JumpCloud-protected resource (e.g. https://us-west-2b.online.tableau.com) and, when prompted for MFA, select "Authenticator App" / "Verification Code" and enter the 6-digit code from the Terminal. JumpCloud should accept it.

If JumpCloud rejects it: (a) the seed was copied wrong — redo Step 3, or (b) the Mac's clock is skewed — run `sudo sntp -sS time.apple.com` and retry.

---

### Task 1: Create the TOTP helper script (TDD)

**Files:**
- Create: `~/.claude/scripts/jumpcloud-totp.sh`

**Dependencies:** Task 0 must be complete (Keychain entry present, `oathtool` installed).

- [ ] **Step 1: Ensure scripts directory exists**

Run:
```bash
mkdir -p ~/.claude/scripts
```

Expected output: (none; idempotent).

- [ ] **Step 2: Write the failing test (inline)**

Run (before the helper exists, expected to FAIL):
```bash
~/.claude/scripts/jumpcloud-totp.sh 2>&1 | grep -E '^[0-9]{6}$'; echo "exit=$?"
```

Expected output: a shell error like `bash: /Users/jcrawley/.claude/scripts/jumpcloud-totp.sh: No such file or directory` and `exit=1` (grep finds nothing).

- [ ] **Step 3: Write the helper script**

Write the file `~/.claude/scripts/jumpcloud-totp.sh` with contents:

```bash
#!/bin/bash
# Emit a current JumpCloud TOTP code to stdout.
# Exit codes: 0 success, 2 missing dep or secret, 3 oathtool failure.
set -euo pipefail

if ! command -v oathtool >/dev/null; then
  echo "jumpcloud-totp: oathtool not found on PATH — run 'brew install oath-toolkit'" >&2
  exit 2
fi

seed=$(security find-generic-password -s jumpcloud-totp -a jcrawley -w 2>/dev/null) || {
  echo "jumpcloud-totp: Keychain entry jumpcloud-totp/jcrawley missing — see ~/docs/superpowers/specs/2026-04-21-jumpcloud-totp-fallback-design.md §One-time setup" >&2
  exit 2
}

oathtool --totp -b "$seed" || exit 3
```

- [ ] **Step 4: Make it executable**

Run:
```bash
chmod 755 ~/.claude/scripts/jumpcloud-totp.sh
```

- [ ] **Step 5: Run the test — expect PASS**

Run:
```bash
~/.claude/scripts/jumpcloud-totp.sh | grep -E '^[0-9]{6}$'; echo "exit=$?"
```

Expected output: a 6-digit code on one line, then `exit=0`.

- [ ] **Step 6: Rotation sanity check**

Run:
```bash
c1=$(~/.claude/scripts/jumpcloud-totp.sh); sleep 31; c2=$(~/.claude/scripts/jumpcloud-totp.sh); echo "c1=$c1 c2=$c2"
```

Expected output: two 6-digit codes. They will almost certainly differ (there's a ~1/1,000,000 chance they match by coincidence); if they do match, run the command again. If they consistently match, the script is broken.

- [ ] **Step 7: Back up and note completion**

Run:
```bash
mkdir -p /tmp/totp-backups && cp ~/.claude/scripts/jumpcloud-totp.sh /tmp/totp-backups/jumpcloud-totp.sh.v1
```

---

### Task 2: Hendrick skill — expand Step 0 TOTP pre-flight

**Files:**
- Modify: `~/.claude/commands/hendricks-pb-report.md:34-39` (Step 0 Pre-flight Checks)

- [ ] **Step 1: Back up the current file**

Run:
```bash
mkdir -p /tmp/totp-backups && cp ~/.claude/commands/hendricks-pb-report.md /tmp/totp-backups/hendricks-pb-report.md.pre-totp
```

- [ ] **Step 2: Edit Step 0 — replace the third check**

Find in the file:
```
3. **JumpCloud MFA device available** — confirm user has phone/TOTP ready before Tableau login prompts trigger. For scheduled/headless runs this is the single most common stall point.
```

Replace with:
```
3. **TOTP helper ready** — verify `oathtool` is on PATH (`command -v oathtool`) and the Keychain entry exists (`security find-generic-password -s jumpcloud-totp -a jcrawley` returns 0). If either check fails, abort with the remediation command shown by the helper error (see JumpCloud MFA Sub-procedure).
```

- [ ] **Step 3: Verify the edit**

Run:
```bash
grep -n "TOTP helper ready" ~/.claude/commands/hendricks-pb-report.md
```

Expected output: one matching line.

---

### Task 3: Hendrick skill — add JumpCloud MFA Sub-procedure + Step 1 reference

**Files:**
- Modify: `~/.claude/commands/hendricks-pb-report.md:41-47` (Step 1 — Tableau)
- Modify: `~/.claude/commands/hendricks-pb-report.md:88-89` (before `## Defaults`) — insert new `## JumpCloud MFA Sub-procedure` section

- [ ] **Step 1: Add MFA sub-procedure reference to Step 1**

Find in Step 1 — Tableau:
```
- Use the `tableau` MCP to pull the **LEI-Local v2** view from the Low Engaged Inventory Report (site: cars, us-west-2b)
```

Replace with:
```
- Use the `tableau` MCP to pull the **LEI-Local v2** view from the Low Engaged Inventory Report (site: cars, us-west-2b)
- **If the Tableau login redirects to a JumpCloud SSO page**, run the JumpCloud MFA Sub-procedure (defined below) before continuing.
```

- [ ] **Step 2: Insert the sub-procedure section**

Find in the file:
```

---

## Defaults
```

Replace with (note: three dashes on their own line before and after the new section):
```

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on a JumpCloud SSO challenge page (URL matches `sso.jumpcloud.com/*` or page title contains "JumpCloud").

1. **Detect the factor form.**
   - If a visible "Verification Code" input field is present → proceed to step 2.
   - If only a "Send Push" button is visible → click the "Try another way" / "Use authenticator code" link to reveal the TOTP input, then proceed.
   - If neither is available → abort with the error: `"JumpCloud MFA page shows no TOTP option — change default factor at console.jumpcloud.com/userconsole → Security → Multi-Factor Authentication"`.
2. **Retrieve a current code.** Run `~/.claude/scripts/jumpcloud-totp.sh` as a subprocess. Capture stdout. If exit code is non-zero, abort and surface the helper's stderr verbatim (it includes the remediation command).
3. **Submit.** Type the 6-digit code into the Verification Code input, then click the Submit/Verify button.
4. **Verify success.** Wait up to 10 seconds for the page to redirect away from `sso.jumpcloud.com`.
5. **Handle rejection (retry once).** If the page re-renders with an "invalid code" error:
   - Wait until the next 30-second TOTP boundary (`sleep $(( 30 - $(date +%S) % 30 ))`).
   - Fetch a fresh code from the helper.
   - Submit it.
   - If that also fails, abort with: `"TOTP rejected twice — check Mac clock (sudo sntp -sS time.apple.com) and that the Keychain seed matches the current JumpCloud enrollment"`.
6. **Never log the 6-digit code or the seed.** If logging page HTML for debugging, redact the Verification Code input value.

---

## Defaults
```

- [ ] **Step 3: Verify both edits**

Run:
```bash
grep -n "JumpCloud MFA Sub-procedure\|JumpCloud SSO page" ~/.claude/commands/hendricks-pb-report.md
```

Expected output: at least two matching lines (one in Step 1 reference, one in the sub-procedure header).

---

### Task 4: Nalley skill — expand Step 0 TOTP pre-flight

**Files:**
- Modify: `~/.claude/commands/nalley-pb-report.md:24-31` (Step 0 Pre-flight Checks)

- [ ] **Step 1: Back up the current file**

Run:
```bash
cp ~/.claude/commands/nalley-pb-report.md /tmp/totp-backups/nalley-pb-report.md.pre-totp
```

- [ ] **Step 2: Edit Step 0 — replace the fourth check**

Find in the file:
```
4. **JumpCloud MFA device available** — Tableau login and admin.cars.com both require JumpCloud SSO. Push timeouts have killed multiple runs; for scheduled jobs prefer TOTP over push.
```

Replace with:
```
4. **TOTP helper ready** — verify `oathtool` is on PATH (`command -v oathtool`) and the Keychain entry exists (`security find-generic-password -s jumpcloud-totp -a jcrawley` returns 0). If either check fails, abort with the remediation command shown by the helper error (see JumpCloud MFA Sub-procedure).
```

- [ ] **Step 3: Verify the edit**

Run:
```bash
grep -n "TOTP helper ready" ~/.claude/commands/nalley-pb-report.md
```

Expected output: one matching line.

---

### Task 5: Nalley skill — add JumpCloud MFA Sub-procedure + Step 1 and Step 2 references

**Files:**
- Modify: `~/.claude/commands/nalley-pb-report.md:33-39` (Step 1 — Tableau)
- Modify: `~/.claude/commands/nalley-pb-report.md:41-46` (Step 2 — admin.cars.com)
- Modify: `~/.claude/commands/nalley-pb-report.md:88-89` (before `## Defaults`) — insert new `## JumpCloud MFA Sub-procedure` section

- [ ] **Step 1: Add sub-procedure reference to Step 1 — Tableau**

Find in Step 1 — Tableau:
```
- **Use Playwright** to open the view in-browser at: `https://us-west-2b.online.tableau.com/#/site/cars/workbooks/996673/views` and apply the dealer's CustomerUUID filter, then download the crosstab CSV
```

Replace with:
```
- **Use Playwright** to open the view in-browser at: `https://us-west-2b.online.tableau.com/#/site/cars/workbooks/996673/views` and apply the dealer's CustomerUUID filter, then download the crosstab CSV
- **If the Tableau login redirects to a JumpCloud SSO page**, run the JumpCloud MFA Sub-procedure (defined below) before continuing.
```

- [ ] **Step 2: Add sub-procedure reference to Step 2 — admin.cars.com**

Find in Step 2 — admin.cars.com:
```
- Use Playwright → https://admin.cars.com/
```

Replace with:
```
- Use Playwright → https://admin.cars.com/
- **If the admin.cars.com login redirects to a JumpCloud SSO page**, run the JumpCloud MFA Sub-procedure (defined below). Note: depending on JumpCloud's SSO session cookie, this may or may not fire a second MFA challenge after the Tableau step. Be prepared for either.
```

- [ ] **Step 3: Insert the sub-procedure section**

Find in the file:
```

---

## Defaults
```

Replace with:
```

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on a JumpCloud SSO challenge page (URL matches `sso.jumpcloud.com/*` or page title contains "JumpCloud"). For Nalley runs, this may fire up to twice per invocation (once for Tableau in Step 1, once for admin.cars.com in Step 2).

1. **Detect the factor form.**
   - If a visible "Verification Code" input field is present → proceed to step 2.
   - If only a "Send Push" button is visible → click the "Try another way" / "Use authenticator code" link to reveal the TOTP input, then proceed.
   - If neither is available → abort with the error: `"JumpCloud MFA page shows no TOTP option — change default factor at console.jumpcloud.com/userconsole → Security → Multi-Factor Authentication"`.
2. **Retrieve a current code.** Run `~/.claude/scripts/jumpcloud-totp.sh` as a subprocess. Capture stdout. If exit code is non-zero, abort and surface the helper's stderr verbatim (it includes the remediation command).
3. **Submit.** Type the 6-digit code into the Verification Code input, then click the Submit/Verify button.
4. **Verify success.** Wait up to 10 seconds for the page to redirect away from `sso.jumpcloud.com`.
5. **Handle rejection (retry once).** If the page re-renders with an "invalid code" error:
   - Wait until the next 30-second TOTP boundary (`sleep $(( 30 - $(date +%S) % 30 ))`).
   - Fetch a fresh code from the helper.
   - Submit it.
   - If that also fails, abort with: `"TOTP rejected twice — check Mac clock (sudo sntp -sS time.apple.com) and that the Keychain seed matches the current JumpCloud enrollment"`.
6. **Never log the 6-digit code or the seed.** If logging page HTML for debugging, redact the Verification Code input value.

---

## Defaults
```

- [ ] **Step 4: Verify all three edits**

Run:
```bash
grep -cn "JumpCloud SSO page\|JumpCloud MFA Sub-procedure" ~/.claude/commands/nalley-pb-report.md
```

Expected output: `3` or higher (two references in Step 1/Step 2, one sub-procedure header).

---

### Task 6: Live attended test — Hendrick

**Purpose:** Exercise the full TOTP pass-through with a human watching. Confirms Tasks 1–3 work end-to-end against the real JumpCloud SSO flow.

**Files:**
- No file changes. This is an integration test.

- [ ] **Step 1: Start the workflow interactively**

Run in a fresh Terminal window:
```bash
claude -p "/hendricks-pb-report" --allowedTools "Bash,Edit,Read,Write,mcp__tableau__*,mcp__gmail__*,mcp__playwright__*" 2>&1 | tee /tmp/hendrick-pb-attended-$(date +%Y%m%d-%H%M%S).log
```

Expected behavior:
- Step 0 pre-flight reports Tableau MCP, Gmail MCP, TOTP helper all OK.
- Step 1 opens Tableau in a Playwright browser.
- When JumpCloud SSO prompts for MFA, the skill invokes the sub-procedure.
- The Verification Code input is auto-filled with a 6-digit code and submitted.
- Browser redirects to Tableau successfully; LEI view loads.

- [ ] **Step 2: Observe the MFA handshake**

Watch the Playwright browser window. Confirm:
- A JumpCloud MFA challenge page appears.
- Within a few seconds, a 6-digit code is typed into the Verification Code field.
- The form submits automatically.
- No push notification appears on your phone.

- [ ] **Step 3: Let the workflow complete through Step 3 (Gmail draft)**

Let the skill continue. Confirm:
- Step 1 Tableau CSV downloads.
- Step 2 sheet QC completes.
- Step 3 Gmail draft appears in the Drafts folder.

- [ ] **Step 4: Capture learnings**

Note in the log file (and in a comment at the bottom of the sub-procedure section in `~/.claude/commands/hendricks-pb-report.md` if any of these are surprising):
- Did JumpCloud default to TOTP, or did the skill need to click "Try another way"?
- Did any retry happen, or was the first code accepted?
- Did the sub-procedure fire at the expected point in Step 1?

---

### Task 7: Unattended dry run — Hendrick

**Purpose:** Prove the workflow runs cleanly from launchd with no human present and screen locked. This is the real goal of the entire plan.

**Files:**
- Modify temporarily: `~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist` (reverted in Step 5)

- [ ] **Step 1: Confirm current plist schedule**

Run:
```bash
grep -A1 "StartCalendarInterval" ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist | head -20
```

Note the current `Hour`, `Minute`, and `Weekday` values. You will restore them in Step 5.

- [ ] **Step 2: Set a one-off trigger ~5 minutes in the future**

Calculate the target time: current UTC + ~5 minutes rounded to next minute boundary.

Run (replace `<HOUR>` and `<MINUTE>` with the target values, no leading zeros):
```bash
# Example: if it's 14:23 local, set Minute=28.
# Use `date -v +5M` to get +5 min, then note the hour/minute.
date -v +5M "+%H %M"
```

Edit the plist to set `StartCalendarInterval` to `{ <Hour>, <Minute> }` only (remove the `Weekday` key for this test), then reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist
launchctl load ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist
```

- [ ] **Step 3: Lock the screen and wait**

Run:
```bash
pmset displaysleepnow
```

This locks the screen but keeps the user session logged in (Keychain stays unlocked). Do not log out.

Wait at least 8–10 minutes to give the workflow time to complete.

- [ ] **Step 4: Review the log**

Run:
```bash
tail -100 ~/.claude/logs/hendrick-pb-report.log; echo "---errors---"; tail -50 ~/.claude/logs/hendrick-pb-report-error.log
```

Expected:
- No MFA timeout errors.
- Step 0 pre-flight passes.
- MFA sub-procedure fires and completes (look for a line confirming the TOTP submission succeeded).
- Gmail draft is created.

If the log shows a Step 0 abort, re-verify Task 0 completed on this Mac. If the log shows an MFA timeout, the sub-procedure didn't trigger — re-read the skill file and confirm Task 3 edits landed.

- [ ] **Step 5: Restore the original schedule**

Run:
```bash
launchctl unload ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist
# Edit plist: restore original Hour/Minute/Weekday
launchctl load ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist
```

Verify:
```bash
grep -A1 "StartCalendarInterval" ~/Library/LaunchAgents/com.jcrawley.hendrick-pb-report.plist | head -20
```

Expected output: matches the original values noted in Step 1.

---

### Task 8: Nalley parity + double-MFA verification

**Purpose:** Confirm the Nalley workflow handles the potential double-MFA (Tableau then admin.cars.com) correctly, and that the sub-procedure is idempotent across invocations.

**Files:**
- No file changes. This is an integration test.

- [ ] **Step 1: Start the workflow interactively**

Run in a fresh Terminal window:
```bash
claude -p "/nalley-pb-report" --allowedTools "Bash,Edit,Read,Write,mcp__tableau__*,mcp__gmail__*,mcp__playwright__*" 2>&1 | tee /tmp/nalley-pb-attended-$(date +%Y%m%d-%H%M%S).log
```

- [ ] **Step 2: Observe MFA challenges**

Watch the Playwright browser window for the duration of Step 1 (Tableau) and Step 2 (admin.cars.com). Count how many JumpCloud MFA challenge pages appear: 0, 1, or 2. Note the count.

- [ ] **Step 3: Confirm all challenges were auto-resolved**

For each MFA page observed:
- 6-digit code appears in the Verification Code input.
- Form submits.
- Browser redirects away from sso.jumpcloud.com.

- [ ] **Step 4: Confirm end-to-end completion**

Let the workflow continue through Step 3 QC and Step 4 Gmail draft. Confirm the Nalley Gmail draft appears in the Drafts folder (addressed to Grayson/Jason/Zlatan/Rashad, CC Shashank).

- [ ] **Step 5: Record the MFA count in a memory note**

If the MFA fired **twice** (no cookie carryover), note this in a new memory entry — it affects the Nalley failure surface area. If it fired **once** (cookie carryover), note that too. Useful for the next time the workflow breaks:

```bash
cat <<'EOF' > ~/.claude/projects/-Users-jcrawley/memory/reference_nalley_mfa_count.md
---
name: Nalley PB MFA Challenge Count
description: On 2026-04-21 live test, the Nalley PB workflow fired N JumpCloud MFA challenge(s) per run (Tableau then admin.cars.com)
type: reference
---

[Fill in N=1 or N=2 based on the test observation. If N=1, admin.cars.com reused the Tableau session cookie. If N=2, each host challenges independently.]
EOF
```

Edit the file to fill in the observed N value and add a line to `~/.claude/projects/-Users-jcrawley/memory/MEMORY.md`:

```
- [Nalley PB MFA Challenge Count](reference_nalley_mfa_count.md) — N JumpCloud MFA challenges per Nalley run (observed 2026-04-21)
```

---

### Task 9: Rollback test

**Purpose:** Verify the Step 0 pre-flight aborts cleanly when the Keychain entry is missing — confirms the error surfaces rather than hanging.

**Files:**
- No file changes. This manipulates Keychain state temporarily.

- [ ] **Step 1: Delete the Keychain entry**

Run:
```bash
security delete-generic-password -s jumpcloud-totp -a jcrawley
```

Expected output: a "password has been deleted" confirmation.

- [ ] **Step 2: Run the helper directly — expect exit 2**

Run:
```bash
~/.claude/scripts/jumpcloud-totp.sh; echo "exit=$?"
```

Expected output on stderr:
```
jumpcloud-totp: Keychain entry jumpcloud-totp/jcrawley missing — see ~/docs/superpowers/specs/2026-04-21-jumpcloud-totp-fallback-design.md §One-time setup
```

Exit code: `exit=2`.

- [ ] **Step 3: Run the skill — expect clean Step 0 abort**

Run:
```bash
claude -p "/hendricks-pb-report" --allowedTools "Bash,Edit,Read,Write,mcp__tableau__*,mcp__gmail__*,mcp__playwright__*" 2>&1 | head -40
```

Expected: the skill reports Step 0 failure with the helper's error message, and aborts before touching Tableau.

- [ ] **Step 4: Restore the Keychain entry**

Run (replace `<BASE32_SEED>` with the seed from Task 0 Step 3; you should still have it in 1Password):
```bash
security add-generic-password -s jumpcloud-totp -a jcrawley -w '<BASE32_SEED>' -U
```

- [ ] **Step 5: Verify restoration**

Run:
```bash
~/.claude/scripts/jumpcloud-totp.sh | grep -E '^[0-9]{6}$' && echo "restored OK"
```

Expected output: a 6-digit code and `restored OK`.

---

## Spec Coverage Check (self-review)

| Spec section | Implementing task(s) |
|---|---|
| One-time setup (Reset + Keychain + brew) | Task 0 |
| Helper script contract + pseudocode | Task 1 |
| Skill Step 0 expansion (Hendrick) | Task 2 |
| JumpCloud MFA Sub-procedure (Hendrick) | Task 3 |
| Skill Step 0 expansion (Nalley) | Task 4 |
| JumpCloud MFA Sub-procedure (Nalley), dual-reference | Task 5 |
| launchd plists unchanged | (no task — spec says no changes) |
| Testing Plan §1 (helper unit-ish) | Task 1 Step 5–6 |
| Testing Plan §2 (live attended — Hendrick) | Task 6 |
| Testing Plan §3 (unattended dry run) | Task 7 |
| Testing Plan §4 (Nalley parity + double-MFA) | Task 8 |
| Testing Plan §5 (rollback test) | Task 9 |
| Rollback (file restore from /tmp backups) | Task 1 Step 7, Task 2 Step 1, Task 4 Step 1 |

No spec requirements are unassigned to a task.
