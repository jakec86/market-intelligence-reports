---
name: Sonic Demand KPI — Market DI % framing
description: Sonic Monthly Report — Market DI is primary (not Portfolio), stakeholder-facing form is "±X% to market", no rotation labels in email copy
type: feedback
originSessionId: 4adc8f83-50db-468a-b0c1-eed587d83946
---
**Rule:** In Sonic Monthly Performance reporting, all stakeholder-facing demand KPIs use Market Demand Index (from admin.cars.com Market Comparison) expressed as `% to Market = (DI − 1) × 100`. Portfolio DI is emergency fallback only, labeled "Internal benchmark (vs Sonic group avg)" — never shown as "Demand Index."

**Why:** Jake confirmed 2026-04-22 that Portfolio DI is self-referential (brand vs Sonic average) and not actionable for brand managers. Now that per-store Market Comparison pulls are automatable via the Tableau JS embedding API (memory `project_sonic_monthly_testrun.md`), Market DI can be primary. Percentage framing ("+24% to market") reads more clearly in email than raw index ("1.24") and ties directly to the gap-formula justification (Market − Group) / Group.

**How to apply:**
- Per-store Market DI = VDP share of DMA ÷ Inventory share of DMA
- Brand rollup uses **per-DMA aggregation** to avoid double-counting shared markets (e.g., 3 Houston Land Rover stores compete in the same DMA — count market size once per DMA, sum brand dealer VDPs/inventory across co-located stores)
- Email header format: `{Brand} — {N} stores, {Month} {Year}` / `Market capture: ±X% to market · VDPs ±X% MoM · Connections ±X% MoM` / `Top story: {one-liner}`
- Drop "Luxury Rotation" / "Volume Rotation" from all subject lines and body copy — rotation is an internal scheduling concept only. Sharon's verification email subject: `Sonic — {Month} {Year} Overview | Pre-Send Review` (not "Sonic Luxury Rotation")
- Signal mix (Leader/Hidden Gem/Underperformer counts) stays in Store Scorecard table, not in the header KPI block
- Fallback: if admin data missing for >20% of a brand's stores, use Portfolio DI labeled `"Internal benchmark: ±X% vs Sonic group avg (market data unavailable)"`
