# JumpCloud TOTP Fallback for Unattended PB Report Workflows

**Date:** 2026-04-21
**Status:** Design approved; ready for implementation plan
**Author:** Jake Crawley (jcrawley@cars.com) with Claude Code

## Problem

Scheduled Price Badge Report workflows (`/hendricks-pb-report` Mondays 6 AM MST, `/nalley-pb-report` Mondays and Fridays 6 AM MST) stall when Tableau or admin.cars.com trigger a JumpCloud SSO challenge that defaults to push-notification MFA. Push requires a live phone tap within the JumpCloud timeout window; for 6 AM launchd runs this is unreliable and has caused multiple workflow failures (per the 2026-04-20 Claude Code insights report and existing memory on JumpCloud MFA friction).

TOTP (Time-based One-Time Password) is already Active as a second factor on the JumpCloud account but currently lives in a phone authenticator app only, not in any form the scheduled workflow can retrieve.

## Goal

Enable both PB Report workflows to pass the JumpCloud MFA challenge unattended by retrieving a current TOTP code from local storage and submitting it via Playwright — eliminating the push-timeout stall as a failure mode.

**In scope:** Hendrick PB and Nalley PB workflows only.

**Out of scope:**
- Other JumpCloud-gated workflows (eCarOne VPM, Herb Chambers DR, market intelligence)
- Non-JumpCloud MFA
- Remote-host execution
- Enrollment for accounts other than `jcrawley@cars.com`

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Secret storage | macOS login Keychain via `security` CLI | Encrypted at rest; accessible to user-level launchd agents while logged in; no dependency on 1Password app running |
| TOTP generator | `oathtool` from `oath-toolkit` | Small, deterministic CLI; reads seed on stdin; widely available via Homebrew |
| Helper form | Shell script at `~/.claude/scripts/jumpcloud-totp.sh` | Six lines; skills call it as a subprocess; no need for Python overhead |
| Keychain service name | `jumpcloud-totp` | Descriptive; prefixed to prevent collision with any future JumpCloud-related entries |
| Keychain account | `jcrawley` | User's UNIX login |
| Retry policy on code rejection | One retry with fresh code, then abort | Balances clock drift tolerance against runaway loops |
| Launchd plists | **No changes** | Existing plists already run as user agents; Keychain is accessible in that context |

## Architecture

```
launchd (Mon/Fri 6 AM MST)
      ↓
claude -p /hendricks-pb-report  (or /nalley-pb-report)
      ↓
Step 0 — Pre-flight checks
      • MCP health (tableau, gmail, playwright — existing)
      • TOTP readiness (new): `oathtool` binary + Keychain entry present
      ↓
Step 1 — Tableau download (Playwright)
      ↓
  [JumpCloud SSO page appears]
      ↓
  helper: security → oathtool → 6-digit code
      ↓
  Playwright fills TOTP input, submits
      ↓
Step 2+ — normal workflow (CSV → sheet → Gmail draft)
```

## Components

### 1. One-time setup (user-driven, attended)

**Done once before first unattended run:**

1. At `console.jumpcloud.com/userconsole` → Security → Multi-Factor Authentication, click **Reset** next to "Authenticator App". This invalidates the existing phone registration and generates a new QR.
2. Click JumpCloud's "Can't scan?" / "Show secret" link to reveal the base32-encoded seed as text.
3. Scan the QR into 1Password (and optionally the phone authenticator) for redundancy.
4. Store the seed in the login Keychain:
   ```bash
   security add-generic-password -s jumpcloud-totp -a jcrawley -w '<BASE32_SEED>' -U
   ```
5. Install `oathtool`:
   ```bash
   brew install oath-toolkit
   ```
6. Install helper script and make executable (see Component 2).

### 2. Helper script — `~/.claude/scripts/jumpcloud-totp.sh`

**Purpose:** Print a current 6-digit TOTP code to stdout, or exit non-zero with a clear error.

**Contract:**
- Exit 0 with 6 ASCII digits + newline on stdout → success
- Exit 2 → missing dependency or missing secret (actionable operator error)
- Exit 3 → `oathtool` execution failed (unexpected)
- Never writes to stderr unless failing
- Never logs the seed or the code anywhere

**Pseudocode:**

```bash
#!/bin/bash
set -euo pipefail

command -v oathtool >/dev/null || { echo "oathtool missing — brew install oath-toolkit" >&2; exit 2; }
seed=$(security find-generic-password -s jumpcloud-totp -a jcrawley -w 2>/dev/null) || {
  echo "Keychain entry jumpcloud-totp/jcrawley missing — see setup doc" >&2; exit 2;
}
oathtool --totp -b "$seed" || exit 3
```

### 3. Skill updates — `hendricks-pb-report.md` and `nalley-pb-report.md`

**Changes to both files:**

- **Step 0 pre-flight** gains two new checks:
  - `command -v oathtool` returns 0
  - `security find-generic-password -s jumpcloud-totp -a jcrawley -w` returns 0 (seed present; output discarded)
- **JumpCloud MFA branch** (new reusable section in each skill): when Playwright lands on a JumpCloud SSO challenge page:
  1. Detect the factor form:
     - If a visible "Verification Code" input field is present → proceed to code submission
     - If only "Send Push" is visible → click "Try another way" or the TOTP selector link to reveal the code input
     - If neither appears → abort with a clear error pointing at the "prompt order" unknown
  2. Call the helper to get a current code
  3. Fill the TOTP input, submit
  4. On failure (page re-prompts with "invalid code"), retry once with a fresh code, then abort

**Nalley-specific:** the MFA branch may execute **twice** in one run (once for Tableau, once for admin.cars.com) if JumpCloud does not reuse the session cookie across those hosts. The MFA branch is written once in the skill as a named sub-procedure and referenced from both the Tableau step and the admin.cars.com step.

### 4. launchd plists

No changes. The existing user-agent plists already run in a context where `security` (Keychain) is available.

`caffeinate` requirement from CLAUDE.md still applies (Mac must be awake; already documented).

## Data Flow

**At runtime, for a single MFA challenge:**

1. Playwright detects JumpCloud SSO redirect
2. Skill invokes `~/.claude/scripts/jumpcloud-totp.sh`
3. Helper reads seed from Keychain → pipes to `oathtool` → prints 6-digit code
4. Skill captures stdout into a variable (never logged)
5. Playwright types code into the TOTP input field, clicks submit
6. Skill waits for post-MFA navigation to complete; proceeds with download

**Secret never appears in:** skill logs, Playwright traces, stdout of the outer `claude -p` invocation, or the launchd log files.

## Error Handling

| Failure | Caught by | Behavior |
|---|---|---|
| `oathtool` not installed | Step 0 | Abort; error lists `brew install oath-toolkit` |
| Keychain entry missing | Step 0 | Abort; error lists the `security add-generic-password` command |
| Keychain access denied (login keychain locked) | Helper | Abort; instruct user to unlock via Keychain Access.app |
| JumpCloud shows push-only page, no "Try another way" | Skill MFA branch | Abort with "prompt order unresolved — change default factor at console.jumpcloud.com" |
| Code rejected on first attempt | Skill MFA branch | Wait for 30s boundary if near rollover, retry once, then abort |
| Seed revoked (user reset TOTP and forgot to update Keychain) | Skill MFA branch | Same path as "code rejected"; operator re-runs one-time setup |
| Clock skew > 30s | Skill MFA branch | Error message suggests `sudo sntp -sS time.apple.com` |

## Testing Plan

1. **Helper unit test:** run `~/.claude/scripts/jumpcloud-totp.sh` three times across a 60-second window; confirm 6-digit output that rotates exactly once at the 30-second boundary.
2. **Live attended test:** run `/hendricks-pb-report` interactively; when JumpCloud prompts for MFA, let the skill submit the code while you watch; confirm Step 1 completes without a push challenge.
3. **Unattended dry run:** re-schedule the Hendrick launchd plist to fire in ~5 minutes (edit `StartCalendarInterval` temporarily); lock the screen; confirm the log shows MFA pass-through and the workflow completes through Gmail draft.
4. **Nalley parity + double-MFA:** same protocol for Nalley; observe whether the second MFA challenge fires on admin.cars.com; confirm the reusable branch handles both.
5. **Rollback test:** temporarily revoke the Keychain entry (`security delete-generic-password ...`), run the skill, confirm clean Step 0 abort with the documented error message.

## Unresolved Questions

Two questions are deferred until first live run — their answers affect only the JumpCloud MFA branch implementation, not the architecture:

1. **Prompt order:** does JumpCloud default to the TOTP input or to push when Tableau/admin.cars.com redirect to SSO? The skill will handle both; first live run will show which is actually seen.
2. **SSO session carryover:** does admin.cars.com reuse the Tableau JumpCloud cookie? The Nalley skill will branch on whether a second MFA page appears.

Both questions resolve empirically during testing step 4.

## Rollback

If the fallback misbehaves, rollback is a two-line change per skill: revert Step 0 TOTP pre-flight and the MFA-branch addition. The Keychain entry and helper script are inert when no skill calls them, so they can be left in place.

## Security Posture

- Seed encrypted at rest (Keychain AES-128 GCM)
- No plaintext seed on disk outside Keychain
- Seed accessible only while login keychain is unlocked (i.e., user logged in)
- Code and seed never logged
- Seed rotation: operator can re-run JumpCloud TOTP Reset at any time; updating Keychain is one `security add -U` command
- No net-new attack surface beyond the existing user account — stealing the seed requires either an already-authenticated user session or physical access to the unlocked Mac, both of which already grant broader access to the PB workflow credentials
