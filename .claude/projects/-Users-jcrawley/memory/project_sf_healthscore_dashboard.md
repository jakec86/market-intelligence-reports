---
name: SF Health Score Dashboard Integration
description: Salesforce Health Scores as alternative data source for Dealer Health Dashboard — faster than waiting for Atlan/Redshift
type: project
originSessionId: 34409d72-3f6a-4a50-a703-aebd30cf0d26
---
## SF Health Score → Dealer Health Dashboard

Identified 2026-04-13 during GTM AMA on "Health Scores and Retention Records."

**Idea:** Use SF Health Score fields as a data source for the Dealer Health Dashboard, potentially bypassing the Tableau row-level security block and admin.cars.com scraping requirement.

**Why:** Atlan API token + Redshift credentials are still pending (requested 2026-04-10). SF CLI already works in the dashboard. If Health Score fields exist on the Account object, this is the fastest path to enriching the health snapshot.

**Next steps:**
1. Query SF schema to find Health Score fields: `sf sobject describe Account` or SOQL describe
2. Check if Retention Records are standard or custom objects
3. If usable, add to `dealer_health.py` SF query alongside existing account fields
4. This approach complements (not replaces) Atlan — Atlan gives VDPs/SRPs/connections/badges, SF gives health scores/retention

**How to apply:** When working on the Dealer Health Dashboard, explore SF Health Score fields before building admin.cars.com scraper. Two-track approach: SF Health Scores (fast, available now) + Atlan SQL (comprehensive, pending access).
