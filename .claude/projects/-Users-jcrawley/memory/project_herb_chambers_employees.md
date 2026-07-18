---
name: Herb Chambers Employee Profile Updates
description: Quarterly DealerRater employee audit for Herb Chambers (~24 stores) — cross-reference website team pages with DR profiles, update adds/removes/titles
type: project
---

Herb Chambers quarterly DealerRater employee profile update.

- **~24 active stores** in MA and RI (27 DealerRater listings — some stores split across multiple DR entries)
- **Report folder:** ~/Documents/Reports/HerbChambers/
- **Skill:** `/herb-chambers-employee-update`
- **Store lookup:** herb_chambers_store_lookup.json (CCIDs, DR IDs, websites, products)
- **Schedule:** Quarterly, manually triggered

**Data sources:**
- DealerRater employee pages (public, WebFetch works) — structured name/title/department
- Dealer website staff pages (`/dealership/staff.htm`) — requires Playwright (Cloudflare blocks WebFetch). Staff in `<h3>` tags, titles in adjacent `<p>` tags.
- Salesforce SBQQ subscriptions for active store verification

**First run completed 2026-04-08:**
- 14 of 24 stores had working website staff pages
- 161 employees to add, 111 to remove, ~53 title updates identified
- 10 stores without website staff pages (luxury brands, Lexus, Volvo use different platforms)

**Why:** Dealer group needs employee profiles on DealerRater kept current for review solicitation and reputation management.

**How to apply:** Use `/herb-chambers-employee-update` skill for quarterly updates. DealerRater admin updates are manual via METAL SSO at dealerrater.com/login.
