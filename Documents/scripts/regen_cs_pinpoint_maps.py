"""
Regenerate Don Franklin Cars Social pinpoint maps with ISOLATED Cars Social reach
(campaign cars.com_carssocial, GA4 467758077 / 467133052, Jan–May 2026).

Updates the stale `cities` reach array, the header KPI panel, the total badge,
the legend/tier scale, the data-date, and hides the bundled-data "Demand Chart".
ZIP demand layer + hitlist (Tableau Q1-YoY) are unchanged — still valid.

Reads the 06.03.26 sources, writes 06.12.26 outputs.
"""
import json, re

SRC = '/Users/jcrawley/Documents/Reports/DonFranklin'

# KY city coords (from existing arrays + zipData)
CO = {
 'Lexington':(37.9892,-84.4299),'Louisville':(38.2527,-85.7585),'Georgetown':(38.2098,-84.5596),
 'Richmond':(37.7479,-84.2947),'Frankfort':(38.2009,-84.8733),'Winchester':(37.9901,-84.1794),
 'Mount Sterling':(38.0565,-83.9435),'Danville':(37.6459,-84.7721),'Berea':(37.5687,-84.2963),
 'Nicholasville':(37.8807,-84.573),'Lawrenceburg':(38.0373,-84.8983),'Harrodsburg':(37.7626,-84.8433),
 'Paris':(38.2098,-84.253),'Versailles':(38.0526,-84.7299),'Irvine':(37.6858,-83.9862),
 'Lancaster':(37.6584,-84.5969),'Stanton':(37.8223,-83.7853),'Stanford':(37.5245,-84.6912),
 'Cynthiana':(38.3964,-84.2949),'Owingsville':(38.1532,-83.7564),'Morehead':(38.184,-83.4321),
 'Shelbyville':(38.2115,-85.2244),'Corbin':(36.9495,-84.0971),
}

# Isolated Cars Social sessions by KY city (region=Kentucky), Jan–May 2026
REACH = {
 'buickgmc': [('Lexington',2019),('Louisville',549),('Georgetown',286),('Richmond',272),
   ('Frankfort',172),('Danville',140),('Mount Sterling',136),('Winchester',135),('Berea',120),
   ('Nicholasville',84),('Lawrenceburg',72),('Irvine',50),('Paris',50),('Harrodsburg',50),
   ('Versailles',49),('Lancaster',39),('Stanton',36),('Stanford',32),('Cynthiana',26)],
 'hyundai': [('Lexington',2087),('Louisville',595),('Richmond',296),('Georgetown',250),
   ('Frankfort',191),('Winchester',160),('Mount Sterling',131),('Danville',122),('Nicholasville',109),
   ('Berea',97),('Lawrenceburg',73),('Paris',63),('Harrodsburg',51),('Irvine',46),('Stanton',35),
   ('Cynthiana',33),('Versailles',33),('Owingsville',24),('Stanford',22),('Lancaster',20)],
}

# Per-store header values
STORE = {
 'buickgmc': {'total':5593, 'newpct':87, 'newusers':3092, 'asc':19053, 'er':'55.0%',
              'file':'cars_social_pinpoint_lexington_buickgmc'},
 'hyundai':  {'total':6002, 'newpct':95, 'newusers':3869, 'asc':18167, 'er':'61.0%',
              'file':'cars_social_pinpoint_lexington_hyundai'},
}

NEW_TIER = """function getTierStyle(t){
  if(t>=1500) return {fill:'rgba(55,11,85,0.72)',   stroke:'#370B55'};
  if(t>= 500) return {fill:'rgba(100,30,150,0.65)', stroke:'#6A1E96'};
  if(t>= 200) return {fill:'rgba(129,54,178,0.60)', stroke:'#8136B2'};
  if(t>= 100) return {fill:'rgba(171,116,207,0.55)',stroke:'#AB74CF'};
  if(t>=  50) return {fill:'rgba(217,186,238,0.65)',stroke:'#C8A0E4'};
  return              {fill:'rgba(240,230,250,0.75)',stroke:'#D9BAEE'};
}"""

def cities_js(rows):
    objs = []
    for name, total in rows:
        lat, lng = CO[name]
        objs.append('  {\n    "name": "%s",\n    "lat": %s,\n    "lng": %s,\n    "total": %d,\n    "zips": ""\n  }'
                    % (name, lat, lng, total))
    return 'const cities = [\n' + ',\n'.join(objs) + '\n];'

for key, st in STORE.items():
    path = f'{SRC}/{st["file"]}_06.03.26.html'
    html = open(path, encoding='utf-8').read()
    n = {}

    # 1. cities reach array
    html, n['cities'] = re.subn(r'const cities = \[[\s\S]*?\];', cities_js(REACH[key]).replace('\\','\\\\'), html, count=1)

    # 2. header KPI tiles (label-anchored)
    html, n['total'] = re.subn(r'(Total Sessions</div>\s*<div style="[^"]*">)[\d,]+(</div>)',
                               lambda m: f'{m.group(1)}{st["total"]:,}{m.group(2)}', html, count=1)
    html, n['new'] = re.subn(r'New Users \(\d+%\)(</div>\s*<div style="[^"]*">)[\d,]+(</div>)',
                             lambda m: f'New Users ({st["newpct"]}%){m.group(1)}{st["newusers"]:,}{m.group(2)}', html, count=1)
    html, n['asc'] = re.subn(r'(ASC Events</div>\s*<div style="[^"]*">)[\d,]+(</div>)',
                             lambda m: f'{m.group(1)}{st["asc"]:,}{m.group(2)}', html, count=1)
    html, n['rank'] = re.subn(r'Traffic Rank(</div>\s*<div style="[^"]*">)[^<]+(</div>)',
                              lambda m: f'Engagement Rate{m.group(1)}{st["er"]}{m.group(2)}', html, count=1)

    # 3. total badge + demandConfig total
    html, n['badge'] = re.subn(r"(total-num'\)\.textContent = \()\d+(\)\.toLocaleString\(\))",
                               lambda m: f'{m.group(1)}{st["total"]}{m.group(2)}', html, count=1)
    html, n['cfg'] = re.subn(r'"totalVdps": \d+', f'"totalVdps": {st["total"]}', html, count=1)

    # 4. data-date
    html, n['date'] = re.subn(r'(<span id="data-date">)[^<]*(</span>)',
                              r'\g<1>· Data as of Jun 12, 2026\g<2>', html, count=1)

    # 5. legend buckets
    for old, new in [('<span>5,000+</span>','<span>1,500+</span>'),
                     ('<span>2,000 – 5,000</span>','<span>500 – 1,500</span>'),
                     ('<span>500 – 2,000</span>','<span>200 – 500</span>'),
                     ('<span>&lt; 500</span>','<span>&lt; 200</span>')]:
        html = html.replace(old, new)

    # 6. tier thresholds
    html, n['tier'] = re.subn(r'function getTierStyle\(t\)\{[\s\S]*?\n\}', NEW_TIER, html, count=1)

    # 7. hide stale Demand Chart toggle
    html, n['hide'] = re.subn(r'<div id="mode-toggle">', '<div id="mode-toggle" style="display:none;">', html, count=1)

    # 8. auto-drop the dealer-centered 30-mile radius on load (draggable + clearable)
    html, n['autodrop'] = re.subn(
        r'(\n// Initialize on load)',
        "\n// Auto-drop the dealer's 30-mile radius on load (draggable + clearable via Radius Tool)\n"
        "placeRadius(dealerPin.lat, dealerPin.lng, dealerPin.name);\n\\g<1>",
        html, count=1)

    # 9. fix radius drag: dealer star was blocking the draggable pin (same point, higher z + interactive).
    #    Make the star non-interactive and lift the radius pin above all markers so it's grabbable.
    html, n['star'] = re.subn(r'zIndexOffset:1000, interactive:true', 'zIndexOffset:1000, interactive:false', html, count=1)
    html, n['pinz'] = re.subn(r'zIndexOffset: 500,', 'zIndexOffset: 2100,', html, count=1)

    out = f'{SRC}/{st["file"]}_06.12.26.html'
    open(out, 'w', encoding='utf-8').write(html)
    assert '5802' not in html and '28,132' not in html, "stale value still present!"
    print(f'{key}: {out}')
    print('   subs:', {k:v for k,v in n.items()})
