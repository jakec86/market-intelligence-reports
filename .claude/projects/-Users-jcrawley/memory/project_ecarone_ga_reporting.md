---
name: ecarone-ga-reporting
description: "eCarOne GA4 property, advertising mix, benchmarks, and reporting project — DFW luxury used car dealer"
metadata: 
  node_type: memory
  type: project
  originSessionId: ca589fff-9f98-4381-a976-02db7636b893
---

## Account

- **Name:** eCarOne
- **CCID:** 6000362
- **SF Account ID:** `0013600001tY8JOAA0`
- **SF Status:** Prospecting (field is stale — active VPM client)
- **Location:** Dallas–Fort Worth
- **Type:** Luxury pre-owned (used only; strong EV/Tesla inventory focus)
- **Monthly meeting:** 2nd Wednesday, 1 PM ET (Cars Commerce/eCarOne); contact: Michael

## GA4 Property

- **Property ID:** `326694710`
- **Property Name:** http://www.ecarone.com - GA4
- **GA Account:** www.ecarone.com (ID: 12780923)
- **Credentials:** `gafield1` (`~/.claude/ga_tokens/gafield1_adc.json`) — OAuth user creds, NOT service account
- **Query method:** Direct REST API (`analyticsdata.googleapis.com/v1beta`) — gafield1 MCP tool fails with "no client_email" error; use Python REST calls instead. See [[ecarone-ga-rest-query-pattern]] (pattern established 2026-06-10).

**Why:** The gafield1 MCP server expects service account ADC; gafield1_adc.json is an OAuth token. Always use the Python REST pattern for this property.

## Advertising Mix (as of May–Jun 2026)

Cars.com Social is $1,998/month (confirmed). Other channel estimates:

| Channel | Sessions/mo (est.) | Est. Spend/mo | Est. CPV | Bounce |
|---|---|---|---|---|
| Google CPC | ~18,200 | ~$5,000–$9,000 | ~$0.50–0.70 | 10.0% |
| Facebook Paid Social | ~10,200 | ~$4,000–$6,500 | ~$0.45–0.65 | 0.4% |
| CarGurus RPM/Display | ~4,600 | ~$2,000–$3,500 | ~$0.45–0.75 | 0.6% |
| Cars.com Social | ~4,000 | **$1,998** (known) | ~$0.50 | 1.8% |
| Edmunds Ad Solutions | ~3,700 | ~$1,500–$2,500 | ~$0.45–0.70 | 5.1% |

Total non-Cars.com estimated ad spend: **$12,500–$21,500/month**

**Cars.com competitive position:** Cars.com referral (5,335 sessions, 1.8% bounce) beats Edmunds in sessions and engagement at lower estimated cost. Facebook has near-zero bounce (retargeting/DPA). Google CPC is largest paid driver.

## Performance Benchmarks (May 1–Jun 10, 2026)

**Site overview:**
- Sessions: 98,020 | Users: 54,853 | Pageviews: 310,682
- Bounce rate: 8.8% (improved from 9.4% prior period) | Avg session: 235s
- Conversions (all events): 388,258
- vs. prior period (Mar 22–Apr 30): sessions −9%, pageviews −11%, conversions −10%

**Weekly run rate:** ~15,000–18,700 sessions/week (stable May–Jun)

**Top content:**
1. /all-inventory — 106K views (inventory browsing dominant)
2. Electric/Hybrid inventory — 25K views (strong EV demand)
3. Homepage — 21K views
4. Luxury SUV inventory — 12K views
5. Tesla pages prominent (Cybertruck, Model Y, Tesla inventory)

**Top sources by sessions:** Google/CPC (24,293) → Direct (19,155) → Facebook/Paid_Social (13,605) → CarGurus RPM/display (6,167) → Google/organic (5,736) → cars.com/referral (5,335) → edmunds/referral (4,913)

## VPM Performance (Tableau — through May 2026)

Sheet: `https://docs.google.com/spreadsheets/d/1E6CIiKbmFIWJdr3uWZHPkXMyQFtnDpAK6xdnJ58jz1Q/edit?gid=247007646`

| Month | VPM Imp | Total Impr | VPM% | Total Leads | VPM Leads | Imp Lift | Leads Lift |
|---|---|---|---|---|---|---|---|
| March | 2,498 | 33,211 | 8% | 496 | 9 | 8% | 2% |
| April | 3,087 | 36,630 | 8% | 529 | 7 | 9% | 1% |
| May | 3,261 | 34,250 | 10% | 440 | 10 | **11%** | 2% |
| Avg | — | — | — | — | — | **7%** | **2%** |

May = record high VPM impression lift (11%). June data not yet added as of 2026-06-10.

## Reporting Opportunity

Goal: Build a recurring eCarOne GA + VPM dashboard/report combining:
- GA4: sessions, users, channel mix, bounce by source, weekly trend
- VPM sheet: impression lift, leads lift MoM
- Ad spend estimates vs. Cars.com value story
- Potential delivery: Google Sheet tab or HTML report, monthly ahead of 2nd-Wed meeting

**Why:** eCarOne has a complex ad mix (~5 channels). Cars.com's value is strong (low bounce, growing VPM lift) but buried under Google CPC volume. A unified monthly report surfaces the Cars.com story clearly and supports retention/upsell of additional products (Verified Listings mentioned May 27).

## SF Activity Log

- **2026-05-27:** Virtual meeting with Michael — "reviewed results, set the stage for verified listing that are coming soon"
