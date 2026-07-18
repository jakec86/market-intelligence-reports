---
name: JumpCloud TOTP Fallback — Paused Awaiting IT Reset
description: PB Report TOTP fallback (spec + plan + skill edits + Python helper) is built and code-reviewed. Task 0 (Keychain seed store) blocked — user cannot self-serve reset at JumpCloud because current TOTP seed isn't accessible to them (phone has push only, 1Password entry unclear). Awaiting IT ticket to clear the Authenticator App enrollment.
type: project
originSessionId: 95102df3-22c8-4e5d-ae8a-42f14c4accc3
---
**Status as of 2026-05-18 (RESOLVED):**

IT cleared the Authenticator App enrollment. User re-enrolled, captured base32 seed, stored in Keychain via `security add-generic-password -s jumpcloud-totp -a jcrawley -w '<SEED>' -U`, and verified with `~/.claude/scripts/jumpcloud-totp.py`. TOTP is now active and generating valid codes. Unattended PB report TOTP fallback is fully unblocked — proceed to Tasks 6–9 (live attended test, unattended dry run, Nalley parity, rollback).

**Status as of 2026-05-08:**

**Mobile Push is now the primary MFA method** — user confirmed TOTP is on hold indefinitely until IT provides enrollment. Nalley PB skill updated: Mobile Push is Step 1 (send push → notify user to approve on phone → wait for redirect). TOTP is a secondary fallback block, only attempted if Keychain seed is enrolled. Do NOT ask about TOTP status each session — user will update when IT provides the reset.

**Status as of 2026-05-04:**

**TOTP pre-flight check bypassed in PB report workflows** — user instructed to skip the Step 0 TOTP check and proceed without it until the Keychain seed is in place. If JumpCloud SSO is hit during a workflow, user will approve via Mobile Push manually.

---

**Status as of 2026-04-22:**

**Implementation complete (tracked artifacts):**
- Spec: `~/docs/superpowers/specs/2026-04-21-jumpcloud-totp-fallback-design.md`
- Plan: `~/docs/superpowers/plans/2026-04-21-jumpcloud-totp-fallback.md`
- Helper: `~/.claude/scripts/jumpcloud-totp.py` (Python stdlib-only; RFC 6238; whitespace-tolerant; handles missing `security` binary)
- Hendrick skill: Step 0 TOTP pre-flight + JumpCloud MFA Sub-procedure + Step 1 ref
- Nalley skill: Step 0 TOTP pre-flight + JumpCloud MFA Sub-procedure + dual refs (Step 1 Tableau, Step 2 admin.cars.com)
- SessionStart MCP health hook in `~/.claude/settings.json`
- Backup copies at `/tmp/totp-backups/` (also `*.pre-totp` of original skill files)

**Pivot history:**
- Originally targeted `oath-toolkit` (Homebrew). Homebrew not installed → pivoted to pure-Python helper (zero external deps).

**Blocker:** Task 0 — user cannot complete JumpCloud Authenticator App reset. The reset dialog requires a current 6-digit code to verify the existing enrollment. User's phone only has Mobile Push enrolled (no authenticator app), and the seed location at original enrollment is unclear.

**How to apply:**
- Next session should ask: has the IT ticket been filed / resolved? If admin cleared the Authenticator App enrollment, the row will show "Not Enrolled" and the user can enroll fresh (QR → capture base32 → `security add-generic-password -s jumpcloud-totp -a jcrawley -w '<SEED>' -U`).
- After Task 0 completes, resume at Tasks 6 (live attended), 7 (unattended dry run), 8 (Nalley parity + double-MFA count), 9 (rollback).
- Code-review hardening already applied: whitespace translation, FileNotFoundError catch, redacted exception in invalid-seed path, `sleep $(( (30 - ... % 30) % 30 ))` boundary-wait fix in both skills.

**Why:** Unattended PB Report workflows stall on JumpCloud push-timeout at 6 AM MST. TOTP fallback eliminates the push dependency.
