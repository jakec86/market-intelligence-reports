---
name: reference_ga4_rest_access
description: How to query dealer GA4 properties — MCP analytics tools are broken; use REST with the OAuth refresh tokens
metadata: 
  node_type: memory
  type: reference
  originSessionId: 98ea4c28-b506-4635-9df4-5a55c3dd49b4
---

The `google-analytics-gafield` / `gafield1` MCP tools FAIL on these accounts: the token files (`~/.claude/ga_tokens/gafield_adc.json`, `gafield1_adc.json`) are OAuth `authorized_user` creds, but the MCP binary expects a service account → errors `does not contain a client_email field`. This is the "OAuth REST only" note in [[project_ecarone_ga_reporting]].

**Working path: call the GA4 Data API directly.** Refresh the access token from the cred file (`client_id`/`client_secret`/`refresh_token` → `https://oauth2.googleapis.com/token`), then POST to `https://analyticsdata.googleapis.com/v1beta/properties/{id}:runReport`. Pattern script: `/tmp/ga_*.py` from this work, or mirror the auth block in `~/Documents/scripts/reformat_cs_doc_v2.py`.

**Credential scope (not what the names imply):**
- `gafield_adc.json` = the **Longo / agency book** — many dealers (Longo Lexus/Toyota, LSC, Lynch, Germain, etc.). Does NOT have Don Franklin.
- `gafield1_adc.json` = eCarOne (326694710) **plus** Don Franklin Lexington: **Buick GMC = 467758077**, **Hyundai = 467133052**. Use gafield1 for Don Franklin.
- List accessible props per cred: GA Admin API `accountSummaries`.

**Useful dims/metrics:** `sessionDefaultChannelGroup`, `sessionSourceMedium`, `sessionSource`/`sessionMedium`/`sessionCampaignName`, `deviceCategory`, `city`, `eventName`, `landingPagePlusQueryString`; metrics `sessions`, `engagementRate`, `newUsers`, `totalUsers`, `eventCount`. `dimensionFilter` with EXACT `stringFilter` works to isolate a campaign.
