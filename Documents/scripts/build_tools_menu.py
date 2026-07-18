#!/usr/bin/env python3
"""
Build a single local reference page listing every custom skill/command and every
generated report, so they can be browsed from one place instead of re-discovered
each session. Regenerate any time new skills or report folders are added:

    python3 ~/Documents/scripts/build_tools_menu.py

Output: ~/Documents/tools_menu.html (local file, NOT committed to the
market-intelligence-reports GitHub Pages repo — this lists internal workflow
names and client folders and should stay private).
"""

import os
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path.home() / "Documents" / "Reports"
OUTPUT_PATH = Path.home() / "Documents" / "tools_menu.html"

# Folders under ~/Documents/Reports that are git/tooling internals, not report output.
SKIP_DIRS = {'.git', '.github', '.claude', 'docs', 'Library', 'Documents'}

# ── Skills & workflows — kept in sync with ~/.claude/CLAUDE.md's skill tables ──
SKILLS = [
    # Recurring reporting workflows
    {'name': 'nalley-pb-report', 'category': 'Recurring Reporting', 'cadence': 'Weekly',
     'desc': 'Nalley Automotive Price Badge Report — Tableau LEI + Demand Signals → Sheet → Gmail draft'},
    {'name': 'hendricks-pb-report', 'category': 'Recurring Reporting', 'cadence': 'Weekly',
     'desc': 'Hendrick Automotive Price Badge Report (same flow as Nalley)'},
    {'name': 'dyer-pb-report', 'category': 'Recurring Reporting', 'cadence': 'Weekly (Thu 8AM)',
     'desc': 'Dyer & Dyer Volvo Price Badge Report — $1000 threshold, LIVE direct send'},
    {'name': 'herb-chambers-pb-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly (1st Wed)',
     'desc': 'Herb Chambers GM monthly Price Badge touchpoint — 6 stores, per-store reports'},
    {'name': 'sonic-monthly-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'Sonic Automotive brand-segmented performance report — ~101 stores, 18 brands'},
    {'name': 'hendrick-monthly-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'Hendrick Automotive brand-segmented report — ~72 stores, 19 brands'},
    {'name': 'sonic-billing', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'Sonic & Hendrick billing reconciliation report'},
    {'name': 'aca-monthly-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'Atlantic Coast Automotive monthly store report — ~72 stores'},
    {'name': 'aca-gm-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'ACA Monthly GM Performance Email'},
    {'name': 'ecarone-vpm-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'eCarOne VPM (Vehicle Performance Metrics) report'},
    {'name': 'ecarone-dr-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'eCarOne DealerRater Review Report'},
    {'name': 'echopark-monthly-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'EchoPark Automotive monthly performance report — 17 used-car stores'},
    {'name': 'asbury-monthly-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'Asbury Group full-umbrella report — 149 stores (Asbury + LHM + Koons + Herb Chambers)'},
    {'name': 'ep-review-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'EchoPark DealerRater review report'},
    {'name': 'hcc4-vdp-report', 'category': 'Recurring Reporting', 'cadence': 'Monthly',
     'desc': 'HCC4 VDP (Vehicle Detail Page) performance report'},
    {'name': 'herb-chambers-employee-update', 'category': 'Recurring Reporting', 'cadence': 'Quarterly',
     'desc': 'Herb Chambers DealerRater employee profile audit — ~24 stores'},

    # On-demand analysis
    {'name': 'book-scan', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Weekly book-of-business health scan — expiring products, upsell signals, trend tracking'},
    {'name': 'investigate-stores', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Unified investigation scan — any store/CCID/group/all'},
    {'name': 'prep', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Pre-call briefing — SF + Tableau + investigation flags + DealerRater in ~90 seconds'},
    {'name': 'auto-research', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Automotive Research Analyst — Growth & Gains deep dive on a dealer or market'},
    {'name': 'dealer-marketshareanalysis', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Dealer market share demand analysis for a ZIP/DMA or dealer radius'},
    {'name': 'dr-employee-update', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Ad-hoc DealerRater employee roster update for any dealer'},
    {'name': 'dark-prospect-report', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': "Shows a dark prospect how their used inventory would perform on Cars.com"},
    {'name': 'jlr-swh-report', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'JLR Southwest Houston Cars.com performance report (now runs on the generalized dealer_market_report.py engine)'},
    {'name': 'asbury-visible-connections-audit', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Visible Connections Audit across multiple groups'},
    {'name': 'marketplace-weekly-connections', 'category': 'On-Demand Analysis', 'cadence': 'Weekly',
     'desc': 'Weekly Marketplace Metrics — Connections Tracker (11-store OBA sheet)'},
    {'name': 'dealer-health-preflight', 'category': 'On-Demand Analysis', 'cadence': 'Ad hoc',
     'desc': 'Dealer Health Dashboard pre-flight check'},

    # Orchestration / utility
    {'name': 'supervisor', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Workflow orchestration with recovery across reporting skills'},
    {'name': 'pb-report-parallel', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Price Badge Report — parallel multi-dealer workflow'},
    {'name': 'tableau-custom-view', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Save a Tableau custom view'},
    {'name': 'validate-csv-schema', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Reusable CSV schema validation skill'},
    {'name': 'recover:tableau-401', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Recovery agent — Tableau 401 / auth failure'},
    {'name': 'recover:gmail-mcp', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Recovery agent — Gmail MCP stale process / tools missing'},
    {'name': 'recover:mfa-timeout', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Recovery agent — JumpCloud MFA timeout / TOTP failure'},
    {'name': 'recover:csv-schema', 'category': 'Orchestration & Utility', 'cadence': 'n/a',
     'desc': 'Recovery agent — CSV schema drift'},
]

# ── Reusable engines behind the skills above (Python scripts, not slash commands) ──
ENGINES = [
    {'name': 'dealer_market_report.py', 'desc': 'Generalized dealer market analysis report engine (LEI + market share + price comparison + CarGurus) — profile-driven, works for any dealer via PROFILES dict or --profile-json'},
    {'name': 'dark_prospect_report.py', 'desc': "Projects a dark prospect's Cars.com performance from their own-site inventory + Demand Signals churner quadrant"},
    {'name': 'generate_market_report.py', 'desc': 'Market Intelligence report generator (Tableau ZIP-level search data → HTML + interactive map)'},
    {'name': 'investigation_triggers.py', 'desc': 'Store investigation trigger detection — powers /investigate-stores and /prep'},
    {'name': 'pb_report.py / pb_dealers.py', 'desc': 'Core Price Badge Report engine shared across Nalley/Hendrick/Dyer/Herb Chambers/parallel workflows'},
    {'name': 'dealer_health.py', 'desc': 'Streamlit dealer health dashboard — SF + admin.cars.com + Claude analysis'},
]

# ── Published GitHub Pages sites ──
PUBLISHED = [
    {'name': 'Market Intelligence Reports', 'url': 'https://jakec86.github.io/market-intelligence-reports/',
     'desc': 'Filterable hub of DMA/make market intelligence reports (this is the live front door for that repo — separate from this menu)'},
    {'name': 'JLR SW Houston Performance Report', 'url': 'https://jakec86.github.io/jlr-swh-performance-report/',
     'desc': 'Standalone published snapshot of the JLR Southwest Houston Cars.com performance report'},
    {'name': 'Mystery Shop Tool', 'url': 'https://jakec86.github.io/mystery-shop/',
     'desc': 'Lead-response scoring app — Pied Piper PSI benchmarks'},
    {'name': 'ACA Market Area Expansion Map', 'url': 'https://jakec86.github.io/aca-mae-map/',
     'desc': 'ACA Market Area Expansion interactive wave map (May 2026)'},
]


def scan_local_reports():
    folders = []
    for entry in sorted(REPORTS_DIR.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIRS:
            continue
        html_files = sorted(entry.rglob('*.html'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not html_files:
            continue
        latest = html_files[0]
        folders.append({
            'name': entry.name,
            'count': len(html_files),
            'latest_path': latest,
            'latest_mtime': datetime.fromtimestamp(latest.stat().st_mtime),
        })
    folders.sort(key=lambda f: f['latest_mtime'], reverse=True)
    return folders


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_html():
    local_reports = scan_local_reports()
    categories = sorted({s['category'] for s in SKILLS})

    skill_cards = ''
    for s in SKILLS:
        skill_cards += f"""
  <div class="card skill-card" data-category="{esc(s['category'])}">
    <div class="card-left">
      <div class="card-title">/{esc(s['name'])}</div>
      <div class="card-meta">{esc(s['desc'])}</div>
      <div class="card-tag">{esc(s['category'])}{f" · {esc(s['cadence'])}" if s['cadence'] != 'n/a' else ''}</div>
    </div>
  </div>"""

    engine_cards = ''.join(
        f"""
  <div class="card">
    <div class="card-left">
      <div class="card-title">{esc(e['name'])}</div>
      <div class="card-meta">{esc(e['desc'])}</div>
    </div>
  </div>""" for e in ENGINES
    )

    published_cards = ''.join(
        f"""
  <a class="card link-card" href="{esc(p['url'])}" target="_blank">
    <div class="card-left">
      <div class="card-title">{esc(p['name'])}</div>
      <div class="card-meta">{esc(p['desc'])}</div>
    </div>
    <span class="card-arrow">&#8599;</span>
  </a>""" for p in PUBLISHED
    )

    local_cards = ''.join(
        f"""
  <a class="card link-card" href="file://{esc(f['latest_path'])}" target="_blank">
    <div class="card-left">
      <div class="card-title">{esc(f['name'])}</div>
      <div class="card-meta">{f['count']} report{'s' if f['count'] != 1 else ''} &middot; latest {f['latest_mtime'].strftime('%b %-d, %Y')}</div>
    </div>
    <span class="card-arrow">&#8594;</span>
  </a>""" for f in local_reports
    )

    generated_str = datetime.now().strftime('%B %-d, %Y')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tools &amp; Reports Menu</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :root {{ --jagger:#370B55; --violet:#8136B2; --vixen:#AB74CF; --lavender:#D9BAEE; --gray:#4D4D4D; --teal:#00A88E; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:#f0ecf5; color:var(--gray); min-height:100vh; }}
  header {{ background:var(--jagger); padding:18px 32px; display:flex; align-items:center; gap:12px; box-shadow:0 2px 12px rgba(55,11,85,.45); }}
  header svg {{ height:26px; }}
  .divider {{ width:1px; height:26px; background:rgba(255,255,255,.25); }}
  .subtitle {{ color:var(--lavender); font-size:12px; font-weight:500; letter-spacing:.8px; text-transform:uppercase; }}
  main {{ max-width:860px; margin:40px auto 64px; padding:0 24px; }}
  h1.page-title {{ font-size:22px; font-weight:700; color:var(--jagger); margin-bottom:4px; }}
  .page-sub {{ font-size:12px; color:#999; margin-bottom:32px; }}
  h2 {{ font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:var(--violet); margin:32px 0 12px; }}
  h2:first-of-type {{ margin-top:0; }}
  .section-note {{ font-size:12px; color:#999; margin-bottom:14px; }}
  .filters {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }}
  .chip {{ padding:4px 12px; border-radius:20px; font-size:11px; font-weight:500; border:1.5px solid var(--lavender); background:#fff; color:var(--violet); cursor:pointer; transition:all .15s; user-select:none; }}
  .chip:hover {{ border-color:var(--vixen); background:#f8f2fd; }}
  .chip.active {{ background:var(--violet); color:#fff; border-color:var(--violet); }}
  .chip.all.active {{ background:var(--jagger); border-color:var(--jagger); }}
  .card {{ background:#fff; border:1px solid #ddd; border-radius:12px; padding:16px 20px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 2px 8px rgba(55,11,85,.08); text-decoration:none; color:inherit; transition:box-shadow .15s, border-color .15s; }}
  .card.hidden {{ display:none; }}
  .link-card:hover {{ box-shadow:0 4px 16px rgba(55,11,85,.16); border-color:var(--vixen); }}
  .card-left {{ display:flex; flex-direction:column; gap:4px; }}
  .card-title {{ font-size:14px; font-weight:600; color:var(--jagger); }}
  .card-meta {{ font-size:12px; color:#666; }}
  .card-tag {{ font-size:10px; color:var(--vixen); font-weight:600; text-transform:uppercase; letter-spacing:.4px; margin-top:2px; }}
  .card-arrow {{ color:var(--vixen); font-size:16px; margin-left:12px; flex-shrink:0; }}
  .count {{ font-size:11px; color:#999; margin-bottom:12px; }}
</style>
</head>
<body>

<header>
  <svg viewBox="0 0 120 30" fill="none" xmlns="http://www.w3.org/2000/svg">
    <text x="0" y="23" font-family="Inter,sans-serif" font-weight="800" font-size="22" fill="#FFFFFF" letter-spacing="-0.5">Cars</text>
    <text x="51" y="23" font-family="Inter,sans-serif" font-weight="800" font-size="22" fill="#AB74CF" letter-spacing="-0.5">.com</text>
  </svg>
  <div class="divider"></div>
  <span class="subtitle">Tools &amp; Reports Menu</span>
</header>

<main>
  <h1 class="page-title">Everything We've Built</h1>
  <div class="page-sub">Personal reference — generated {generated_str} by build_tools_menu.py. Not published; local file only.</div>

  <h2>Skills &amp; Workflows</h2>
  <div class="count">{len(SKILLS)} skills</div>
  <div class="filters" id="skillFilters"></div>
  <div id="skill-no-results" style="display:none; font-size:13px; color:#999; padding:12px 0;">No skills match the selected filter.</div>
  <div id="skillCards">{skill_cards}
  </div>

  <h2>Reusable Engines</h2>
  <div class="section-note">Python scripts behind the skills above — edit these directly for cross-cutting fixes.</div>
  {engine_cards}

  <h2>Published Report Sites</h2>
  <div class="section-note">Live on GitHub Pages.</div>
  {published_cards}

  <h2>Local Report Folders</h2>
  <div class="section-note">~/Documents/Reports/&lt;folder&gt; — {len(local_reports)} folders with generated HTML, sorted by most recent.</div>
  {local_cards}
</main>

<script>
(function() {{
  const cards = Array.from(document.querySelectorAll('.skill-card'));
  const filtersEl = document.getElementById('skillFilters');
  const noResults = document.getElementById('skill-no-results');
  const categories = [...new Set(cards.map(c => c.dataset.category))].sort();
  let active = null;

  const allChip = document.createElement('span');
  allChip.className = 'chip all active';
  allChip.textContent = 'All categories';
  allChip.addEventListener('click', () => {{ active = null; applyFilter(); }});
  filtersEl.appendChild(allChip);

  categories.forEach(cat => {{
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = cat;
    chip.dataset.value = cat;
    chip.addEventListener('click', () => {{ active = cat; applyFilter(); }});
    filtersEl.appendChild(chip);
  }});

  function applyFilter() {{
    let visible = 0;
    cards.forEach(card => {{
      const show = !active || card.dataset.category === active;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    noResults.style.display = visible === 0 ? 'block' : 'none';
    filtersEl.querySelectorAll('.chip').forEach(chip => {{
      const isAll = chip.classList.contains('all');
      chip.classList.toggle('active', isAll ? active === null : chip.dataset.value === active);
    }});
  }}
}})();
</script>
</body>
</html>
"""
    return html


if __name__ == '__main__':
    OUTPUT_PATH.write_text(build_html(), encoding='utf-8')
    print(f"✓ Wrote {OUTPUT_PATH}")
