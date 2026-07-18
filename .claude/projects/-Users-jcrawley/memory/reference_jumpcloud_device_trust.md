---
name: jumpcloud-device-trust
description: JumpCloud SSO blocks isolated/unmanaged Playwright browser profiles from reaching admin.cars.com even with valid creds+MFA
metadata: 
  node_type: memory
  type: reference
  originSessionId: 45f5ce84-91b4-4396-b164-642a69e19ce9
---

JumpCloud enforces a device-trust / managed-device conditional-access policy on the `webadmin` SAML app that fronts admin.cars.com. An isolated (`--isolated`) or otherwise fresh/unmanaged Playwright browser profile will authenticate successfully (username, password, TOTP all pass) but then get redirected with `error=policyDenial` and the message "Access to company data is restricted to company managed computers" — this is an IdP-side check, not a credentials/MFA failure, and cannot be worked around via browser automation.

**Why:** Confirmed empirically 2026-07-13 while pulling EchoPark demand data — an isolated browser profile completed full login+MFA but was denied at the SSO redirect step specifically for admin.cars.com. Never attempt to spoof device-trust signals.

**How to apply:** For admin.cars.com automation, always use the existing persistent/default Playwright MCP profile (already trusted by JumpCloud, used by scheduled PB reports) — never spin up an isolated instance as a workaround for a locked profile. If that profile is locked by another live process, wait for it to free up (or verify it's stale before closing) rather than isolating. See [[reference_login_flows]] and [[project_totp_fallback_paused]] for the unattended-login credential chain (Keychain: jumpcloud-username/password/totp).

Also noted in the same session: when scripting Keychain lookups (`security find-generic-password`), never pipe the secret through `head`/`echo`/print for verification — even a partial character count getting into an agent's own tool output/report is an avoidable exposure. Retrieve and use in one step.

**Confirmed working 2026-07-17:** `pb-profile` (`~/Library/Caches/ms-playwright-mcp/pb-profile`) is admin.cars.com-trusted — a standalone `python3` script using `playwright.sync_api` + `launch_persistent_context(PROFILE_DIR)` against this profile reached the Connections & Contact Details report with no `policyDenial`, matching a manual chrome-devtools pull exactly. Built for [[project_market_metrics_weekly]]. If a future admin.cars.com automation needs a trusted profile, reuse `pb-profile` rather than building a new one — but coordinate scheduling to avoid two processes touching it at once (see [[reference_scheduling_architecture]]).
