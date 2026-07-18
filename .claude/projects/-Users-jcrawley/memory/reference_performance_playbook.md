---
name: Marketplace Performance Deep Dive Playbook
description: Cars Commerce internal playbook for proactive dealer account management — investigation scenarios, report references, and escalation paths
type: reference
---

## Document

- **Title:** Marketplace Performance Deep Dive Playbook (Proactive Account Management)
- **URL:** https://docs.google.com/document/d/1r5SnvjAakAbikitNguXrr4vFwmfBkV4RJb1n39-sKzc/edit
- **Classification:** Internal Use
- **Purpose:** Roadmap to identify dealer accounts needing attention; investigation steps for common performance concerns

## Dealer Health Tab

- Links to **Marketplace Dealer Health Metrics** Tableau dashboard (Internal Only)
- Has embedded **GenAI Dealer Metrics** tool (inputs: Major Account Name, Dealer Group Name, Customer Name, Customer ID, CCID, Month, Comparison Month, 30-Day Window, Partial Month, Provide Explanation)
- **Top-row KPIs:** Total Vehicles, Pct Merchandised, Total VDPs, Total Leads (New/Used split), Total Contacts**, Cost Per Lead**, Dealer Ratings**, Cost Per VDP** (** = can't split by stock type)
- **Filters:** Major Cust Name, Group Cust Name, Dealer Name, Sales Director, RSM, AE, DMA, Franchise/Inde
- **Setup:** Select your name → Save Custom View → Subscribe monthly via Watch > Subscriptions

## Investigation Scenarios

### Scenario 1: Drop in Connections (3-4 month consecutive decline)
- **Inventory Display Issues** → check Live Inventory in Inventory Management; review Deeplink Dashboard for deep link status
- **High-Performing Vehicles Removed** → Historical Connections report (check if specific popular units were removed)
- **Low Engaged Inventory** → Low Engaged Inventory report (above-market pricing, high mileage, merchandising problems)
- **Mismatched Inventory to Demand** → Demand Signals report (what local shoppers search for vs. what's on lot)

### Scenario 2: Best Match Concerns (not showing on first page)
- **Replicate the Search** → run the same search; if too broad, reference Consumer Search Behavior doc
- **Algorithm context** → Best Match is ever-evolving; tests for page 1 diversity, better merchandised listings, high CPL dealers with incremental value
- **Evaluate Best Match Factors** → "Best Match" tab in Listings Optimizer (VDPs & connections per VIN by photo bucket, price-to-market, reviews)
- **Radius Performance** → where impressions & leads actually originate

### Scenario 3: Gradual Decrease in VDPs (despite consistent inventory/merchandising)
- **Isolate Stock Type** → is drop in NEW, USED, or both?
- **Check SRPs** → Performance Trends; if SRPs also declining, may be Best Match issue
- **Low Engaged Inventory** → above-market prices, high mileage, merchandising problems
- **Vehicle Demand** → Demand Signals (inventory mix vs. current market demand)

### Scenario 4: Vehicle Demand / Traffic Questions (shopper exposure, popular vehicles, competitive position)
- **Inventory/VDPs/Connections & Zip Codes** → Market Area Planner (SRPs, VDPs, connections by market/make/stock type + zip code detail); Radius Performance (dealer-specific radius view of impressions/leads origin)
- **Vehicles in Demand** → Demand Signals (inventory, VDPs, connections by make/model vs DMA; price-to-market intel; discuss Accu-Trade for acquisition)
- **Competitive Performance** → Competitive Set (anonymous share of inventory, VDPs, connections vs similar market dealers) — **competitor data MUST be masked if shared with dealer**
- **Deeper Market Insights** → Tableau dashboard with trend info and lead data per market

### Scenario 5: Lead Quality or Attribution Issues (dealer claims leads don't convert)
- **Lead Quality Insights** → Dealer Lead Intelligence report + Shopper Details in Dealer Dash (post-submission shopper behavior)
- **Attribution & Sold Vehicles** → Sales Attribution Summary (last connection type before vehicle removed; VIN-level attributions from cars.com to sold vehicles; estimated dollar value)
- **CRM lead issues** → open a case with support@cars.com

### Scenario 6: Walk-in Demand / Lot Insights Missing Dealer (no data, "not mapped" notice)
- **For AEs/Reps** → contact support team to fix mapping in Radar tool (lat/long)
- **For Support Teams** → log into Radar tool, adjust address/lat/long; handle duplicate dealer names; reference Tableau report for mapped stores

## Key admin.cars.com Reports Referenced

| Report | Use Case |
|--------|----------|
| Performance Trends | MoM metrics overview (inventory, VDPs, connections, badges) |
| Demand Signals | Make/model demand vs. inventory, price comparison, market intel |
| Low Engaged Inventory | Units priced above market, high mileage, poor merchandising |
| Listings Optimizer | Best Match tab, photo analysis, listing quality |
| Historical Connections | Vehicle-level connection history, high-performers removed |
| Deeplink Dashboard | Deep link status and impact |
| Market Area Planner | SRPs/VDPs/connections by market, make, stock type, zip code |
| Radius Performance | Dealer-specific view of impression/lead origin geography |
| Competitive Set | Anonymous comparison vs. similar-market dealers |
| Dealer Lead Intelligence | Lead quality insights, post-submission shopper behavior |
| Shopper Details | Shopper behavior on site after lead submission |
| Sales Attribution Summary | Last connection type, VIN-level attribution, estimated dollar value |
| Walk-in Demand / Lot Insights | Walk-in traffic data (requires Radar mapping) |

## Other Sections (in playbook but not fully detailed here)
- Group Reporting (5 tabs: Overall, Store, Best Match, Comparison, Inventory)
- GA4 & Looker Studio (11 tabs + Appendix)
- Cars Social & VPM Troubleshooting (10 sections)
- Hub Troubleshooting (Login/Access Issues)
- Retention Deck Template
- Appendix: Key Reports

## Help & Escalation
- **Slack:** #help-dealer-facing-reporting
- **Office Hours:** Beast Mode Office Hours (sign up)
- **Support:** support@cars.com (for CRM/lead quality issues)
