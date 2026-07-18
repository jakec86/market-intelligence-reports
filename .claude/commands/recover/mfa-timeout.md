# Recovery Agent: JumpCloud MFA Timeout / TOTP Failure

Invoked when a JumpCloud SSO challenge cannot be completed — push not approved, TOTP rejected, or no MFA option available.

**Autonomy level: PARTIAL** — TOTP is fully autonomous if the Keychain seed is present. Push timeout always requires the human to approve on their phone.

---

## What This Failure Means

| Signal | Root Cause |
|--------|-----------|
| Push notification sent but no redirect after 90s | User didn't approve on phone, or JumpCloud app notification wasn't received |
| TOTP rejected twice | Mac clock drifted, or the Keychain seed doesn't match current JumpCloud enrollment |
| "No TOTP option" on SSO page | JumpCloud default factor is set to Push; need to click "Try another way" |
| `security find-generic-password` exits non-zero | TOTP seed not enrolled in Keychain — can only use push |

---

## Recovery Decision Tree

```
MFA challenge detected
├─ Is TOTP seed in Keychain?
│   ├─ YES → Try TOTP (Steps 1–3)
│   └─ NO  → Fall back to Push (Step 4)
│
TOTP attempted
├─ Accepted → Continue ✓
└─ Rejected twice
    ├─ Check Mac clock (Step 5)
    └─ Clock OK → Seed mismatch → Escalate (Step 6)
```

---

## Recovery Steps

### Step 1 — Check Keychain for TOTP seed

```bash
security find-generic-password -s "jumpcloud-totp" -a "jcrawley" -w 2>/dev/null
```

- **Returns a seed:** Proceed to Step 2
- **Returns nothing / error:** Jump to Step 4 (Push fallback)

### Step 2 — Switch SSO page to TOTP input

On the JumpCloud SSO page:
1. If only a "Send Push" button is visible, click "Try another way" or "Use authenticator code"
2. The Verification Code input field must be visible before proceeding
3. If no TOTP option is available at all → jump to Step 4

### Step 3 — Generate and submit TOTP code

```bash
python3 ~/.claude/scripts/jumpcloud-totp.py
```

- Type the 6-digit code into the Verification Code field
- Click Submit/Verify
- Wait up to 10s for redirect away from `sso.jumpcloud.com`
- **If rejected:** wait for next 30s TOTP boundary, generate fresh code, retry once
- **If rejected twice:** jump to Step 5

### Step 4 — Push fallback

Click "Send Push". Output:
```
⏳ JumpCloud push sent — approve on your phone to continue.
```
Poll every 5s for up to 90s for redirect away from `sso.jumpcloud.com`. If no redirect after 90s:

```
⚠️ ESCALATE: Push not approved after 90 seconds.
Action required: Check JumpCloud app on your phone and approve the push, then type 'continue'.
```

Wait for human confirmation, then check if the page has redirected.

### Step 5 — Diagnose clock drift (TOTP rejected twice)

```bash
sudo sntp -sS time.apple.com
date
```

If clock was off by >30s, the sync fixes it. Generate a fresh code and retry once more.

### Step 6 — Escalate: seed mismatch

```
⚠️ ESCALATE: TOTP rejected despite clock sync.
The Keychain seed likely doesn't match the current JumpCloud enrollment.

Action required:
  1. Log into console.jumpcloud.com/userconsole → Security → MFA
  2. Check which authenticator app is enrolled
  3. If enrolled: scan the QR code and update Keychain:
     security add-generic-password -a jcrawley -s jumpcloud-totp -w <NEW_SEED> -U
  4. Or contact IT to reset the TOTP factor
Workflow state saved at checkpoint — resume after MFA is working.
```

---

## Checkpoint Contract

On TOTP success: `cp.step("mfa_completed", {"method": "totp"})`

On push success: `cp.step("mfa_completed", {"method": "push"})`

On escalation: `cp.fail("mfa_completed", "MFA could not be completed — human action required", kind="mfa-escalation")`
