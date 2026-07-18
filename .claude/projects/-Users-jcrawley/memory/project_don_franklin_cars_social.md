---
name: project_don_franklin_cars_social
description: Don Franklin Cars Social case study — how to isolate true Cars Social in GA4 (cars.com_carssocial campaign)
metadata: 
  node_type: memory
  type: project
  originSessionId: 98ea4c28-b506-4635-9df4-5a55c3dd49b4
---

Don Franklin Automotive Group (Lexington KY) Cars Social case study. Doc ID `1QysBsr9z5Lc50UQvsYqES4bi1fdvsRphUEdJG27kTQc`. Two stores: Buick GMC (GA4 467758077) + Hyundai (467133052) — query via gafield1 REST, see [[reference_ga4_rest_access]].

**Core rule — isolate Cars Social to its OWN campaign.** True Cars.com Cars Social = `sessionCampaignName = "cars.com_carssocial"` (source `cars.com` / medium `referral`). Do NOT bundle in:
- `meta / cpc_social / DriveAuto_Social` — that's the dealer's PAID-SOCIAL AGENCY (DriveAuto / Force Marketing), not Cars Social. All `DriveAuto_*` campaigns (search/VLA/display/email/social) are DriveAuto.
- organic social (Organic Social channel), facebook/instagram referrals.

**The original v1 doc mislabeled "Cars Social" as all-social-bundled → headline 53,618 sessions Jan–May. TRUE Cars Social was 11,595** (Buick 5,593 + Hyundai 6,002) — ~5× smaller. Rebuilt 2026-06-12 via `~/Documents/scripts/reformat_cs_doc_v2.py` (v1 `reformat_cs_doc.py` preserved). Jake chose "isolate, honest, full rebuild," all tables Jan–May.

**True Cars Social profile (Jan–May 2026):** high net-new (87% Buick / 95% Hyundai), 94% mobile, engagement (55%/61%) beats the dealer's bulk DriveAuto paid social (42%/56%), top-of-funnel browsing (heavy asc_item_pageview + media_interaction) with near-zero hard conversions on first visit (Buick 2 / Hyundai 1 form submits). Volume declining since Q1 (Buick 1,531→791) — but **spend is consistent** (confirmed by Jake), so this is a delivery/efficiency decline (creative fatigue / audience saturation / CPM inflation), NOT a budget taper. Talking point = campaign-health review.

**Interactive pinpoint maps:** Leaflet HTML in repo `jakec86/market-intelligence-reports` (gh authed as jakec86), path `DonFranklin/`, served at jakec86.github.io. Regenerated 2026-06-12 → `..._06.12.26.html` (Buick GMC + Hyundai); old `06.03.26` removed; `index.html` cards + Google-Doc named links updated. Maps' stale layer was `const cities=[]` (reach bubbles, had bundled Lexington 5,802) + hardcoded KPI panel + `total-num` badge + legend/`getTierStyle` scale + a bundled "Demand Chart" (now hidden). `zipData` (Q1-YoY demand) + `hitlistZips` are demand-based and stay valid. Regen script: `~/Documents/scripts/regen_cs_pinpoint_maps.py` (KY-only city reach, matches doc geo table). Doc builder with real tables: `reformat_cs_doc_v3.py`.

**Why 28 days (the v1 chart):** GA4's default reporting window is "Last 28 days" (4 weeks, day-of-week normalized) — it was just the carried-through default, inconsistent with the doc's calendar-month basis. Make timeframes consistent.
