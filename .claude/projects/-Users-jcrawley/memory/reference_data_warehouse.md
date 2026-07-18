---
name: Cars Commerce Data Warehouse & Query Library
description: Redshift-based data warehouse schemas, key tables, data sources, and Confluence SQL query library — maps to admin.cars.com, Tableau, and dealer reporting data
type: reference
originSessionId: e7ffdfe1-f939-4972-84b9-5148810c9196
---
## Data Warehouse Platform
- **Amazon Redshift** (confirmed from SQL syntax + explicit "redshift" reference in queries)
- **SAP BOBI** was the legacy BI layer on top — being retired, replaced by Cars Commerce Hub (launched Jan 2026)
- **Atlan** active at `carscommerce.atlan.com` for data governance/catalog — 617K assets cataloged; Jake has Member/Data Analyst role (no Admin for API tokens — requested via #data_governance_communications 2026-04-10)
- **DataGrip** used for direct Redshift SQL queries (not installed on Jake's Mac — may be on another machine)
- **BigQuery** project `claude-integration-491419` exists (empty) — possibly intended as federated query layer

## Atlan Catalog Structure
- **Connection:** `rs-prod` (Redshift production) → database `dw` → 54K assets
- **Connectors available:** Airflow (airflow-prod), Glue (atlan-glue-spark, glue-np, glue-prod), Postgres (dms-reporting-np-v2, dms-reporting-v2-prod), Redshift (rs-prod)
- **Jake's Atlan personas:** CDP Feature Store, Business User, Marketing, Data Science, Dealer Inspire
- **MCP integration:** Atlan MCP server plugin available (`github.com/atlanhq/agent-toolkit`) — requires API token (Admin must generate); pending request submitted 2026-04-10

## Key Schemas & Tables (confirmed in Atlan 2026-04-10)

| Schema | Purpose | Key Tables | Usage (queries) |
|---|---|---|---|
| `dw.dw` | Core warehouse | `lead` (116 cols, 412q), `customer_daily` (185 cols, 37q), `agg_vehicle_metric_daily` (83 cols, 29q), `agg_vehicle_metric_monthly` (82 cols) | High |
| `dw.dw_vw` | Warehouse views (310 views) | `customer_vw` (242 cols, **964q**), `customer_daily_vw` (248 cols, 327q), `agg_vehicle_metric_daily_vw` (84 cols, **380q**), `agg_vehicle_metric_monthly_vw` (83 cols) | Highest — use these for queries |
| `dw.master_data` | Master/reference | `customer` (CCIDs), `accutrade_dealer`, `vehicle` (**594M rows**, 152 cols, 21q) | Medium |
| `dw.insight` | Analytics | `search_activity_raw` (82 cols, 129q) — search results, impressions, clicks, connections per listing | Medium |
| `dw.di_data_restricted` | Restricted/PII | `accounts` (Online Shopper, 21 cols) | Low |
| `dw.enrich` | Enrichment | `adobe_analytics_enrich` | Low |
| `stream_data.*` | Real-time streams | `dc_dealership_stream` (DealerClub) | Low |
| `raw_ext*` | Rudderstack raw events | Clickstream event data | Low |

## Data Sources Feeding the Warehouse
- **Rudderstack** — CDP/event tracking (replaces Segment)
- **Amplitude** — product analytics (trip_id ↔ device_id mapping)
- **Split** — A/B testing / feature flags
- **Iterable** — email marketing campaigns
- **LenderDesk** — financing/incentive data

## Mapping to Current Manual Workflows
- admin.cars.com Performance Trends → `dw_vw.agg_vehicle_metric_monthly_vw` (VDPs, SRPs, connections, inventory, badges)
- Salesforce CCID lookups → `master_data.customer`
- Tableau leads/connections crosstabs → `dw.lead` + lead classification queries
- AccuTrade dealer mapping → `master_data.accutrade_dealer`
- Dealer group aggregate metrics → master queries for traffic, visitors, leads, inventory, ROI, churn

## Confluence SQL Query Library
- **Main page:** https://carscommerce.atlassian.net/wiki/spaces/~712020625527fcd1dc42259bd5835a5b5596e5/pages/3664413291/Data+Warehouse+Data+Lake+SQL+Query+Library
- **Author:** Ralf Kloeckner
- **Subpages:** SQL Query Library Main Page, PostGreSQL database powering Customer Insights API, Amplitude Links
- Contains master queries for: lead classification, sales attribution, dealer metrics, ROI, churn prediction, listing optimizer, vehicle metrics, experiment analysis

## Key Fields
- `customer_legacy_id` = CCID
- `ultimate_parent_customer_legacy_id` = parent dealer group CCID
- `customer_id` = internal ID (joins across dw tables)

## Mapping to Manual Report Workflows
| Manual Workflow | Replacement Query Source |
|---|---|
| admin.cars.com Performance Trends (VDPs, SRPs, connections, inventory, badges) | `dw_vw.agg_vehicle_metric_daily_vw` / `agg_vehicle_metric_monthly_vw` |
| Tableau LEI crosstab (Price Badge Report) | `dw_vw.agg_vehicle_metric_daily_vw` + badge columns |
| Salesforce CCID lookups + product checks | `dw_vw.customer_vw` (964 queries — most used view) |
| Tableau leads/connections crosstabs | `dw.lead` (412 queries) |
| Search/SRP activity | `insight.search_activity_raw` |

## Next Steps to Enable Direct Access
1. ~~Request read-only Redshift access from data team (Ralf Kloeckner or #data_all)~~ → Pending: API token request submitted to #data_governance_communications (2026-04-10)
2. Once token received: configure Atlan MCP server in `~/.claude/settings.json` using `uvx atlan-mcp-server` with `ATLAN_API_KEY` + `ATLAN_BASE_URL=https://carscommerce.atlan.com`
3. Test `query_asset` tool for direct SQL against Redshift through Atlan
4. If direct query works: replace Tableau CSV exports + admin.cars.com scraping + SF CLI for most reporting workflows
5. Ask if BigQuery project is meant to federate into Redshift
