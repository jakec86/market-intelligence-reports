"""
Cars Social Case Study — Don Franklin (REBUILD v2)
- Timeframe: Jan–May 2026 (consistent across ALL tables)
- Cars Social ISOLATED to campaign `cars.com_carssocial` (source cars.com/referral)
  -> excludes DriveAuto paid social (meta/cpc_social), organic social, other referrers
- Data re-pulled live from GA4 Data API (props 467758077 Buick GMC / 467133052 Hyundai)
Original (bundled-social) version preserved in reformat_cs_doc.py.
"""
import json, urllib.request, urllib.parse, time

creds = json.load(open('/Users/jcrawley/.claude/tokens/gdocs_credentials.json'))
def _find_gdocs_env(o):
    if isinstance(o, dict):
        if 'google-docs' in o and isinstance(o['google-docs'], dict) and 'env' in o['google-docs']:
            return o['google-docs']['env']
        for v in o.values():
            r = _find_gdocs_env(v)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = _find_gdocs_env(v)
            if r: return r
    return None
env = _find_gdocs_env(json.load(open('/Users/jcrawley/.claude.json')))
payload = urllib.parse.urlencode({
    'client_id': env['GOOGLE_CLIENT_ID'], 'client_secret': env['GOOGLE_CLIENT_SECRET'],
    'refresh_token': creds.get('refresh_token'), 'grant_type': 'refresh_token'
}).encode()
req = urllib.request.Request('https://oauth2.googleapis.com/token', data=payload,
    headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
AT = json.loads(urllib.request.urlopen(req, timeout=10).read())['access_token']
print("Auth OK")

DOC_ID = '1QysBsr9z5Lc50UQvsYqES4bi1fdvsRphUEdJG27kTQc'

def docs_get(doc_id):
    req = urllib.request.Request(f'https://docs.googleapis.com/v1/documents/{doc_id}',
        headers={'Authorization': f'Bearer {AT}'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def docs_batch(doc_id, requests_list):
    body = json.dumps({'requests': requests_list}).encode()
    req = urllib.request.Request(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
        data=body, headers={'Authorization': f'Bearer {AT}', 'Content-Type': 'application/json'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  batchUpdate {e.code}: {e.read().decode()[:300]}")
        return None

PURPLE = {'red': 0.42, 'green': 0.18, 'blue': 0.55}
TEAL   = {'red': 0.0,  'green': 0.66, 'blue': 0.56}
WHITE  = {'red': 1.0,  'green': 1.0,  'blue': 1.0}
LGRAY  = {'red': 0.95, 'green': 0.95, 'blue': 0.97}
DGRAY  = {'red': 0.3,  'green': 0.3,  'blue': 0.3}
LTEAL  = {'red': 0.88, 'green': 0.97, 'blue': 0.95}
LPURP  = {'red': 0.93, 'green': 0.88, 'blue': 0.97}

doc = docs_get(DOC_ID)
print(f"Doc: {doc.get('title')}")
content = doc.get('body', {}).get('content', [])
end_idx = content[-1].get('endIndex', 2) if content else 2
if end_idx > 2:
    docs_batch(DOC_ID, [{'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_idx - 1}}}])
    print("Cleared.")
    time.sleep(0.6)

full_text = (
    "Cars Social Case Study\n"
    "Don Franklin Automotive Group · Lexington, KY · January–May 2026\n"
    "\n"
    "PERFORMANCE SNAPSHOT — CARS SOCIAL (cars.com_carssocial)\n"
    "11,595\tCars Social Sessions\t5,593 Buick GMC · 6,002 Hyundai (Jan–May)\n"
    "91%\tNet-New Shoppers\t87% Buick GMC · 95% Hyundai — first-time site visitors\n"
    "55–61%\tEngagement Rate\tBeats dealer paid social (DriveAuto 42–56%)\n"
    "94%\tMobile-First\tCars Social shoppers are nearly all on mobile\n"
    "\n"
    "MONTHLY TREND — CARS SOCIAL SESSIONS\n"
    "Month\tBuick GMC\tHyundai\tCombined\tNote\n"
    "January 2026\t1,531\t830\t2,361\t\n"
    "February 2026\t1,388\t1,410\t2,798\t\n"
    "March 2026\t1,200\t1,748\t2,948\tPeak\n"
    "April 2026\t728\t1,053\t1,781\t\n"
    "May 2026\t791\t932\t1,723\t\n"
    "Jan–May Total\t5,593\t6,002\t11,595\t\n"
    "Spend held flat, but output slipped — Buick GMC nearly halved since January (1,531→791) and combined volume is down ~42% from the March peak. Flat budget + falling sessions points to a delivery/efficiency decline (creative fatigue, audience saturation, or CPM inflation), not a budget cut — worth a Cars Social campaign-health review.\n"
    "\n"
    "CARS SOCIAL PERFORMANCE — BUICK GMC (Jan–May)\n"
    "Metric\tCars Social\tBenchmark / Context\n"
    "Sessions\t5,593\t6.8% of 82,415 total sessions\n"
    "Net-new shoppers\t3,092 (87%)\tTop-of-funnel reach, not retargeting\n"
    "Engagement rate\t55.0%\tDealer paid social (DriveAuto) 42.1% → +12.9pp\n"
    "VDP views generated\t6,503\t1.16 vehicle pages per session\n"
    "Media interactions\t3,759\tPhoto / video engagement\n"
    "\n"
    "CARS SOCIAL PERFORMANCE — HYUNDAI (Jan–May)\n"
    "Metric\tCars Social\tBenchmark / Context\n"
    "Sessions\t6,002\t3.8% of 156,231 total sessions\n"
    "Net-new shoppers\t3,869 (95%)\tTop-of-funnel reach, not retargeting\n"
    "Engagement rate\t61.0%\tDealer paid social (DriveAuto) 55.9% → +5.1pp\n"
    "VDP views generated\t6,125\t1.02 vehicle pages per session\n"
    "Media interactions\t4,261\tPhoto / video engagement\n"
    "\n"
    "ON-SITE ENGAGEMENT — ASC EVENTS FROM CARS SOCIAL (Jan–May)\n"
    "All events tagged per the Automotive Standards Council (ASC) schema, isolated to Cars Social sessions.\n"
    "Buick GMC — ASC Event\tCount\n"
    "asc_pageview\t7,420\n"
    "asc_item_pageview (VDP views)\t6,503\n"
    "asc_media_interaction\t3,759\n"
    "asc_itemlist_pageview\t762\n"
    "asc_cta_interaction\t245\n"
    "asc_element_configuration\t187\n"
    "asc_menu_interaction\t163\n"
    "asc_form_engagement\t12\n"
    "asc_form_submission (KEY)\t2\n"
    "Hyundai — ASC Event\tCount\n"
    "asc_pageview\t6,917\n"
    "asc_item_pageview (VDP views)\t6,125\n"
    "asc_media_interaction\t4,261\n"
    "asc_itemlist_pageview\t365\n"
    "asc_cta_interaction\t300\n"
    "asc_menu_interaction\t96\n"
    "asc_element_configuration\t94\n"
    "asc_form_engagement\t8\n"
    "asc_form_submission (KEY)\t1\n"
    "Cars Social is a top-of-funnel discovery channel: heavy vehicle browsing + media engagement, with hard conversions occurring downstream (not on the first social visit).\n"
    "\n"
    "AUDIENCE PROFILE — CARS SOCIAL SHOPPER (Jan–May)\n"
    "Metric\tBuick GMC\tHyundai\n"
    "Cars Social sessions\t5,593\t6,002\n"
    "Total users\t3,557\t4,057\n"
    "New users (net-new)\t3,092 (87%)\t3,869 (95%)\n"
    "Mobile share\t94%\t95%\n"
    "Engagement rate\t55.0%\t61.0%\n"
    "\n"
    "GEOGRAPHIC REACH — TOP CITIES (Cars Social, Jan–May)\n"
    "City\tBuick GMC\tHyundai\tDistance\n"
    "Lexington KY\t2,019\t2,087\tHome market\n"
    "Louisville KY\t549\t595\t60 mi\n"
    "Georgetown KY\t286\t251\t17 mi\n"
    "Richmond KY\t272\t297\t18 mi\n"
    "Frankfort KY\t172\t191\t29 mi\n"
    "Out-of-market spillover (Indianapolis, etc.) excluded — Cars Social reach concentrates in the Lexington DMA.\n"
    "\n"
    "PINPOINT RECOMMENDATIONS — ZIP TARGETS\n"
    "Based on Lexington DMA ZIP demand trend (Q1 2026 YoY) vs. current Cars Social reach. See interactive maps below.\n"
    "Tier 1 — Activate Now (17–34 mi · Growing Demand · No Current Social Reach)\n"
    "ZIP\tCity\tDistance\tQ1 2026 Demand\tWhy It Matters\n"
    "40384\tVersailles\t17 mi\t+20.5% YoY\tWoodford Co. — horse-country demographics\n"
    "41031\tCynthiana\t29 mi\t+26.1% YoY\tHarrison Co. — growing, zero social reach\n"
    "40472\tRavenna\t34 mi\t+83.1% YoY\tLargest demand surge in gap ring\n"
    "Tier 2 — Consider Next (35–55 mi)\n"
    "ZIP\tCity\tDistance\tQ1 2026 Demand\tNote\n"
    "40456\tMount Vernon\t41 mi\t+29.8% YoY\tRockcastle Co. seat\n"
    "40437\tHustonville\t43 mi\t+45.7% YoY\tLincoln Co.\n"
    "\n"
    "Interactive Pinpoint Maps:\n"
    "Buick GMC: https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_buickgmc_06.03.26.html\n"
    "Hyundai: https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_hyundai_06.03.26.html\n"
    "\n"
    "DATA SOURCES & METHODOLOGY\n"
    "GA4: Don Franklin Lexington Buick GMC (467758077) · Don Franklin Lexington Hyundai (467133052)\n"
    "Cars Social = campaign cars.com_carssocial (source cars.com / referral). EXCLUDES DriveAuto paid social (meta / cpc_social), organic social, and other referrers — previously these were bundled together.\n"
    "Window: January 1 – May 31, 2026 · ZIP demand: Tableau Searches-by-ZIP (Q1 2026 YoY) · pgeocode\n"
    "Prepared June 12, 2026 · Jake Crawley · Claude Code\n"
)

docs_batch(DOC_ID, [{'insertText': {'location': {'index': 1}, 'text': full_text}}])
print(f"Inserted {len(full_text)} chars.")
time.sleep(0.8)

doc2 = docs_get(DOC_ID)
para_map = {}
for elem in doc2.get('body', {}).get('content', []):
    if 'paragraph' not in elem:
        continue
    si, ei = elem.get('startIndex', 0), elem.get('endIndex', 0)
    text = ''.join(pe.get('textRun', {}).get('content', '')
                   for pe in elem['paragraph'].get('elements', [])).strip()
    if text and text not in para_map:
        para_map[text] = (si, ei)
print(f"Parsed {len(para_map)} paragraphs")

style_requests = []
def add_style(si, ei, bold=False, size=11, fg=None, bg=None, align='START', named='NORMAL_TEXT'):
    style_requests.append({'updateParagraphStyle': {
        'range': {'startIndex': si, 'endIndex': ei},
        'paragraphStyle': {'namedStyleType': named, 'alignment': align},
        'fields': 'namedStyleType,alignment'}})
    ts = {'bold': bold, 'fontSize': {'magnitude': size, 'unit': 'PT'}}
    if fg: ts['foregroundColor'] = {'color': {'rgbColor': fg}}
    fields = 'bold,fontSize' + (',foregroundColor' if fg else '')
    style_requests.append({'updateTextStyle': {
        'range': {'startIndex': si, 'endIndex': max(si+1, ei-1)},
        'textStyle': ts, 'fields': fields}})
    if bg:
        style_requests.append({'updateParagraphStyle': {
            'range': {'startIndex': si, 'endIndex': ei},
            'paragraphStyle': {'shading': {'backgroundColor': {'color': {'rgbColor': bg}}}},
            'fields': 'shading'}})

def s(key, **kw):
    coords = para_map.get(key)
    if coords: add_style(coords[0], coords[1], **kw)

# Title block
s('Cars Social Case Study', bold=True, size=24, fg=WHITE, bg=PURPLE, align='CENTER', named='HEADING_1')
s('Don Franklin Automotive Group · Lexington, KY · January–May 2026', size=12, fg=WHITE, bg=PURPLE, align='CENTER')

# H2 section headers (teal)
for h in ['PERFORMANCE SNAPSHOT — CARS SOCIAL (cars.com_carssocial)',
          'MONTHLY TREND — CARS SOCIAL SESSIONS',
          'CARS SOCIAL PERFORMANCE — BUICK GMC (Jan–May)',
          'CARS SOCIAL PERFORMANCE — HYUNDAI (Jan–May)',
          'ON-SITE ENGAGEMENT — ASC EVENTS FROM CARS SOCIAL (Jan–May)',
          'AUDIENCE PROFILE — CARS SOCIAL SHOPPER (Jan–May)',
          'GEOGRAPHIC REACH — TOP CITIES (Cars Social, Jan–May)',
          'PINPOINT RECOMMENDATIONS — ZIP TARGETS',
          'DATA SOURCES & METHODOLOGY']:
    s(h, bold=True, size=11, fg=WHITE, bg=TEAL, named='HEADING_2')

# H3 sub-headers (purple)
for h in ['Buick GMC — ASC Event\tCount', 'Hyundai — ASC Event\tCount',
          'Tier 1 — Activate Now (17–34 mi · Growing Demand · No Current Social Reach)',
          'Tier 2 — Consider Next (35–55 mi)', 'Interactive Pinpoint Maps:']:
    s(h, bold=True, size=10, fg=PURPLE, bg=LGRAY, named='HEADING_3')

# KPI cards
s('11,595\tCars Social Sessions\t5,593 Buick GMC · 6,002 Hyundai (Jan–May)', bold=True, size=14, fg=PURPLE, bg=LPURP)
for kpi in ['91%\tNet-New Shoppers\t87% Buick GMC · 95% Hyundai — first-time site visitors',
            '55–61%\tEngagement Rate\tBeats dealer paid social (DriveAuto 42–56%)',
            '94%\tMobile-First\tCars Social shoppers are nearly all on mobile']:
    s(kpi, bold=True, size=12, fg=TEAL, bg=LTEAL)

# Table header rows (purple bg / white)
for th in ['Month\tBuick GMC\tHyundai\tCombined\tNote',
           'Metric\tCars Social\tBenchmark / Context',
           'Metric\tBuick GMC\tHyundai',
           'City\tBuick GMC\tHyundai\tDistance',
           'ZIP\tCity\tDistance\tQ1 2026 Demand\tWhy It Matters',
           'ZIP\tCity\tDistance\tQ1 2026 Demand\tNote']:
    s(th, bold=True, size=10, fg=WHITE, bg=PURPLE)

# Monthly trend rows (alt shading) + total row highlighted
month_rows = ['January 2026\t1,531\t830\t2,361\t', 'February 2026\t1,388\t1,410\t2,798\t',
              'March 2026\t1,200\t1,748\t2,948\tPeak', 'April 2026\t728\t1,053\t1,781\t',
              'May 2026\t791\t932\t1,723\t']
for i, row in enumerate(month_rows):
    s(row, size=10, fg=PURPLE if i % 2 == 0 else DGRAY, bg=LPURP if i % 2 == 0 else LGRAY)
s('Jan–May Total\t5,593\t6,002\t11,595\t', bold=True, size=10, fg=WHITE, bg=TEAL)

# Performance + audience data rows (alt shading)
perf_rows = ['Sessions\t5,593\t6.8% of 82,415 total sessions',
             'Net-new shoppers\t3,092 (87%)\tTop-of-funnel reach, not retargeting',
             'Engagement rate\t55.0%\tDealer paid social (DriveAuto) 42.1% → +12.9pp',
             'VDP views generated\t6,503\t1.16 vehicle pages per session',
             'Media interactions\t3,759\tPhoto / video engagement',
             'Sessions\t6,002\t3.8% of 156,231 total sessions',
             'Net-new shoppers\t3,869 (95%)\tTop-of-funnel reach, not retargeting',
             'Engagement rate\t61.0%\tDealer paid social (DriveAuto) 55.9% → +5.1pp',
             'VDP views generated\t6,125\t1.02 vehicle pages per session',
             'Media interactions\t4,261\tPhoto / video engagement',
             'Cars Social sessions\t5,593\t6,002', 'Total users\t3,557\t4,057',
             'New users (net-new)\t3,092 (87%)\t3,869 (95%)', 'Mobile share\t94%\t95%',
             'Engagement rate\t55.0%\t61.0%']
for i, row in enumerate(perf_rows):
    coords = para_map.get(row)
    if coords: add_style(coords[0], coords[1], size=10, bg=LGRAY if i % 2 else None)

# ASC event rows
asc_rows = ['asc_pageview\t7,420', 'asc_item_pageview (VDP views)\t6,503', 'asc_media_interaction\t3,759',
            'asc_itemlist_pageview\t762', 'asc_cta_interaction\t245', 'asc_element_configuration\t187',
            'asc_menu_interaction\t163', 'asc_form_engagement\t12', 'asc_form_submission (KEY)\t2',
            'asc_pageview\t6,917', 'asc_item_pageview (VDP views)\t6,125', 'asc_media_interaction\t4,261',
            'asc_itemlist_pageview\t365', 'asc_cta_interaction\t300', 'asc_menu_interaction\t96',
            'asc_element_configuration\t94', 'asc_form_engagement\t8', 'asc_form_submission (KEY)\t1']
for i, row in enumerate(asc_rows):
    coords = para_map.get(row)
    if coords:
        key = 'KEY' in row
        add_style(coords[0], coords[1], size=10, bold=key, fg=PURPLE if key else None,
                  bg=LPURP if key else (LGRAY if i % 2 else None))

# Geo rows
for row in ['Lexington KY\t2,019\t2,087\tHome market', 'Louisville KY\t549\t595\t60 mi',
            'Georgetown KY\t286\t251\t17 mi', 'Richmond KY\t272\t297\t18 mi',
            'Frankfort KY\t172\t191\t29 mi']:
    coords = para_map.get(row)
    if coords:
        bg = LPURP if row.startswith('Lexington') else LGRAY
        add_style(coords[0], coords[1], size=10, bg=bg)

# ZIP target rows
for row in ['40384\tVersailles\t17 mi\t+20.5% YoY\tWoodford Co. — horse-country demographics',
            '41031\tCynthiana\t29 mi\t+26.1% YoY\tHarrison Co. — growing, zero social reach',
            '40472\tRavenna\t34 mi\t+83.1% YoY\tLargest demand surge in gap ring']:
    s(row, bold=True, size=10, fg=TEAL, bg=LTEAL)
for row in ['40456\tMount Vernon\t41 mi\t+29.8% YoY\tRockcastle Co. seat',
            '40437\tHustonville\t43 mi\t+45.7% YoY\tLincoln Co.']:
    s(row, size=10, bg=LGRAY)

# Callouts / notes (gray italic-ish)
for line in ['Spend held flat, but output slipped — Buick GMC nearly halved since January (1,531→791) and combined volume is down ~42% from the March peak. Flat budget + falling sessions points to a delivery/efficiency decline (creative fatigue, audience saturation, or CPM inflation), not a budget cut — worth a Cars Social campaign-health review.',
             'Cars Social is a top-of-funnel discovery channel: heavy vehicle browsing + media engagement, with hard conversions occurring downstream (not on the first social visit).',
             'All events tagged per the Automotive Standards Council (ASC) schema, isolated to Cars Social sessions.',
             'Out-of-market spillover (Indianapolis, etc.) excluded — Cars Social reach concentrates in the Lexington DMA.',
             'Based on Lexington DMA ZIP demand trend (Q1 2026 YoY) vs. current Cars Social reach. See interactive maps below.',
             'GA4: Don Franklin Lexington Buick GMC (467758077) · Don Franklin Lexington Hyundai (467133052)',
             'Cars Social = campaign cars.com_carssocial (source cars.com / referral). EXCLUDES DriveAuto paid social (meta / cpc_social), organic social, and other referrers — previously these were bundled together.',
             'Window: January 1 – May 31, 2026 · ZIP demand: Tableau Searches-by-ZIP (Q1 2026 YoY) · pgeocode']:
    s(line, size=9, fg=DGRAY, bg=LGRAY)

s('Prepared June 12, 2026 · Jake Crawley · Claude Code', size=9, fg=DGRAY, align='CENTER')

print(f"Sending {len(style_requests)} style requests...")
BATCH = 40
for i in range(0, len(style_requests), BATCH):
    result = docs_batch(DOC_ID, style_requests[i:i+BATCH])
    print(f"  Batch {i//BATCH+1}/{(len(style_requests)+BATCH-1)//BATCH}: {'OK' if result else 'FAIL'}")
    time.sleep(0.35)

print(f"\nhttps://docs.google.com/document/d/{DOC_ID}/edit")
