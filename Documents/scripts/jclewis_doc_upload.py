#!/usr/bin/env python3
"""
J.C. Lewis Auto Group — Cars Commerce Research Report (condensed, corrected)
Uploads to Google Drive as Google Doc. Overwrites previous version.
"""

import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

SHEET_URL = "https://docs.google.com/spreadsheets/d/16YWmPwmhdfl7zqlYmA8GcK-8DDKri28LcC9QoP1ig6k"
TODAY = "April 23, 2026"

HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; color: #222; margin: 72px; line-height: 1.5; }}
  h1 {{ color: #1A3A4A; font-size: 18pt; text-align: center; margin-bottom: 2px; }}
  h2 {{ color: #2C5F7A; font-size: 13pt; border-bottom: 2px solid #2C5F7A; padding-bottom: 3px; margin-top: 28px; margin-bottom: 10px; }}
  h3 {{ color: #1A3A4A; font-size: 11pt; margin-bottom: 4px; margin-top: 16px; }}
  .subtitle {{ text-align: center; color: #666; font-size: 10pt; margin-bottom: 28px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0 16px 0; font-size: 10pt; }}
  th {{ background: #2C5F7A; color: white; padding: 7px 10px; text-align: left; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #E0E0E0; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #F7FAFC; }}
  .critical {{ background: #CC0000; color: white; font-weight: bold; padding: 2px 7px; border-radius: 3px; font-size: 9pt; white-space: nowrap; }}
  .high {{ background: #E65C00; color: white; font-weight: bold; padding: 2px 7px; border-radius: 3px; font-size: 9pt; white-space: nowrap; }}
  .alert {{ background: #FFF0F0; border-left: 4px solid #CC0000; padding: 10px 14px; margin: 12px 0; font-size: 10.5pt; }}
  .callout {{ background: #EEF5FA; border-left: 4px solid #2C5F7A; padding: 10px 14px; margin: 12px 0; font-size: 10.5pt; }}
  .sheet-link {{ background: #F0F7EE; border: 1px solid #4CAF50; border-radius: 4px; padding: 9px 13px; margin: 10px 0; font-size: 10pt; }}
  li {{ margin-bottom: 5px; }}
  ul {{ margin-top: 4px; margin-bottom: 8px; }}
  code {{ font-family: monospace; background: #F0F0F0; padding: 1px 5px; border-radius: 2px; font-size: 9pt; }}
  .page-break {{ page-break-before: always; }}
  .store-label {{ font-weight: bold; font-size: 10.5pt; }}
  .note {{ font-size: 9pt; color: #777; font-style: italic; }}
  .promo-box {{ background: #F0F7EE; border: 2px solid #2C5F7A; border-radius: 5px; padding: 14px 18px; margin: 16px 0; }}
</style>
</head>
<body>

<h1>J.C. Lewis Auto Group</h1>
<h1 style="font-size:13pt; margin-top:2px; font-weight:normal;">Cars Commerce — Account Research &amp; Opportunity Brief</h1>
<div class="subtitle">{TODAY} &nbsp;|&nbsp; Internal Use Only</div>

<h2>Overview</h2>
<p>J.C. Lewis Auto Group operates 5 active stores across Southeast Georgia (Savannah, Pooler, Hinesville, Statesboro) plus a Mazda franchise. All stores use Cars Commerce platform products (DealerInspire websites, DealerRater, media tools) but <strong>none currently hold an active Cars.com marketplace subscription.</strong> This brief focuses on three high-opportunity stores for a promotional marketplace pitch: <strong>Mazda, Lincoln of Savannah, and Ford of Pooler.</strong></p>

<div class="sheet-link">
  📊 <strong>Supporting Data:</strong> <a href="{SHEET_URL}">{SHEET_URL}</a> &nbsp;|&nbsp; Tabs: Portfolio Overview · Pixel Audit · Gap Analysis · Edmunds Risk
</div>

<h2>Focus Store Profiles</h2>

<h3>J.C. Lewis Mazda &nbsp;<span class="note">CCID 6035432</span></h3>
<p>Already the most invested store in the Cars Commerce ecosystem — running a media stack but missing marketplace reach.</p>
<table>
  <tr><th>Product</th><th>Monthly</th><th>Notes</th></tr>
  <tr><td>DealerInspire Website</td><td>$350</td><td>Legacy rate — opportunity to upgrade</td></tr>
  <tr><td>Facebook Data Package 2</td><td>$474</td><td></td></tr>
  <tr><td>Fuel PPC Software</td><td>$200</td><td></td></tr>
  <tr><td>Digital Ad Spend (Mazda)</td><td>~$1,164</td><td></td></tr>
  <tr><td>Programmatic Display</td><td>$400</td><td></td></tr>
  <tr><td>Cars Premium Display</td><td>$500</td><td></td></tr>
  <tr><td><strong>Cars.com Marketplace</strong></td><td style="color:#CC0000;font-weight:bold;">— NONE —</td><td>Significant gap given existing media investment</td></tr>
</table>
<p>Mazda is spending on paid media to drive shoppers to their site but has no Cars.com listing presence to capture in-market shoppers already browsing the marketplace. Adding marketplace amplifies the existing media investment.</p>

<h3>J.C. Lewis Lincoln of Savannah &nbsp;<span class="note">CCID 6039661 — Prospecting</span></h3>
<p>No active Cars Commerce products. Lincoln is a brand with strong in-market demand and a relatively small competitive set — high-value listing opportunity.</p>
<ul>
  <li>Zero current footprint with Cars Commerce</li>
  <li>Competing Lincoln stores in the Savannah DMA are active on marketplace</li>
  <li>Clean onboarding — no legacy pricing or configuration to unwind</li>
</ul>

<h3>J.C. Lewis Ford Pooler &nbsp;<span class="note">CCID 6062323</span></h3>
<p>Active DealerInspire website customer ($1,799/mo) with no marketplace listing — inventory is invisible to Cars.com shoppers.</p>
<table>
  <tr><th>Product</th><th>Monthly</th><th>Notes</th></tr>
  <tr><td>DealerInspire Website</td><td>$1,799</td><td>Active</td></tr>
  <tr><td>Conversations w/ Trade Eval</td><td>$0</td><td>Free add-on</td></tr>
  <tr><td>DealerRater AutoResponse</td><td>$0</td><td>Free add-on</td></tr>
  <tr><td><strong>Cars.com Marketplace</strong></td><td style="color:#CC0000;font-weight:bold;">— NONE —</td><td>Paying for the website; no marketplace to match</td></tr>
</table>
<p>Pooler already trusts the Cars Commerce platform for their website. Adding marketplace is a natural extension — and a straightforward conversation given the existing relationship.</p>

<h2>Pixel Audit — jclewisford.com</h2>
<p class="note">Live browser audit, {TODAY}. Critical and High findings only.</p>

<table>
  <tr><th>Risk</th><th>Vendor</th><th>Finding</th></tr>
  <tr style="background:#FFF0F0;">
    <td><span class="critical">CRITICAL</span></td>
    <td><strong>Edmunds (CarMax-owned)</strong></td>
    <td>3 scripts active including <code>ADSOL.EdmundsEventTracking()</code> — a live conversion tracker. Every form submission and phone click on J.C. Lewis's own website fires a conversion event back to CarMax, their direct used-car competitor. CarMax acquired Edmunds in 2021 for $404M.</td>
  </tr>
  <tr>
    <td><span class="high">HIGH</span></td>
    <td>Google Analytics 4</td>
    <td>6 GA4 properties firing simultaneously. Every lead is counted multiple times across multiple dashboards — no vendor's reported ROI is comparable to another's without normalization.</td>
  </tr>
  <tr>
    <td><span class="high">HIGH</span></td>
    <td>Google Ads</td>
    <td>4 separate conversion IDs active. Each account claims independent credit for the same conversions — reported ROAS figures are inflated and unreliable as a comparison basis.</td>
  </tr>
</table>

<div class="alert">
  <strong>The Edmunds problem in plain language:</strong> J.C. Lewis is paying Edmunds for advertising while simultaneously allowing CarMax to receive conversion data from visitors on J.C. Lewis's own website. The tracking is active today and requires no special access to verify — it fires on every page load.
</div>

<h2>Opportunity — Promo Variation</h2>

<div class="promo-box">
  <strong>Target stores for promotional marketplace pitch:</strong>
  <ul style="margin-bottom:0;">
    <li><strong>J.C. Lewis Mazda</strong> (CCID 6035432) — already a media buyer; marketplace is the missing piece</li>
    <li><strong>J.C. Lewis Lincoln of Savannah</strong> (CCID 6039661) — clean open, no competing Cars Commerce products to navigate</li>
    <li><strong>J.C. Lewis Ford Pooler</strong> (CCID 6062323) — existing website relationship; marketplace is a natural add</li>
  </ul>
</div>

<p>The promo conversation has a clear angle for each store:</p>
<ul>
  <li><strong>Mazda:</strong> "You're already spending on Cars Commerce media — marketplace puts your listings in front of the shoppers that media is trying to reach. Without it, you're paying to drive traffic to a destination that isn't on Cars.com."</li>
  <li><strong>Lincoln Savannah:</strong> "Lincoln buyers are a small, intentional audience. Cars.com is where they search. Right now a competing Lincoln store is capturing those shoppers and you're not."</li>
  <li><strong>Pooler:</strong> "You trust us with your website. Your inventory deserves the same reach on the marketplace side. A promo gets you in at low risk to see the return."</li>
</ul>

<h2>Data Notes</h2>
<ul class="note">
  <li>Portfolio data from Salesforce SBQQ. Subscription records include historical/legacy entries — only active product lines shown above. None of the three focus stores hold a current Cars.com marketplace subscription.</li>
  <li>Pixel audit via live browser inspection of jclewisford.com. Other group stores may differ. Findings current as of {TODAY}.</li>
  <li>Edmunds source: Automotive News acquisition reporting, CarMax IR press release (June 2021).</li>
</ul>

<p style="text-align:center; font-size:9pt; color:#AAA; margin-top:48px;">
  Cars Commerce Account Intelligence &nbsp;·&nbsp; {TODAY} &nbsp;·&nbsp; Internal Use Only
</p>

</body>
</html>
"""

def load_creds():
    data = json.load(open('/Users/jcrawley/.claude/tokens/gsheets_credentials.json'))
    gcp = json.load(open('/Users/jcrawley/gcp-oauth.keys.json'))['installed']
    creds = Credentials(
        token=data.get('access_token'),
        refresh_token=data['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=gcp['client_id'],
        client_secret=gcp['client_secret'],
        scopes=data.get('scope', '').split()
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def main():
    creds = load_creds()
    drive = build('drive', 'v3', credentials=creds)

    media = MediaInMemoryUpload(HTML.encode('utf-8'), mimetype='text/html', resumable=False)
    result = drive.files().create(
        body={
            'name': f'J.C. Lewis Auto Group — Cars Commerce Opportunity Brief ({TODAY})',
            'mimeType': 'application/vnd.google-apps.document'
        },
        media_body=media,
        fields='id,webViewLink'
    ).execute()

    doc_id = result['id']

    # Share: anyone with link
    drive.permissions().create(
        fileId=doc_id,
        body={'type': 'anyone', 'role': 'writer'},
        fields='id'
    ).execute()

    print(f"\nDOC:   https://docs.google.com/document/d/{doc_id}/edit")
    print(f"SHEET: {SHEET_URL}")

if __name__ == "__main__":
    main()
