---
name: login-flows-for-mcp-services
description: "SSO and Google login steps needed when Playwright browser session is fresh — admin.cars.com uses JumpCloud SSO, Gmail/Sheets need Google sign-in"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7283b1ef-19ff-4923-84dd-82f2df7755c4
---

**admin.cars.com**
- SSO via JumpCloud (console.jumpcloud.com)
- Email pre-fills as jcrawley@cars.com
- After clicking Continue, password page appears (Chrome auto-fills)
- MFA: prefer TOTP via `python3 ~/.claude/scripts/jumpcloud-totp.py`; fall back to push if TOTP unavailable

**Gmail / Google Sheets (Playwright)**
- Playwright browser sessions don't persist Google login
- Must sign in at accounts.google.com with jcrawley@cars.com (or @carscommerce.inc — confirm which works)
- Google Sheets can be accessed without sign-in for shared sheets, but editing and Gmail require auth
- Once signed into one Google service, others work in that session

**DealerRater**
- Uses Cars.com / METAL SSO (login.carscommerce.inc)
- Login is **email-only** — no password required
- Fill email field with `jcrawley@cars.com`, click "Sign In" — done
- Works in both interactive Chrome and headless Playwright
