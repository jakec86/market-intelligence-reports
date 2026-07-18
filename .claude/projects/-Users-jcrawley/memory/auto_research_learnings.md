---
name: auto-research-learnings
description: Cumulative knowledge base from /auto-research sessions — dealer patterns, market insights, data tips, and effective framings
type: project
originSessionId: 05cb594c-d01d-4120-a86e-7ad6866e33e1
---
# Auto Research — Session Learnings

Knowledge accumulated from automotive research analyst sessions. Referenced by the `/auto-research` skill to improve analysis quality over time.

## Dealer-Specific Insights

### [2026-04-07] — Tactical Fleet Charlotte MAE Drop
- **Context:** MAE connections dropped 59% (41→17) Feb→Mar while organic surged 30% (165→215)
- **Finding:** Root cause was merchandising degradation, not market/product issues. Under-merchandised listings +75% (4→7), Fair/Above badges -12.5% (30%→26%). MAE shoppers are the most listing-quality-sensitive audience — they have no relationship with the dealer, so the listing IS the store. High-demand nameplates (AMG G 63 score 0.09, Urus 0.56, 911 0.72) were functionally invisible due to poor merchandising/pricing.
- **Apply when:** Any dealer shows MAE drop but organic growth — check merchandising quality first, not MAE product config. Exotic/luxury inventory is especially MAE-sensitive because these are destination-worthy vehicles that pull shoppers across DMA lines.

## Market Patterns

### [2026-04-07] — MAE vs Organic as Diagnostic Signal
- **Context:** Tactical Fleet Charlotte total connections looked fine (+12.6%) but masked a 59% MAE collapse
- **Finding:** Splitting MAE vs organic connections is a powerful diagnostic. When organic grows but MAE drops, it's almost always a listing quality issue — local shoppers compensate with brand familiarity, but out-of-market shoppers won't tolerate missing photos/prices on high-ticket items.
- **Apply when:** Any dealer with MAE product shows connection volatility — always split MAE vs organic before diagnosing

## Data Source Tips

### [2026-04-07] — Market Comparison Crosstab Doesn't Filter by Month
- **Context:** Tried downloading Feb vs Mar crosstabs from Demand Signals Market Comparison
- **Finding:** The month filter on the Demand Signals dashboard only affects KPI tiles and charts, NOT the Market Comparison crosstab. Both downloads were identical. Use KPI screenshots + MAE-filtered Connections Contact Details for month-over-month comparison instead.
- **Apply when:** Any time you need month-over-month demand score comparison — don't waste time downloading multiple crosstabs

### [2026-04-07] — MAE Filter in Connections Contact Details
- **Context:** Needed to isolate MAE-specific connections for Tactical Fleet Charlotte
- **Finding:** The "Market expansion leads" filter in the Connections Contact Details Tableau iframe has three options: All, Yes, No. Filter to "Yes" to get MAE-only connections. Access via admin.cars.com `/dealers/{UUID}/reports/connections_contact_details`.
- **Apply when:** Any MAE-specific connection analysis

## Effective Framings

### [2026-04-07] — MAE Analysis: "The Listing IS the Store"
- **Context:** Explaining why merchandising quality matters more for MAE than organic
- **Finding:** Framing "for MAE shoppers 100+ miles away, the listing IS the store" made the connection between merchandising quality and MAE performance immediately intuitive. Also effective: calling out specific high-demand nameplates that "should be MAE magnets" but are "functionally invisible."
- **Apply when:** Any MAE-related dealer conversation — lead with the local-vs-distance shopper quality sensitivity gap

### [2026-04-07] — Word Doc Report Format for Complex Analysis
- **Context:** Built a python-docx report for the MAE analysis with signal-colored tables
- **Finding:** Structured as: The Numbers (MoM table) → Why It Dropped (3 factors with bullets) → What's Working (performers table) → Signal Distribution → The Takeaway. Color-coded signal cells (HOT CONVERTER through DEAD WEIGHT) made the doc scannable. The "single biggest lever" closing paragraph tied everything together.
- **Apply when:** Any analysis complex enough to warrant a deliverable doc — use this section structure

## Dealer-Specific Insights (continued)

### [2026-04-08] — eCarOne Plano (6000362) — Prospecting Account Profile
- **Context:** Full demand score + web research on independent used luxury/EV dealer in DFW
- **Finding:** 237 units across 99 models = 2.4 avg depth. 45.5% WEAK signal rate driven by single-unit listings competing against franchise depth. Sweet spot is luxury EVs (Escalade IQ, LYRIQ, Rivian, Tesla) where niche positioning drives outsized engagement. Exceptional reputation (4.8 DealerRater/3,050 reviews) is a major competitive advantage vs. Autos of Dallas (BBB D, same street). BBB C- from 3 unanswered complaints is an easy fix.
- **Apply when:** Prospecting conversations with eCarOne — lead with demand score data showing their niche strength, then frame Cars.com subscription as amplifying what's already working. Also applies to any niche independent: depth beats breadth for marketplace visibility.

## Market Patterns (continued)

### [2026-04-08] — DFW Used EV Landscape
- **Context:** Researched EV market dynamics in Dallas-Ft. Worth
- **Finding:** 145K+ EVs registered in North Texas, concentrated in Plano/Frisco/McKinney. Off-lease EV wave from 2023 leases hitting in 2026 increases supply. Tax credit rollback cooled demand (~6% share vs 7.5% in 2025). For dealers like eCarOne, this means better acquisition costs but potential margin compression.
- **Apply when:** Any DFW EV-focused dealer research or when assessing EV inventory strategy

## Effective Framings (continued)

### [2026-04-08] — "Stock Deeper, Not Wider" for Niche Independents
- **Context:** eCarOne had 99 models at 2.4 avg depth — impressive breadth but invisible per-model
- **Finding:** Framing inventory optimization as "stock deeper, not wider" resonated — it's actionable and intuitive. Supporting it with Demand Score data showing that models with 4+ units consistently outperformed single-unit listings made it data-backed. Also effective: "53 models scoring below 0.5 are effectively invisible to DFW shoppers."
- **Apply when:** Any independent dealer with broad-but-thin inventory — use demand score to identify which models deserve depth

### [2026-04-08] — Revenue Framing for Prospect Subscription Pitch
- **Context:** Needed to estimate Cars.com subscription value for a Prospecting account
- **Finding:** Formula that worked: current organic connections × expected lift % × close rate × avg GPU = monthly incremental gross. For eCarOne: 611 connections × 20% lift × 8% close × $3K GPU = ~$29K/month. This makes the subscription ROI self-evident.
- **Apply when:** Any prospect account research — always include a revenue-framed subscription value estimate

## Dealer-Specific Insights (continued)

### [2026-04-23] — J.C. Lewis Auto Group (Savannah, GA) — Portfolio & Pixel Audit
- **Context:** Full portfolio research for a 5-store Ford/Mazda group in Savannah area; focus on waste and Cars.com justification
- **Finding:** Pooler store pays $1,799/mo for Cars Commerce website but has ZERO marketplace listings — inventory invisible on Cars.com. 3 Lincoln/Group stores are Prospecting with no products. Mazda has the most diverse product mix (display, PPC, FB data pkg). Total identified upsell opportunity ~$171–186K/yr ARR. Edmunds pixel confirmed on jclewisford.com: 3 scripts + ADSOL.EdmundsEventTracking() conversion tracker — CarMax receives every conversion event from J.C. Lewis's own website.
- **Apply when:** Any J.C. Lewis account conversation; also use Pooler gap as a talking point for any group where a store has website-only with no marketplace product.

### [2026-04-23] — Dealer Website Pixel Audit via Browser JS Evaluation
- **Context:** Needed to find third-party tracking scripts on jclewisford.com to document Edmunds waste/risk
- **Finding:** Can use `mcp__playwright__browser_evaluate` to extract all GA4 IDs (regex: `G-[A-Z0-9]{8,12}`), GTM IDs, Google Ads IDs, and vendor-specific URLs from the page HTML in one pass. Also use `document.querySelectorAll('script[src]')` to enumerate third-party domains. This technique takes ~2 minutes and produces a complete pixel inventory. J.C. Lewis Savannah: 45 scripts from 24 domains, Edmunds (3 scripts + conversion tracker), 6 GA4 IDs, 4 Google Ads IDs.
- **Apply when:** Any dealer research where you want to show attribution waste, competitive pixel risk, or bloated vendor stack. Especially powerful for prospecting conversations.

## Dealer-Specific Insights (continued)

### [2026-06-04] — Dyer & Dyer Volvo Cars (CCID 10730, Chamblee GA) — Badge Rate Collapse
- **Context:** Prospecting franchise Volvo dealer, Georgia's largest for 33 years; researched used inventory drop over 30-60 days
- **Finding:** Only 1% badge rate (7/626 units) — down -30% MoM, driving VDPs -16.5% and Connections -16.1%. Root cause is not used inventory (used avg 15 days live, healthy) — it's 352 new units averaging 118 days live at $65,449 avg with 58% under-photographed (<20 photos). CPO (29 units, 32 days, $40K) is the best performer by connection rate (0.52/unit/wk vs 0.20 used, 0.026 new). Atlanta used market at 171 days supply vs 90 industry avg makes uncompetitive pricing especially costly.
- **Apply when:** Any Volvo franchise research; any dealer with sub-5% badge rate; any situation where "used is dropping" turns out to be a new-inventory drag problem

## Market Patterns (continued)

### [2026-06-04] — Atlanta Used Car Market Oversupply
- **Context:** Researched market context for Dyer & Dyer Volvo Cars
- **Finding:** Atlanta used car market at 171 days supply vs 90-day industry average — nearly 2x oversupplied. In this environment, uncompetitive pricing has outsized impact because buyers have abundant alternatives. Badge rate and Best Match placement become survival requirements, not differentiators.
- **Apply when:** Any Atlanta-area dealer research; any dealer claiming "the market is slow" — the market is oversupplied, which means pricing discipline matters MORE

## Data Source Tips (continued)

### [2026-06-04] — Listings Optimizer Reveals New vs CPO vs Used Splits
- **Context:** Pulling listings data for Dyer & Dyer Volvo (Prospecting account)
- **Finding:** admin.cars.com Listings Optimizer shows Merchandising Status table broken out by New/CPO/Used with: vehicle count, complete/incomplete, photos breakdown, avg days live, avg photos, avg price, and 7-day connections. This is the fastest way to diagnose which segment is dragging performance. URL: `/dealers/{UUID}/reports/listings_optimizer`
- **Apply when:** Any dealer where you need to isolate whether new vs. used vs. CPO is the performance problem

## New Scenarios

### [2026-04-07] — "Why did MAE connections drop?"
- **Context:** First MAE-specific analysis — required splitting connection types, cross-referencing merchandising data, and demand score analysis
- **Finding:** This is a distinct playbook from generic "why did metric drop" — requires MAE vs organic split, merchandising quality audit, and understanding that MAE shoppers have different quality thresholds than local shoppers
- **Apply when:** Added as new playbook in auto-research skill
