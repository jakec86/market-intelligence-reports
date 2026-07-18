---
name: Atlan & Redshift Access Requests Pending
description: "Atlan catalog SOLVED via claude.ai OAuth connector (2026-06-10); only remaining blocker is per-user Redshift query credentials for SQL"
type: project
originSessionId: 5e89c129-f77f-4999-ae43-9da2b2dff386
---
## ✅ RESOLVED (2026-06-10): Atlan catalog access — no API token needed

The **claude.ai "Atlan - carscommerce" connector** (Atlan-hosted MCP endpoint at
`https://carscommerce.atlan.com/mcp`) now works via OAuth — Jake authenticated via
`/mcp` with normal SSO. The April API-token request is moot for catalog access.

**Working tools (26 total):** `semantic_search_tool` (NL search, returns full view
DDL/definitions), `search_assets_tool`, `get_asset_tool`, `traverse_lineage_tool`,
glossary/tag/domain tools. Catalog browse + schema discovery for all 617K assets
works today. Avoid the write tools (tags/glossaries/domains/lifecycle).

The local `uvx atlan-mcp-server` + `ATLAN_API_KEY` plan is no longer needed unless
headless runs require it (claude.ai connectors may be absent in headless sessions).

## ⛔ STILL BLOCKED: SQL execution (`query_assets_tool`)

Tested 2026-06-10 against both Redshift connections — both return
`INVALID_CREDENTIALS: Connection requires user credentials for querying`:
- `redshift-prod` → `default/redshift/1662759587`
- `rs-prod-consumer` → `default/redshift/1698171927`

Atlan passes through **per-user Redshift credentials** (set in the user's Atlan
profile / Insights query prompt) — there is no shared service account on these
connections. Jake has no personal Redshift credentials.

**The single remaining ask** (in #data_all or the #data_governance_communications
thread, to Ralf Kloeckner's team):
> Could I get read-only Redshift credentials for the dw database (host
> dw.data-prod.cars.com:5439) to use with Atlan Insights?

Once received: add them in Atlan profile → query credentials. `query_assets_tool`
then works immediately — no config changes needed on the Claude side.

**Redshift connection details:** Host `dw.data-prod.cars.com`, port `5439`,
database `dw`, basic auth (also supports IAM).

**Why this matters:** direct SQL via [[cars-commerce-data-warehouse]] views
(`dw_vw.customer_vw`, `agg_vehicle_metric_daily_vw`, `dw.lead`) replaces Tableau
CSV scraping + admin.cars.com Playwright pulls in the PB/monthly report workflows.
Catalog access already lets us design those queries now (exact columns + DDL).
