---
name: project_dealerinspire_testimonial_updates
description: "DealerRater testimonial-feed → Dealer Inspire page-update workflow (ACA book); mechanics, IDs, draft script"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5c5fb9c4-3d2a-40e2-a674-4914462060d8
---

Replace dealer-site testimonial-page reviews with the configured DealerRater feed, then ask Dealer Inspire to remove the right-side info box & center the HTML. Template = Danielle's "Update Kenny Ross Ford - Testimonial Page" email (Gmail thread 19ebd1d78aa616a0). Done 2026‑06‑15/16: created 59 unsent drafts across the ACA book.

**Source sheet:** `1M1vL0V9ps93oNBR5VkaL7Pt6GEwMygp3cey23er7zcw` — cols `Store | CCID | URL | DealerRater(status) | Testimonial Link | Check Header`. `DealerRater` col = status: `Done`/`N/A …`/blank(=to-do). **CCID ≠ DR feed ID.**

**Per store:**
- Testimonial page URL = usually `{site}/about-us/customer-testimonials/`; variants seen: `/testimonials/`, `/customer-testimonials/`, `/kia-dealership-near-me/customer-testimonials/`, `/about-us/reviews/` (leave-a-review only). Confirm the live (redirected) URL.
- **DR feed ID** from the dealer testimonial page (`dealer-reviews-{ID}` link). If the page has no DR link, use the **DR dealer-panel switcher**: on any `dealerrater.com/dp/...` page, `$('#dp-dealer-search')` (jQuery UI autocomplete) → `$(inp).autocomplete('search', name)`, then read `$(inp).data('ui-autocomplete').menu.element.find('li').map(()=>$(this).data('ui-autocomplete-item'))` → gives `dealerId, groupId, dealerName, basicListing`. `groupId 1067 = "Atlantic Coast Automotive Group"` (entire ACA book; the GROUP widget code is `testimonials/group/1067` = too broad for a single sub-group).
- **Configure widget:** `dealerrater.com/dp/{ID}/tools/my-website-tools` → Testimonial Feed → set `#reviews=50`, `MinimumScore=4`, All Sources → click "Save Changes" (`input[type=submit]`). Setting `<select>.value` + dispatching `change`+`input` then clicking save works (verified; `?showSaved=True` confirms). The DEALERSHIP ("store") embed = `testimonials/{ID}/javascript` (vs group code `testimonials/group/{gid}/javascript`).
- **Basic-listing dealers** (product flag `basicListing:true`) have **no Testimonial Feed widget** — `/tools/my-website-tools` redirects to `/awards`; can't set 50/4 → flag (e.g. Ride Today Cars 54912, Southern Alfa Romeo 115101, Southern Collision 118189, NYE group profile 121122).
- **Combined profiles (one DR feed for many rooftops):** Miami Lakes Automall = **35248** (all ML rooftops); Southern Team Roanoke = **30387** (Hyundai/Nissan/Subaru/VW + Team Automall + Roanoke Nissan).
- **Umbrella sites:** Vision Auto Group has a real group profile **121096** w/ feed (clean). NYE Auto Group page embeds rooftop 38960 (used that). Southern Auto Group (drivingsouthern.com) has **no** testimonial page.

**Login:** METAL SSO — DR `/dp/` → login.carscommerce.inc → Google (jcrawley@cars.com) → JumpCloud password + MFA (user does password+MFA; don't enter creds via fill).

**Screenshots (chrome-devtools):** info box = `.dealer-info` / `.sidebar.vertical`; `scrollIntoView({block:'center'})`; hide cookie/`.privacy_prompt` + engagement-widget overlays via `elementFromPoint(boxCenter)` loop (never hide body/html/box); **reload then screenshot** to beat delayed chat widgets (Emplifi). Saved to `~/Documents/Reports/DealerRater-Testimonials/`.

**Draft engine:** `~/Documents/Reports/DealerRater-Testimonials/_make_draft.py --store --url --drid --slug --img [--noinfobox]`. Refreshes Gmail token from `~/.gmail-mcp/gcp-oauth.keys.json` + `credentials.json`, builds raw MIME w/ inline PNG (so big base64 stays out of context), creates **UNSENT** draft via Gmail API. To support@dealerinspire.com; Cc mjoyce@dealerinspire.com, ksiner@dealerinspire.com, dmcjunkins@carscommerce.inc. `--noinfobox` for full-width pages (no right box). Gmail draft `create_draft` only does attachments via the `raw` param.

**Still flagged (2026-06-16):** NowCar (404), Southern Auto Group (no page), Vision Mitsubishi (no feed page), Ride Today Cars / Southern Alfa Romeo / Southern Collision (basic listing, no widget). Sheet status NOT written back (Google Sheets MCP cert error) — can update via Sheets API w/ same token method. Related: [[project_aca_reporting]], [[reference_dr_admin_form]], [[reference_login_flows]].
