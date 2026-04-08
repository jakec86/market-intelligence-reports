#!/usr/bin/env python3
"""
Auto-generate index.html by scanning report directories for market intelligence HTML files.
Parses DMA, makes, date, and data range from filenames and report content.

Usage:
    python3 build_index.py              # scan current directory
    python3 build_index.py /path/to/reports
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

REPORTS_BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


def discover_reports(base):
    """Find all market_intelligence_*.html files in subdirectories."""
    reports = []
    for html_file in sorted(base.glob("*/market_intelligence_*.html")):
        info = parse_report(html_file, base)
        if info:
            reports.append(info)
    # Sort newest first
    reports.sort(key=lambda r: r["sort_date"], reverse=True)
    return reports


def parse_report(html_path, base):
    """Extract metadata from a report filename and HTML content."""
    fname = html_path.stem  # e.g. market_intelligence_Mobile_Pensacola_Ft_Walt_Honda_04.08.26
    rel_path = html_path.relative_to(base)

    # Extract date (last segment: MM.DD.YY)
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{2})$', fname)
    if not date_match:
        return None
    mm, dd, yy = date_match.groups()
    date_str = f"{MONTH_NAMES.get(mm, mm)} {int(dd)}, 20{yy}"
    sort_date = f"20{yy}-{mm}-{dd}"

    # Remove prefix and date to isolate DMA + makes
    middle = fname.replace("market_intelligence_", "").replace(f"_{mm}.{dd}.{yy}", "")

    # Folder name is the DMA slug
    folder_slug = html_path.parent.name

    # Makes = whatever is after the folder slug in the middle
    if middle.startswith(folder_slug):
        makes_part = middle[len(folder_slug):]
        makes_part = makes_part.lstrip("_")
    else:
        makes_part = ""

    makes = [m for m in makes_part.split("_") if m] if makes_part else []

    # Reverse-slugify DMA: underscores → spaces, add hyphens where common
    dma_display = folder_slug.replace("_", " ")
    # Try to extract a cleaner DMA name from the HTML
    dma_clean = dma_display

    # Read HTML to extract data_date from the %%DATA_DATE%% injection
    data_date = ""
    try:
        content = html_path.read_text(encoding="utf-8")
        m = re.search(r'Data as of ([^<"]+)', content)
        if m:
            data_date = m.group(1).strip()
        # Also try to get a better DMA name from the report title
        t = re.search(r'<span id="logo-subtitle">([^<]+)</span>', content)
        if t:
            title_raw = t.group(1)
            # "Mobile-Pensacola (Ft Walt) Market Intelligence | Honda"
            dma_clean = title_raw.split(" Market Intelligence")[0].strip()
    except Exception:
        pass

    # Build display title
    makes_label = " · ".join(makes) if makes else "All Makes"
    title = f"{dma_clean} · {makes_label}" if makes else dma_clean

    # data-dma for filtering: normalize to hyphenated short form
    dma_filter = re.sub(r'\s*\([^)]*\)\s*', '', dma_clean).strip()

    return {
        "href": str(rel_path),
        "title": title,
        "date_str": date_str,
        "data_date": data_date,
        "dma": dma_filter,
        "make": makes[0] if makes else "All",
        "sort_date": sort_date,
    }


def build_card_html(report):
    """Generate one report card HTML block."""
    meta = report["date_str"]
    if report["data_date"]:
        meta += f" · {report['data_date']}"
    return f"""  <a class="report-card" href="{report['href']}"
     data-dma="{report['dma']}" data-make="{report['make']}">
    <div class="card-left">
      <div class="card-title">{report['title']}</div>
      <div class="card-meta">{meta}</div>
    </div>
    <span class="card-arrow">\u2192</span>
  </a>
"""


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Intelligence Reports</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :root { --jagger:#370B55; --violet:#8136B2; --vixen:#AB74CF; --lavender:#D9BAEE; --gray:#4D4D4D; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',sans-serif; background:#f0ecf5; color:var(--gray); min-height:100vh; }

  header {
    background:var(--jagger); padding:18px 32px;
    display:flex; align-items:center; gap:12px;
    box-shadow:0 2px 12px rgba(55,11,85,.45);
  }
  header svg { height:26px; }
  .divider { width:1px; height:26px; background:rgba(255,255,255,.25); }
  .subtitle { color:var(--lavender); font-size:12px; font-weight:500; letter-spacing:.8px; text-transform:uppercase; }

  main { max-width:760px; margin:48px auto; padding:0 24px; }
  h2 { font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:var(--violet); margin-bottom:12px; }

  .filters { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px; }
  .filter-group { display:flex; gap:6px; flex-wrap:wrap; }
  .chip {
    padding:4px 12px; border-radius:20px; font-size:11px; font-weight:500;
    border:1.5px solid var(--lavender); background:#fff; color:var(--violet);
    cursor:pointer; transition:all .15s; user-select:none;
  }
  .chip:hover { border-color:var(--vixen); background:#f8f2fd; }
  .chip.active { background:var(--violet); color:#fff; border-color:var(--violet); }
  .chip.all { border-color:#ddd; color:var(--gray); }
  .chip.all.active { background:var(--jagger); border-color:var(--jagger); color:#fff; }
  .filter-sep { width:1px; background:#ddd; align-self:stretch; margin:2px 0; }
  #no-results { display:none; font-size:13px; color:#999; padding:20px 0; }

  .report-card {
    background:#fff; border:1px solid #ddd; border-radius:12px;
    padding:18px 20px; margin-bottom:12px;
    display:flex; align-items:center; justify-content:space-between;
    box-shadow:0 2px 8px rgba(55,11,85,.08);
    text-decoration:none; color:inherit;
    transition:box-shadow .15s, border-color .15s;
  }
  .report-card:hover { box-shadow:0 4px 16px rgba(55,11,85,.16); border-color:var(--vixen); }
  .report-card.hidden { display:none; }
  .card-left { display:flex; flex-direction:column; gap:4px; }
  .card-title { font-size:14px; font-weight:600; color:var(--jagger); }
  .card-meta { font-size:11px; color:#999; }
  .card-arrow { color:var(--vixen); font-size:18px; }
  .count { font-size:11px; color:#999; margin-bottom:16px; }
</style>
</head>
<body>

<header>
  <svg viewBox="0 0 120 30" fill="none" xmlns="http://www.w3.org/2000/svg">
    <text x="0" y="23" font-family="Inter,sans-serif" font-weight="800" font-size="22" fill="#FFFFFF" letter-spacing="-0.5">Cars</text>
    <text x="51" y="23" font-family="Inter,sans-serif" font-weight="800" font-size="22" fill="#AB74CF" letter-spacing="-0.5">.com</text>
  </svg>
  <div class="divider"></div>
  <span class="subtitle">Market Intelligence Reports</span>
</header>

<main>
  <h2>Available Reports</h2>
  <div class="count">%%COUNT%% reports</div>

  <div class="filters" id="filters"></div>
  <div id="no-results">No reports match the selected filters.</div>

%%CARDS%%
</main>

<script>
(function() {
  const cards = Array.from(document.querySelectorAll('.report-card'));
  const filtersEl = document.getElementById('filters');
  const noResults = document.getElementById('no-results');

  const dmas  = [...new Set(cards.map(c => c.dataset.dma).filter(Boolean))].sort();
  const makes = [...new Set(cards.map(c => c.dataset.make).filter(Boolean))].sort();

  let activeDma  = null;
  let activeMake = null;

  function buildChips(values, key, getActive, setActive) {
    const group = document.createElement('div');
    group.className = 'filter-group';

    const allChip = document.createElement('span');
    allChip.className = 'chip all active';
    allChip.textContent = 'All ' + (key === 'dma' ? 'DMAs' : 'Makes');
    allChip.addEventListener('click', () => { setActive(null); applyFilters(); });
    group.appendChild(allChip);

    values.forEach(v => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = v;
      chip.dataset.value = v;
      chip.addEventListener('click', () => { setActive(v); applyFilters(); });
      group.appendChild(chip);
    });
    return group;
  }

  function updateChips(group, active) {
    group.querySelectorAll('.chip').forEach(chip => {
      const isAll = chip.classList.contains('all');
      chip.classList.toggle('active', isAll ? active === null : chip.dataset.value === active);
    });
  }

  function applyFilters() {
    let visible = 0;
    cards.forEach(card => {
      const matchDma  = !activeDma  || card.dataset.dma  === activeDma;
      const matchMake = !activeMake || card.dataset.make === activeMake;
      const show = matchDma && matchMake;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    });
    noResults.style.display = visible === 0 ? 'block' : 'none';
    updateChips(dmaGroup,  activeDma);
    updateChips(makeGroup, activeMake);
  }

  const dmaGroup  = buildChips(dmas,  'dma',  () => activeDma,  v => activeDma  = v);
  const makeGroup = buildChips(makes, 'make', () => activeMake, v => activeMake = v);

  if (dmas.length > 1)  { filtersEl.appendChild(dmaGroup);  filtersEl.appendChild(Object.assign(document.createElement('div'), {className:'filter-sep'})); }
  if (makes.length > 0) filtersEl.appendChild(makeGroup);

  if (cards.length <= 1) filtersEl.style.display = 'none';
})();
</script>
</body>
</html>
"""


def main():
    reports = discover_reports(REPORTS_BASE)
    if not reports:
        print("No reports found.")
        return

    cards_html = "\n".join(build_card_html(r) for r in reports)
    html = INDEX_TEMPLATE.replace("%%CARDS%%", cards_html)
    html = html.replace("%%COUNT%%", str(len(reports)))

    out = REPORTS_BASE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✓ index.html rebuilt with {len(reports)} reports:")
    for r in reports:
        print(f"  • {r['title']} ({r['date_str']})")


if __name__ == "__main__":
    main()
