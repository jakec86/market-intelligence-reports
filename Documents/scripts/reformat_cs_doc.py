import json, urllib.request, urllib.parse, time

creds = json.load(open('/Users/jcrawley/.claude/tokens/gdocs_credentials.json'))
s = json.load(open('/Users/jcrawley/.claude/settings.json'))
env = s['mcpServers']['google-docs']['env']
CLIENT_ID = env['GOOGLE_CLIENT_ID']
CLIENT_SECRET = env['GOOGLE_CLIENT_SECRET']

payload = urllib.parse.urlencode({
    'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
    'refresh_token': creds.get('refresh_token'), 'grant_type': 'refresh_token'
}).encode()
req = urllib.request.Request('https://oauth2.googleapis.com/token', data=payload,
    headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
with urllib.request.urlopen(req, timeout=10) as r:
    AT = json.loads(r.read())['access_token']
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
    "PERFORMANCE SNAPSHOT\n"
    "53,618\tSessions Jan–May\t25,486 Buick GMC · 28,132 Hyundai\n"
    "#3\tTraffic Source\tRanked behind Direct + Google Organic\n"
    "49%\tSession Engagement\tComparable to Google Organic (46.6%)\n"
    "17\tHard Conversions\t11 Buick GMC · 6 Hyundai (click-to-call + forms)\n"
    "\n"
    "MONTHLY TREND — CARS SOCIAL SESSIONS\n"
    "Month\tBuick GMC\tHyundai\tCombined\tVisual Bar\n"
    "January 2026\t5,984\t5,962\t11,946\t████████████\n"
    "February 2026\t5,851\t5,637\t11,488\t███████████\n"
    "March 2026\t5,305\t6,438\t11,743\t████████████ ◄ Peak (Hyundai)\n"
    "April 2026\t3,774\t5,389\t9,163\t█████████\n"
    "May 2026\t4,572\t4,706\t9,278\t█████████\n"
    "June 2026*\t351\t329\t680\t▌\n"
    "*June 1–3 only. Peak month: March 2026 (11,743 combined).\n"
    "\n"
    "CARS SOCIAL vs. GOOGLE ORGANIC (Buick GMC · Last 28 Days)\n"
    "Metric\tCars Social\tGoogle Organic\tResult\n"
    "Sessions\t4,168\t3,779\tCars Social ✓\n"
    "Share of Traffic\t22.9%\t20.8%\tCars Social ✓\n"
    "Engagement Rate\t49.3%\t46.6%\tCars Social ✓\n"
    "Traffic Rank\t#3 Source\t#2 Source\t—\n"
    "Cars Social out-performed Google Organic in the most recent 28-day window at a higher engagement rate.\n"
    "\n"
    "TOP MODELS DRIVEN BY CARS SOCIAL\n"
    "Buick GMC — Top Models (Last 28 Days)\n"
    "Model\tSocial Sessions\tSignal\n"
    "GMC HUMMER EV (all trims)\t473\t★★★ Halo model — social magnet\n"
    "GMC Yukon Denali (all trims)\t332\t★★★ Aspirational reach\n"
    "Buick Enclave Avenir\t184\t★★ Luxury crossover\n"
    "GMC Acadia AT4\t140\t★★\n"
    "GMC Sierra 2500 HD AT4\t108\t★★\n"
    "GMC Terrain AT4 + Encore GX\t194\t★ Entry/mid\n"
    "Hyundai — Top Models (Last 28 Days)\n"
    "Model\tSocial Sessions\tSignal\n"
    "Palisade (all trims)\t188\t★★★ Dominant — 3 trims in top 10\n"
    "Sonata N-Line\t48\t★★ Performance appeal\n"
    "Santa Fe Limited\t38\t★★\n"
    "IONIQ 9 SEL (EV)\t34\t★ Early EV interest\n"
    "Santa Cruz XRT\t33\t★\n"
    "\n"
    "NEW USER ACQUISITION (Cars Social, Jan–Jun 2026)\n"
    "Store\tTotal CS Sessions\tNew Users\tNew User %\n"
    "Buick GMC\t25,880\t15,261\t59%\n"
    "Hyundai\t28,320\t21,913\t77%\n"
    "Cars Social is generating net-new shoppers — not retargeting existing site visitors.\n"
    "\n"
    "DEVICE BREAKDOWN\n"
    "Store\tMobile\tDesktop\tTablet\n"
    "Buick GMC\t92%\t3%\t5%\n"
    "Hyundai\t76%\t21%\t3%\n"
    "Hyundai desktop sessions engage at 95.3% — highest-intent social traffic.\n"
    "\n"
    "GEOGRAPHIC REACH — TOP CITIES (Cars Social Sessions, Jan–Jun 2026)\n"
    "City\tBuick GMC\tHyundai\tDistance\n"
    "Lexington KY\t5,802\t5,377\tHome market\n"
    "Louisville KY\t2,599\t2,885\t60 mi\n"
    "Richmond KY\t740\t714\t18 mi\n"
    "Georgetown KY\t671\t576\t17 mi\n"
    "Frankfort KY\t604\t634\t29 mi\n"
    "Winchester KY\t414\t461\t14 mi\n"
    "Mount Sterling KY\t356\t432\t27 mi\n"
    "\n"
    "PINPOINT RECOMMENDATIONS\n"
    "Tier 1 — Add Now (0–35 mi, Growing Demand, Gap in Social Reach)\n"
    "ZIP\tCity\tDistance\tDemand Trend\tAction\n"
    "40384\tVersailles\t17 mi\t+20.5% YoY\tPINPOINT — Woodford Co. horse country\n"
    "41031\tCynthiana\t29 mi\t+26.1% YoY\tPINPOINT — Harrison Co. seat\n"
    "40472\tRavenna\t34 mi\t+83.1% YoY\tPINPOINT — Largest demand surge in gap ring\n"
    "Tier 2 — Secondary (35–55 mi)\n"
    "ZIP\tCity\tDistance\tDemand Trend\tAction\n"
    "40456\tMount Vernon\t41 mi\t+29.8% YoY\tConsider Pinpoint\n"
    "40437\tHustonville\t43 mi\t+45.7% YoY\tConsider Pinpoint\n"
    "\n"
    "Interactive Pinpoint Maps:\n"
    "Buick GMC: https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_buickgmc_06.03.26.html\n"
    "Hyundai: https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_hyundai_06.03.26.html\n"
    "\n"
    "DATA SOURCES & CHECKLIST\n"
    "Sources: GA4 (Properties 467758077 / 467133052) · Tableau Cars Social · pgeocode\n"
    "☐ Add dealer quote from DF Lex Buick GMC or Hyundai contact\n"
    "☐ Pull full June 2026 Tableau metrics at month-end\n"
    "☐ Check admin.cars.com ROI One-Sheeter for lead attribution\n"
    "☐ Confirm Cars Social start date for both stores\n"
    "☐ Verify Hyundai form engagement vs. actual CRM lead volume\n"
    "\n"
    "Prepared June 3, 2026 · Jake Crawley · Claude Code\n"
)

docs_batch(DOC_ID, [{'insertText': {'location': {'index': 1}, 'text': full_text}}])
print(f"Inserted {len(full_text)} chars.")
time.sleep(0.8)

doc2 = docs_get(DOC_ID)
content2 = doc2.get('body', {}).get('content', [])
para_map = {}
for elem in content2:
    if 'paragraph' not in elem:
        continue
    si = elem.get('startIndex', 0)
    ei = elem.get('endIndex', 0)
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
        'fields': 'namedStyleType,alignment'
    }})
    ts = {'bold': bold, 'fontSize': {'magnitude': size, 'unit': 'PT'}}
    if fg:
        ts['foregroundColor'] = {'color': {'rgbColor': fg}}
    fields = 'bold,fontSize' + (',foregroundColor' if fg else '')
    style_requests.append({'updateTextStyle': {
        'range': {'startIndex': si, 'endIndex': max(si+1, ei-1)},
        'textStyle': ts, 'fields': fields
    }})
    if bg:
        style_requests.append({'updateParagraphStyle': {
            'range': {'startIndex': si, 'endIndex': ei},
            'paragraphStyle': {'shading': {'backgroundColor': {'color': {'rgbColor': bg}}}},
            'fields': 'shading'
        }})

def s(key, **kw):
    coords = para_map.get(key)
    if coords:
        add_style(coords[0], coords[1], **kw)

s('Cars Social Case Study', bold=True, size=24, fg=WHITE, bg=PURPLE, align='CENTER', named='HEADING_1')
s('Don Franklin Automotive Group · Lexington, KY · January–May 2026',
  bold=False, size=12, fg=WHITE, bg=PURPLE, align='CENTER')

for h in ['PERFORMANCE SNAPSHOT', 'MONTHLY TREND — CARS SOCIAL SESSIONS',
          'CARS SOCIAL vs. GOOGLE ORGANIC (Buick GMC · Last 28 Days)',
          'TOP MODELS DRIVEN BY CARS SOCIAL',
          'NEW USER ACQUISITION (Cars Social, Jan–Jun 2026)',
          'DEVICE BREAKDOWN',
          'GEOGRAPHIC REACH — TOP CITIES (Cars Social Sessions, Jan–Jun 2026)',
          'PINPOINT RECOMMENDATIONS', 'DATA SOURCES & CHECKLIST']:
    s(h, bold=True, size=11, fg=WHITE, bg=TEAL, named='HEADING_2')

for h in ['Buick GMC — Top Models (Last 28 Days)', 'Hyundai — Top Models (Last 28 Days)',
          'Tier 1 — Add Now (0–35 mi, Growing Demand, Gap in Social Reach)',
          'Tier 2 — Secondary (35–55 mi)', 'Interactive Pinpoint Maps:',
          'Sources: GA4 (Properties 467758077 / 467133052) · Tableau Cars Social · pgeocode']:
    s(h, bold=True, size=10, fg=PURPLE, bg=LGRAY, named='HEADING_3')

s('53,618\tSessions Jan–May\t25,486 Buick GMC · 28,132 Hyundai', bold=True, size=14, fg=PURPLE, bg=LPURP)
for kpi in ['#3\tTraffic Source\tRanked behind Direct + Google Organic',
            '49%\tSession Engagement\tComparable to Google Organic (46.6%)',
            '17\tHard Conversions\t11 Buick GMC · 6 Hyundai (click-to-call + forms)']:
    s(kpi, bold=True, size=12, fg=TEAL, bg=LTEAL)

for th in ['Month\tBuick GMC\tHyundai\tCombined\tVisual Bar',
           'Metric\tCars Social\tGoogle Organic\tResult',
           'Store\tTotal CS Sessions\tNew Users\tNew User %',
           'Store\tMobile\tDesktop\tTablet',
           'City\tBuick GMC\tHyundai\tDistance',
           'ZIP\tCity\tDistance\tDemand Trend\tAction']:
    s(th, bold=True, size=10, fg=WHITE, bg=PURPLE)

for th in ['Model\tSocial Sessions\tSignal']:
    coords = para_map.get(th)
    if coords:
        add_style(coords[0], coords[1], bold=True, size=10, fg=WHITE, bg=PURPLE)

bar_rows = [
    'January 2026\t5,984\t5,962\t11,946\t████████████',
    'February 2026\t5,851\t5,637\t11,488\t███████████',
    'March 2026\t5,305\t6,438\t11,743\t████████████ ◄ Peak (Hyundai)',
    'April 2026\t3,774\t5,389\t9,163\t█████████',
    'May 2026\t4,572\t4,706\t9,278\t█████████',
    'June 2026*\t351\t329\t680\t▌',
]
for i, row in enumerate(bar_rows):
    s(row, size=10, fg=PURPLE if i%2==0 else DGRAY, bg=LPURP if i%2==0 else LGRAY)

for i, row in enumerate(['Sessions\t4,168\t3,779\tCars Social ✓',
                          'Share of Traffic\t22.9%\t20.8%\tCars Social ✓',
                          'Engagement Rate\t49.3%\t46.6%\tCars Social ✓',
                          'Traffic Rank\t#3 Source\t#2 Source\t—']):
    s(row, size=10, bg=LPURP if i%2==0 else LGRAY)

for row in ['40384\tVersailles\t17 mi\t+20.5% YoY\tPINPOINT — Woodford Co. horse country',
            '41031\tCynthiana\t29 mi\t+26.1% YoY\tPINPOINT — Harrison Co. seat',
            '40472\tRavenna\t34 mi\t+83.1% YoY\tPINPOINT — Largest demand surge in gap ring']:
    s(row, bold=True, size=10, fg=TEAL, bg=LTEAL)

for row in ['40456\tMount Vernon\t41 mi\t+29.8% YoY\tConsider Pinpoint',
            '40437\tHustonville\t43 mi\t+45.7% YoY\tConsider Pinpoint']:
    s(row, size=10, bg=LGRAY)

for ci in ['☐ Add dealer quote from DF Lex Buick GMC or Hyundai contact',
           '☐ Pull full June 2026 Tableau metrics at month-end',
           '☐ Check admin.cars.com ROI One-Sheeter for lead attribution',
           '☐ Confirm Cars Social start date for both stores',
           '☐ Verify Hyundai form engagement vs. actual CRM lead volume']:
    s(ci, size=10, bg=LGRAY)

for row in ['Buick GMC\t25,880\t15,261\t59%', 'Hyundai\t28,320\t21,913\t77%',
            'Buick GMC\t92%\t3%\t5%', 'Hyundai\t76%\t21%\t3%']:
    coords = para_map.get(row)
    if coords:
        add_style(coords[0], coords[1], size=10)

for row in ['Lexington KY\t5,802\t5,377\tHome market', 'Louisville KY\t2,599\t2,885\t60 mi',
            'Richmond KY\t740\t714\t18 mi', 'Georgetown KY\t671\t576\t17 mi',
            'Frankfort KY\t604\t634\t29 mi', 'Winchester KY\t414\t461\t14 mi',
            'Mount Sterling KY\t356\t432\t27 mi']:
    coords = para_map.get(row)
    if coords:
        bg = LPURP if row.startswith('Lexington') else LGRAY
        add_style(coords[0], coords[1], size=10, bg=bg)

for line in ['Cars Social out-performed Google Organic in the most recent 28-day window at a higher engagement rate.',
             'Cars Social is generating net-new shoppers — not retargeting existing site visitors.',
             'Hyundai desktop sessions engage at 95.3% — highest-intent social traffic.',
             '*June 1–3 only. Peak month: March 2026 (11,743 combined).']:
    s(line, size=10, fg=DGRAY, bg=LGRAY)

s('Prepared June 3, 2026 · Jake Crawley · Claude Code', size=9, fg=DGRAY, align='CENTER')

print(f"Sending {len(style_requests)} style requests...")
BATCH = 40
for i in range(0, len(style_requests), BATCH):
    result = docs_batch(DOC_ID, style_requests[i:i+BATCH])
    print(f"  Batch {i//BATCH+1}/{(len(style_requests)+BATCH-1)//BATCH}: {'OK' if result else 'FAIL'}")
    time.sleep(0.35)

print(f"\nhttps://docs.google.com/document/d/{DOC_ID}/edit")
