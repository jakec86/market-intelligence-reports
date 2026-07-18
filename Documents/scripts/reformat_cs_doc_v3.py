"""
Cars Social Case Study — Don Franklin (REBUILD v3 — REAL TABLES)
Same corrected/isolated Jan–May data as v2, but rendered with actual Google Docs
tables (marker + reverse-order insertTable + structural styling) to match v1 final.
Data: GA4 props 467758077 (Buick GMC) / 467133052 (Hyundai), campaign cars.com_carssocial.
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

def docs_get():
    req = urllib.request.Request(f'https://docs.googleapis.com/v1/documents/{DOC_ID}',
        headers={'Authorization': f'Bearer {AT}'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def batch(reqs):
    body = json.dumps({'requests': reqs}).encode()
    for attempt in range(5):
        req = urllib.request.Request(f'https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate',
            data=body, headers={'Authorization': f'Bearer {AT}', 'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            if e.code == 429 and attempt < 4:
                wait = 20 * (attempt + 1)
                print(f"  429 quota — backoff {wait}s"); time.sleep(wait); continue
            print(f"  batch {e.code}: {msg[:200]}"); return None

PURPLE = {'red': 0.42, 'green': 0.176, 'blue': 0.545}
TEAL   = {'red': 0.0,  'green': 0.659, 'blue': 0.557}
WHITE  = {'red': 1.0,  'green': 1.0,  'blue': 1.0}
LGRAY  = {'red': 0.953,'green': 0.953,'blue': 0.976}
DGRAY  = {'red': 0.302,'green': 0.302,'blue': 0.302}
LTEAL  = {'red': 0.88, 'green': 0.97, 'blue': 0.95}
LPURP  = {'red': 0.93, 'green': 0.88, 'blue': 0.97}
POPPINS = {'fontFamily': 'Poppins'}

# ---- document model: ordered list of blocks ----
SUB = 'Don Franklin Automotive Group · Lexington, KY · January–May 2026'
CALLOUT = ('Spend held flat, but output slipped — Buick GMC nearly halved since January (1,531→791) and '
           'combined volume is down ~42% from the March peak. Flat budget + falling sessions points to a '
           'delivery/efficiency decline (creative fatigue, audience saturation, or CPM inflation), not a '
           'budget cut — worth a Cars Social campaign-health review.')
N_ASC = 'All events tagged per the Automotive Standards Council (ASC) schema, isolated to Cars Social sessions.'
N_TOF = ('Cars Social is a top-of-funnel discovery channel: heavy vehicle browsing + media engagement, with '
         'hard conversions occurring downstream (not on the first social visit).')
N_GEO = 'Out-of-market spillover (Indianapolis, etc.) excluded — Cars Social reach concentrates in the Lexington DMA.'
N_PIN = 'Based on Lexington DMA ZIP demand trend (Q1 2026 YoY) vs. current Cars Social reach. See interactive maps below.'
N_SRC = 'GA4: Don Franklin Lexington Buick GMC (467758077) · Don Franklin Lexington Hyundai (467133052)'
N_DEF = ('Cars Social = campaign cars.com_carssocial (source cars.com / referral). EXCLUDES DriveAuto paid social '
         '(meta / cpc_social), organic social, and other referrers — previously these were bundled together.')
N_WIN = 'Window: January 1 – May 31, 2026 · ZIP demand: Tableau Searches-by-ZIP (Q1 2026 YoY) · pgeocode'
N_FOOT = 'Prepared June 12, 2026 · Jake Crawley · Claude Code'
URL_B = 'https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_buickgmc_06.12.26.html'
URL_H = 'https://jakec86.github.io/market-intelligence-reports/DonFranklin/cars_social_pinpoint_lexington_hyundai_06.12.26.html'
MAP_B = 'Buick GMC Intelligence Map'
MAP_H = 'Hyundai Intelligence Map'

TABLES = {
  0: ('kpi', [['11,595', '91%', '55–61%', '94%'],
              ['Cars Social Sessions\n5,593 Buick GMC · 6,002 Hyundai (Jan–May)',
               'Net-New Shoppers\n87% Buick GMC · 95% Hyundai',
               'Engagement Rate\nBeats DriveAuto paid social (42–56%)',
               'Mobile-First\nNearly all sessions on mobile']]),
  1: ('monthly', [['Month','Buick GMC','Hyundai','Combined','Note'],
              ['January 2026','1,531','830','2,361',''],
              ['February 2026','1,388','1,410','2,798',''],
              ['March 2026','1,200','1,748','2,948','Peak'],
              ['April 2026','728','1,053','1,781',''],
              ['May 2026','791','932','1,723',''],
              ['Jan–May Total','5,593','6,002','11,595','']]),
  2: ('std', [['Metric','Cars Social','Benchmark / Context'],
              ['Sessions','5,593','6.8% of 82,415 total sessions'],
              ['Net-new shoppers','3,092 (87%)','Top-of-funnel reach, not retargeting'],
              ['Engagement rate','55.0%','Dealer paid social (DriveAuto) 42.1% → +12.9pp'],
              ['VDP views generated','6,503','1.16 vehicle pages per session'],
              ['Media interactions','3,759','Photo / video engagement']]),
  3: ('std', [['Metric','Cars Social','Benchmark / Context'],
              ['Sessions','6,002','3.8% of 156,231 total sessions'],
              ['Net-new shoppers','3,869 (95%)','Top-of-funnel reach, not retargeting'],
              ['Engagement rate','61.0%','Dealer paid social (DriveAuto) 55.9% → +5.1pp'],
              ['VDP views generated','6,125','1.02 vehicle pages per session'],
              ['Media interactions','4,261','Photo / video engagement']]),
  4: ('asc', [['Buick GMC — ASC Event','Count'],
              ['asc_pageview','7,420'],['asc_item_pageview (VDP views)','6,503'],
              ['asc_media_interaction','3,759'],['asc_itemlist_pageview','762'],
              ['asc_cta_interaction','245'],['asc_element_configuration','187'],
              ['asc_menu_interaction','163'],['asc_form_engagement','12'],
              ['asc_form_submission (KEY)','2']]),
  5: ('asc', [['Hyundai — ASC Event','Count'],
              ['asc_pageview','6,917'],['asc_item_pageview (VDP views)','6,125'],
              ['asc_media_interaction','4,261'],['asc_itemlist_pageview','365'],
              ['asc_cta_interaction','300'],['asc_menu_interaction','96'],
              ['asc_element_configuration','94'],['asc_form_engagement','8'],
              ['asc_form_submission (KEY)','1']]),
  6: ('std', [['Metric','Buick GMC','Hyundai'],
              ['Cars Social sessions','5,593','6,002'],['Total users','3,557','4,057'],
              ['New users (net-new)','3,092 (87%)','3,869 (95%)'],['Mobile share','94%','95%'],
              ['Engagement rate','55.0%','61.0%']]),
  7: ('std', [['City','Buick GMC','Hyundai','Distance'],
              ['Lexington KY','2,019','2,087','Home market'],['Louisville KY','549','595','60 mi'],
              ['Georgetown KY','286','250','17 mi'],['Richmond KY','272','296','18 mi'],
              ['Frankfort KY','172','191','29 mi'],['Danville KY','140','122','35 mi'],
              ['Mount Sterling KY','136','131','27 mi'],['Winchester KY','135','160','14 mi']]),
  8: ('tier1', [['ZIP','City','Distance','Q1 2026 Demand','Why It Matters'],
              ['40384','Versailles','17 mi','+20.5% YoY','Woodford Co. — horse-country demographics'],
              ['41031','Cynthiana','29 mi','+26.1% YoY','Harrison Co. — growing, zero social reach'],
              ['40472','Ravenna','34 mi','+83.1% YoY','Largest demand surge in gap ring']]),
  9: ('std', [['ZIP','City','Distance','Q1 2026 Demand','Note'],
              ['40456','Mount Vernon','41 mi','+29.8% YoY','Rockcastle Co. seat'],
              ['40437','Hustonville','43 mi','+45.7% YoY','Lincoln Co.']]),
}

# document order: (kind, value). kind: h1,h2,h3,p,tbl
DOCBLOCKS = [
  ('h1','Cars Social Case Study'), ('p',SUB),
  ('h2','PERFORMANCE SNAPSHOT — CARS SOCIAL (cars.com_carssocial)'), ('tbl',0),
  ('h2','MONTHLY TREND — CARS SOCIAL SESSIONS'), ('tbl',1), ('note',CALLOUT),
  ('h2','CARS SOCIAL PERFORMANCE — BUICK GMC (Jan–May)'), ('tbl',2),
  ('h2','CARS SOCIAL PERFORMANCE — HYUNDAI (Jan–May)'), ('tbl',3),
  ('h2','ON-SITE ENGAGEMENT — ASC EVENTS FROM CARS SOCIAL (Jan–May)'), ('note',N_ASC),
  ('tbl',4), ('tbl',5), ('note',N_TOF),
  ('h2','AUDIENCE PROFILE — CARS SOCIAL SHOPPER (Jan–May)'), ('tbl',6),
  ('h2','GEOGRAPHIC REACH — TOP CITIES (Cars Social, Jan–May)'), ('tbl',7), ('note',N_GEO),
  ('h2','PINPOINT RECOMMENDATIONS — ZIP TARGETS'), ('note',N_PIN),
  ('h3','Tier 1 — Activate Now (17–34 mi · Growing Demand · No Current Social Reach)'), ('tbl',8),
  ('h3','Tier 2 — Consider Next (35–55 mi)'), ('tbl',9),
  ('h3','Interactive Pinpoint Maps:'), ('p',MAP_B), ('p',MAP_H),
  ('h2','DATA SOURCES & METHODOLOGY'), ('note',N_SRC), ('note',N_DEF), ('note',N_WIN), ('note',N_FOOT),
]

# ---------- Phase A: clear + insert body text with table markers ----------
doc = docs_get()
content = doc['body']['content']
end_idx = content[-1].get('endIndex', 2)
if end_idx > 2:
    batch([{'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_idx - 1}}}])
    time.sleep(0.5)

lines = []
for kind, val in DOCBLOCKS:
    lines.append(f'@@TBL{val}@@' if kind == 'tbl' else val)
body_text = '\n'.join(lines) + '\n'
batch([{'insertText': {'location': {'index': 1}, 'text': body_text}}])
print(f"Inserted body ({len(body_text)} chars)")
time.sleep(0.7)

# ---------- Phase B: replace markers with empty tables, BOTTOM->TOP ----------
def find_markers():
    d = docs_get()
    m = {}
    for el in d['body']['content']:
        if 'paragraph' not in el: continue
        txt = ''.join(e.get('textRun', {}).get('content', '') for e in el['paragraph'].get('elements', [])).strip()
        if txt.startswith('@@TBL') and txt.endswith('@@'):
            tid = int(txt[5:-2])
            m[tid] = (el['startIndex'], el['endIndex'])
    return m

markers = find_markers()
for tid in sorted(markers, key=lambda k: markers[k][0], reverse=True):
    si, ei = markers[tid]
    rows = TABLES[tid][1]
    R, C = len(rows), len(rows[0])
    batch([{'deleteContentRange': {'range': {'startIndex': si, 'endIndex': ei - 1}}},
           {'insertTable': {'rows': R, 'columns': C, 'location': {'index': si}}}])
    time.sleep(0.4)
print("Inserted all empty tables")
time.sleep(0.6)

# ---------- Phase C: fill cells (read true indices, fill high->low) ----------
def collect_tables():
    d = docs_get()
    tbls = [el for el in d['body']['content'] if 'table' in el]
    return d, tbls

_, tbls = collect_tables()
assert len(tbls) == len(TABLES), f"expected {len(TABLES)} tables, found {len(tbls)}"
fills = []
for ti, el in enumerate(tbls):
    rows = TABLES[ti][1]
    for r, row in enumerate(el['table']['tableRows']):
        for c, cell in enumerate(row['tableCells']):
            text = rows[r][c]
            if text:
                pstart = cell['content'][0]['startIndex']
                fills.append((pstart, text))
fill_reqs = [{'insertText': {'location': {'index': ps}, 'text': t}}
             for ps, t in sorted(fills, key=lambda x: x[0], reverse=True)]
for i in range(0, len(fill_reqs), 20):
    batch(fill_reqs[i:i+20]); time.sleep(0.5)
print(f"Filled {len(fills)} cells")
time.sleep(0.6)

# ---------- Phase D: style tables structurally ----------
def cell_para_range(cell):
    paras = [x for x in cell['content'] if 'paragraph' in x]
    return paras[0]['startIndex'], paras[-1]['endIndex'] - 1

def style_text(s, e, color=None, bold=False, size=None, align=None):
    out = []
    ts = {'weightedFontFamily': POPPINS, 'bold': bold}
    fields = 'weightedFontFamily,bold'
    if color: ts['foregroundColor'] = {'color': {'rgbColor': color}}; fields += ',foregroundColor'
    if size: ts['fontSize'] = {'magnitude': size, 'unit': 'PT'}; fields += ',fontSize'
    out.append({'updateTextStyle': {'range': {'startIndex': s, 'endIndex': e}, 'textStyle': ts, 'fields': fields}})
    if align:
        out.append({'updateParagraphStyle': {'range': {'startIndex': s, 'endIndex': e},
            'paragraphStyle': {'alignment': align}, 'fields': 'alignment'}})
    return out

def cell_bg(tstart, r, c, color):
    return {'updateTableCellStyle': {'tableCellStyle': {'backgroundColor': {'color': {'rgbColor': color}}},
        'fields': 'backgroundColor',
        'tableRange': {'tableCellLocation': {'tableStartLocation': {'index': tstart},
            'rowIndex': r, 'columnIndex': c}, 'rowSpan': 1, 'columnSpan': 1}}}

_, tbls = collect_tables()
style_reqs = []
for ti, el in enumerate(tbls):
    kind = TABLES[ti][0]
    tstart = el['startIndex']
    trows = el['table']['tableRows']
    for r, row in enumerate(trows):
        for c, cell in enumerate(row['tableCells']):
            s, e = cell_para_range(cell)
            if e <= s: continue
            if kind == 'kpi':
                if r == 0:
                    style_reqs.append(cell_bg(tstart, r, c, LPURP))
                    style_reqs += style_text(s, e, PURPLE, True, 18, 'CENTER')
                else:
                    style_reqs.append(cell_bg(tstart, r, c, LPURP))
                    style_reqs += style_text(s, e, DGRAY, False, 9, 'CENTER')
            elif r == 0:  # header row for all non-kpi tables
                style_reqs.append(cell_bg(tstart, r, c, PURPLE))
                style_reqs += style_text(s, e, WHITE, True, 10, 'CENTER')
            else:  # data rows
                bg = None; fg = None; bold = False
                if kind == 'monthly' and r == len(trows) - 1:      # total row
                    bg = TEAL; fg = WHITE; bold = True
                elif kind == 'tier1':                               # tier1 highlight
                    bg = LTEAL; fg = TEAL; bold = True
                elif kind == 'asc' and '(KEY)' in TABLES[ti][1][r][0]:
                    bg = LPURP; fg = PURPLE; bold = True
                elif r % 2 == 1:                                    # alt shading
                    bg = LGRAY
                if bg: style_reqs.append(cell_bg(tstart, r, c, bg))
                align = 'START' if c == 0 else 'CENTER'
                style_reqs += style_text(s, e, fg, bold, 10, align)

# headings & notes by text match (unique strings)
d = docs_get()
pmap = {}
for el in d['body']['content']:
    if 'paragraph' not in el: continue
    txt = ''.join(e.get('textRun', {}).get('content', '') for e in el['paragraph'].get('elements', [])).strip()
    if txt and txt not in pmap:
        pmap[txt] = (el['startIndex'], el['endIndex'])

def style_para(text, named='NORMAL_TEXT', size=11, color=None, bg=None, bold=False, align='START'):
    if text not in pmap: return
    si, ei = pmap[text]
    style_reqs.append({'updateParagraphStyle': {'range': {'startIndex': si, 'endIndex': ei},
        'paragraphStyle': {'namedStyleType': named, 'alignment': align,
            **({'shading': {'backgroundColor': {'color': {'rgbColor': bg}}}} if bg else {})},
        'fields': 'namedStyleType,alignment' + (',shading' if bg else '')}})
    ts = {'weightedFontFamily': POPPINS, 'bold': bold, 'fontSize': {'magnitude': size, 'unit': 'PT'}}
    fields = 'weightedFontFamily,bold,fontSize'
    if color: ts['foregroundColor'] = {'color': {'rgbColor': color}}; fields += ',foregroundColor'
    style_reqs.append({'updateTextStyle': {'range': {'startIndex': si, 'endIndex': max(si+1, ei-1)},
        'textStyle': ts, 'fields': fields}})

style_para('Cars Social Case Study', 'HEADING_1', 24, WHITE, PURPLE, True, 'CENTER')
style_para(SUB, 'NORMAL_TEXT', 12, WHITE, PURPLE, False, 'CENTER')
for _, val in DOCBLOCKS:
    pass
for txt in [b[1] for b in DOCBLOCKS if b[0] == 'h2']:
    style_para(txt, 'HEADING_2', 11, WHITE, TEAL, True)
for txt in [b[1] for b in DOCBLOCKS if b[0] == 'h3']:
    style_para(txt, 'HEADING_3', 10, PURPLE, LGRAY, True)
for txt in [CALLOUT, N_ASC, N_TOF, N_GEO, N_PIN, N_SRC, N_DEF, N_WIN]:
    style_para(txt, 'NORMAL_TEXT', 9, DGRAY, LGRAY)
style_para(N_FOOT, 'NORMAL_TEXT', 9, DGRAY, None, False, 'CENTER')
def style_link(text, url):
    if text not in pmap: return
    si, ei = pmap[text]
    style_reqs.append({'updateParagraphStyle': {'range': {'startIndex': si, 'endIndex': ei},
        'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT', 'alignment': 'START'},
        'fields': 'namedStyleType,alignment'}})
    style_reqs.append({'updateTextStyle': {'range': {'startIndex': si, 'endIndex': max(si+1, ei-1)},
        'textStyle': {'link': {'url': url}, 'underline': True, 'bold': True,
            'fontSize': {'magnitude': 11, 'unit': 'PT'}, 'weightedFontFamily': POPPINS,
            'foregroundColor': {'color': {'rgbColor': {'red': 0.05, 'green': 0.43, 'blue': 0.99}}}},
        'fields': 'link,underline,bold,fontSize,weightedFontFamily,foregroundColor'}})

style_link(MAP_B, URL_B)
style_link(MAP_H, URL_H)

print(f"Applying {len(style_reqs)} style requests...")
B = 30
for i in range(0, len(style_reqs), B):
    ok = batch(style_reqs[i:i+B])
    print(f"  style batch {i//B+1}/{(len(style_reqs)+B-1)//B}: {'OK' if ok else 'FAIL'}")
    time.sleep(0.3)

print(f"\nhttps://docs.google.com/document/d/{DOC_ID}/edit")
