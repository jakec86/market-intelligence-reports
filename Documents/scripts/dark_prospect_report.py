#!/usr/bin/env python3
"""
dark_prospect_report.py — "Your inventory on the Churners graph"

Repeatable prospecting tool: takes a DARK prospect's scraped used inventory +
admin.cars.com Demand Signals data, plots each vehicle onto the DFW demand
quadrant (Churner / Lot Sitter / Rarity / Niche), and projects how that
inventory WOULD perform on Cars.com today (monthly VDPs / connections /
incremental gross), benchmarked against a blend of:
  (a) the prospect's own prior Cars.com history,
  (b) an active comparable store (per-vehicle monthly rates), and
  (c) current DMA market demand.

Output: a standalone, brand-correct HTML report (Chart.js quadrant scatter +
projection tables + revenue range + full assumptions/disclaimers).

First case: Park Place Mercedes-Benz (Dallas / Fort Worth / Arlington), DFW.
Reusable: swap the CONFIG block (or load a per-prospect YAML) and re-run.
"""
import io, csv, json, statistics, html, datetime
from pathlib import Path
from collections import defaultdict, Counter

# ----------------------------------------------------------------------------
# CONFIG  (per-prospect — swap this block for a new prospect)
# ----------------------------------------------------------------------------
HOME = Path.home()
TABLEAU = HOME / "Documents" / "Tableau"
PPDIR = HOME / "Documents" / "Reports" / "ParkPlace"

CONFIG = {
    "prospect_name": "Park Place Mercedes-Benz",
    "prospect_type": "winback",          # winback | greenfield
    "dma": "Dallas-Ft. Worth",
    "primary_make": "Mercedes-Benz",
    "report_date": "2026-06-12",
    "inventory_json": PPDIR / "inventory" / "parkplace_MB_stores_2026-06-12.json",
    "market_comparison_csv": TABLEAU / "Market Comparison.csv",
    "demand_quadrants_csv": TABLEAU / "Demand Quadrants (2).csv",   # broad all-make churner view (covers trade-ins)

    # Blended benchmark legs — monthly per-vehicle rates derived below.
    # self = prospect's own FPL-period Cars.com history (May 2025, documented)
    # comp = active comparable store (MB of Plano) current monthly KPIs
    # market = current DMA make-level demand on Cars.com
    # All legs on a consistent ALL-STOCK-TYPES basis (rates = monthly VDPs/connections per listed vehicle, all stock).
    "legs": {
        "self":   {"label": "Park Place 2025 (own Cars.com history)", "inventory": 230, "vdps": 5198, "connections": 50,
                   "note": "Their May-2025 Cars.com listings (all stock types)"},
        "comp":   {"label": "MB of Plano (active comparable, current)", "inventory": 2267, "vdps": 18701, "connections": 531,
                   "note": "Current Cars.com listings (all stock types)"},
        "market": {"label": "DFW Mercedes-Benz market on Cars.com (current)", "inventory": 4476, "vdps": 26441, "connections": 589,
                   "note": "All DFW Mercedes-Benz listings (all stock types)"},
    },
    # New+used (all-stock) projection: rates must be all-stock too. Self is used-only → dropped from the
    # rate blend (kept as a used proof point in the historical section). Rate = active comparable + market.
    "weights": {"self": 0.00, "comp": 0.60, "market": 0.40},
    # current NEW inventory per MB store (scraped 2026-06-12 from each store's /new-inventory feed)
    "new_by_store": {"Dallas": 477, "Fort Worth": 206, "Arlington": 154},

    # consolidated historical Cars.com performance (when last active) — documented; omit for greenfield prospects
    "historical": {
        "period": "May 2025 — their last active month on Cars.com (FPL contract)",
        "stores": [
            {"store": "Dallas",     "inventory": 129, "vdps": 2078, "connections": 24, "leads": 9, "badge": 0.36},
            {"store": "Fort Worth", "inventory": 57,  "vdps": 1897, "connections": 18, "leads": 7, "badge": 0.16},
            {"store": "Arlington",  "inventory": 44,  "vdps": 1223, "connections": 8,  "leads": 2, "badge": 0.20},
        ],
        "link": "park_place_pitch_v2.html",
        "link_label": "Full Park Place market & historical deck (Polk share, 24-mo trend, competitive set)",
    },

    # quadrant per-VIN multipliers (normalized so inventory-weighted mean == 1.0)
    "quad_mult": {"Churner": 1.30, "Niche": 1.10, "Rarity": 0.85, "Lot Sitter": 0.70, "Unmatched": 1.00},

    # revenue framing — store is DARK so projected connections are net-new (incremental)
    "revenue": {"close_rate": 0.08, "close_range": [0.06, 0.10],          # LEAD close rate (phone/email/chat)
                "click_close_rate": 0.01, "click_close_range": [0.005, 0.015],  # conversion on non-lead connections (VDP deep-link clicks, website transfers)
                "gpu": 4500, "gpu_range": [4000, 5000],
                # Leads (phone+email+chat) / total connections. Park Place's OWN actual,
                # pooled across the 3 MB stores over their paid-active window (May–Sep 2025):
                # 62 leads / 269 connections = 0.23. Robust across windows (May–Jul .222, May–Aug .236).
                # Cross-validated by active comparable MB Plano (Mar–May 2026) = 0.217.
                # NOTE: ~60% of connections are VDP deep-link clicks; gross is BLENDED — leads close
                # at close_rate, the click/transfer remainder converts at click_close_rate.
                "lead_share_of_conn": 0.23},

    "out_html": PPDIR / "parkplace_inventory_projection_2026-06-12.html",
    "out_slide": PPDIR / "parkplace_inventory_projection_SLIDE_2026-06-12.html",
}

PURPLE, TEAL, DARK = "#6B2D8B", "#00A88E", "#2A2A33"
QUAD_COLORS = {"Churner": TEAL, "Niche": "#8E44AD", "Rarity": "#E08E0B", "Lot Sitter": "#C0392B", "Unmatched": "#9AA0A6"}

# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------
def load_csv(path):
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    first = text.split("\n", 1)[0]
    delim = "\t" if first.count("\t") >= first.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))

def num(x):
    try: return float(str(x).replace(",", "").replace("%", "").replace("$", "").strip() or 0)
    except: return 0.0

# ----------------------------------------------------------------------------
# Mercedes nameplate normalization (collapse trims to nameplate)
# ----------------------------------------------------------------------------
MB_CLASSES = ["GLE", "GLC", "GLB", "GLA", "GLS", "GLK", "CLA", "CLE", "CLS",
              "EQB", "EQE", "EQS", "EQA", "SL", "GT", "AMG GT", "Sprinter", "Metris", "Maybach"]

def nameplate(make, model):
    """Collapse a model string to its market nameplate for joining."""
    m = (model or "").strip()
    mk = (make or "").strip().upper()
    if mk in ("MERCEDES-BENZ", "MERCEDES"):
        u = m.upper().replace("AMG", "").replace("MAYBACH", "").strip()
        # single-letter class + number, e.g. "C 300" / "E 350" / "S 580" -> "C-CLASS"
        toks = u.split()
        if u.endswith("-CLASS"):
            return u
        if toks and toks[0] in ("C", "E", "S", "A", "B", "G") and (len(toks) == 1 or toks[1][:1].isdigit()):
            return toks[0] + "-CLASS"
        for cls in sorted(MB_CLASSES, key=len, reverse=True):
            if u.startswith(cls.upper()):
                return cls.upper()
        return toks[0] if toks else u
    # other makes: first 1-2 tokens (e.g. "Sierra 1500"->"SIERRA", "Range Rover Sport"->"RANGE ROVER SPORT")
    return m.strip().upper()

# ----------------------------------------------------------------------------
# Build market lookup + quadrant
# ----------------------------------------------------------------------------
def build_market(mc_rows, primary_make):
    """Aggregate Market Comparison to (make, nameplate); compute quadrant via median splits."""
    agg = defaultdict(lambda: {"veh": 0.0, "vdp": 0.0, "conn": 0.0})
    for r in mc_rows:
        stock = (r.get("Stock type") or "").strip().lower()
        if stock == "new":
            continue
        mk = (r.get("Make") or "").strip()
        np_ = nameplate(mk, r.get("Model"))
        key = (mk.upper(), np_)
        a = agg[key]
        a["veh"]  += num(r.get("Market vehicles"))
        a["vdp"]  += num(r.get("Market VDPs"))
        a["conn"] += num(r.get("Market connections"))
    rows = [{"make": k[0], "nameplate": k[1], **v} for k, v in agg.items() if v["veh"] > 0]
    med_veh = statistics.median([x["veh"] for x in rows])
    med_vdp = statistics.median([x["vdp"] for x in rows])
    lookup = {}
    for x in rows:
        hi_sup = x["veh"] >= med_veh
        hi_dem = x["vdp"] >= med_vdp
        x["quadrant"] = ("Churner" if (hi_sup and hi_dem) else
                         "Niche" if (hi_dem and not hi_sup) else
                         "Lot Sitter" if (hi_sup and not hi_dem) else "Rarity")
        lookup[(x["make"], x["nameplate"])] = x
    return lookup, med_veh, med_vdp, rows

MULTIWORD_MAKES = ["Land Rover", "Mercedes-Benz", "Alfa Romeo", "Aston Martin"]
def split_make_model(s):
    s = (s or "").strip()
    for m in MULTIWORD_MAKES:
        if s.upper().startswith(m.upper() + " "):
            return m, s[len(m):].strip()
    parts = s.split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")

def build_dq_lookup(dq_rows):
    """Demand Quadrants view = admin.cars' broad all-make churner classification (covers trade-ins).
    Keyed by (MAKE, nameplate); honors the report's own 'Dynamic quadrant' label."""
    out = {}
    for r in dq_rows:
        make, model = split_make_model(r.get("Make model"))
        q = (r.get("Dynamic quadrant") or "").strip().rstrip("s")  # "Churners" -> "Churner"
        key = (make.strip().upper(), nameplate(make, model))
        out[key] = {"make": make, "nameplate": nameplate(make, model),
                    "veh": num(r.get("Inventory")), "vdp": num(r.get("VDP imps")),
                    "quadrant": q or "Churner", "source": "DQ"}
    return out

def classify_vehicle(v, lookup, dq_lookup):
    key = (v["make"].strip().upper(), nameplate(v["make"], v["model"]))
    hit = lookup.get(key)
    if hit:
        return hit["quadrant"], hit          # Market Comparison (full 4-quadrant, used)
    dq = dq_lookup.get(key)
    if dq:
        return dq["quadrant"], dq             # Demand Quadrants fallback (covers trade-ins)
    return ("Unmatched", None)

# ----------------------------------------------------------------------------
# Benchmark blend + projection
# ----------------------------------------------------------------------------
def per_veh_rates(legs, weights):
    out = {}
    for name, L in legs.items():
        inv = L["inventory"] or 1
        out[name] = {"vdp": L["vdps"]/inv, "conn": L["connections"]/inv}
    blend_vdp = sum(weights[n]*out[n]["vdp"] for n in weights)
    blend_conn = sum(weights[n]*out[n]["conn"] for n in weights)
    return out, blend_vdp, blend_conn

QUAD_ORDER = {"Churner": 0, "Niche": 1, "Lot Sitter": 2, "Rarity": 3, "Unmatched": 4}
def build_chips(vehicles):
    """One entry per distinct nameplate in inventory, with its quadrant, count, and market coords."""
    agg = {}
    for v in vehicles:
        if v.get("_mkt"):
            lbl = f'{v["_mkt"]["make"].title()} {v["_mkt"]["nameplate"].title()}'
            x, y = v["_mkt"]["veh"], v["_mkt"]["vdp"]
        else:
            lbl = f'{(v.get("make") or "").title()} {(v.get("model") or "").title()}'.strip() or "Unknown"
            x, y = None, None
        a = agg.setdefault(lbl, {"label": lbl, "count": 0, "quad": v["quadrant"], "x": x, "y": y, "pvdp": 0.0, "pconn": 0.0})
        a["count"] += 1
        a["pvdp"] += v.get("proj_vdp", 0); a["pconn"] += v.get("proj_conn", 0)
    chips = list(agg.values())
    for c in chips:
        c["color"] = QUAD_COLORS[c["quad"]]
    chips.sort(key=lambda c: (QUAD_ORDER.get(c["quad"], 9), -c["count"]))
    return chips

def project(vehicles, lookup, dq_lookup, base_vdp, base_conn, quad_mult):
    # classify
    for v in vehicles:
        q, hit = classify_vehicle(v, lookup, dq_lookup)
        v["quadrant"] = q
        v["_mkt"] = hit
        v["_rawmult"] = quad_mult.get(q, 1.0)
    mean_mult = sum(v["_rawmult"] for v in vehicles) / len(vehicles)
    for v in vehicles:
        v["mult"] = v["_rawmult"] / mean_mult          # normalize -> redistribute, never inflate
        v["proj_vdp"] = base_vdp * v["mult"]
        v["proj_conn"] = base_conn * v["mult"]
    return vehicles

# ----------------------------------------------------------------------------
# HTML report
# ----------------------------------------------------------------------------
def esc(s): return html.escape(str(s))

def build_html(cfg, vehicles, market_rows, med_veh, med_vdp, rates, blend_vdp, blend_conn):
    n = len(vehicles)
    by_store = Counter(v.get("store", "?") for v in vehicles)
    by_quad = Counter(v["quadrant"] for v in vehicles)
    proj_vdp = sum(v["proj_vdp"] for v in vehicles)        # used-only (drives the used churner calculator)
    proj_conn = sum(v["proj_conn"] for v in vehicles)
    lead_share = cfg["revenue"]["lead_share_of_conn"]   # Leads = phone+email+chat subset of total connections
    proj_leads = proj_conn * lead_share                 # used-lot leads (drives the interactive calculator)
    churner_pct = 100*by_quad["Churner"]/n
    matched = sum(1 for v in vehicles if v["quadrant"] != "Unmatched")

    # new+used totals — projection is on the full (all-stock) inventory at the all-stock blended rate
    new_by_store = cfg.get("new_by_store", {})
    new_total = sum(new_by_store.values())
    used_total = n
    grand_total = used_total + new_total
    proj_vdp_total = grand_total * blend_vdp
    proj_conn_total = grand_total * blend_conn
    proj_leads_total = proj_conn_total * lead_share     # full-inventory leads — matches the headline connections KPI

    # revenue range — BLENDED: close leads (P+E+C) at the lead-close rate, plus a small
    # conversion on the non-lead connections (VDP deep-link clicks, website transfers).
    # Store is dark -> all incremental.
    rv = cfg["revenue"]
    clicks_total = proj_conn_total - proj_leads_total
    def gross(close, click, gpu): return (proj_leads_total*close + clicks_total*click) * gpu
    lo  = gross(rv["close_range"][0], rv["click_close_range"][0], rv["gpu_range"][0])
    mid = gross(rv["close_rate"], rv["click_close_rate"], rv["gpu"])
    hi  = gross(rv["close_range"][1], rv["click_close_range"][1], rv["gpu_range"][1])

    # scatter points: one per (make, nameplate) present in PP inventory & matched
    pts = defaultdict(lambda: {"count": 0})
    for v in vehicles:
        if v["_mkt"]:
            k = (v["_mkt"]["make"], v["_mkt"]["nameplate"])
            p = pts[k]
            p["count"] += 1
            p["x"] = v["_mkt"]["veh"]; p["y"] = v["_mkt"]["vdp"]; p["quad"] = v["_mkt"]["quadrant"]
            p["label"] = f'{v["_mkt"]["make"].title()} {v["_mkt"]["nameplate"].title()}'
    scatter = [{"x": p["x"], "y": p["y"], "r": min(28, 6+p["count"]*1.4), "label": p["label"],
                "count": p["count"], "quad": p["quad"], "color": QUAD_COLORS[p["quad"]]}
               for p in pts.values()]
    chips = build_chips(vehicles)

    # quadrant mix table rows
    quad_order = ["Churner", "Niche", "Lot Sitter", "Rarity", "Unmatched"]
    quad_rows = "".join(
        f'<tr><td><span class="dot" style="background:{QUAD_COLORS[q]}"></span>{q}</td>'
        f'<td class="num">{by_quad.get(q,0)}</td><td class="num">{100*by_quad.get(q,0)/n:.0f}%</td>'
        f'<td>{ {"Churner":"Proven fast-movers — high supply &amp; high demand","Niche":"Strong demand, thin supply — pricing power","Lot Sitter":"Oversupplied, softer demand","Rarity":"Thin on both sides","Unmatched":"Trade-in make/model not in DFW demand set"}[q] }</td></tr>'
        for q in quad_order if by_quad.get(q,0) > 0)

    # per-store projection table (new + used; all-stock rate applied to the full per-store count)
    store_rows = ""
    for store in ["Dallas", "Fort Worth", "Arlington"]:
        used_n = sum(1 for v in vehicles if v.get("store") == store)
        new_n = new_by_store.get(store, 0)
        tot = used_n + new_n
        if not tot: continue
        svd = tot * blend_vdp; sc = tot * blend_conn
        store_rows += (f'<tr><td>{store}</td><td class="num">{new_n:,}</td><td class="num">{used_n:,}</td>'
                       f'<td class="num">{tot:,}</td>'
                       f'<td class="num">{svd:,.0f}</td><td class="num">{sc:,.0f}</td>'
                       f'<td class="num">{sc*lead_share:,.0f}</td></tr>')

    # benchmark transparency rows
    leg_rows = ""
    for name in ["self", "comp", "market"]:
        L = cfg["legs"][name]; w = cfg["weights"][name]; r = rates[name]
        cav = L.get("note", "")
        leg_rows += (f'<tr><td>{esc(L["label"])}</td><td class="num">{w*100:.0f}%</td>'
                     f'<td class="num">{r["vdp"]:.1f}</td><td class="num">{r["conn"]:.3f}</td>'
                     f'<td class="small">{esc(cav)}</td></tr>')

    # top churner nameplates the prospect already stocks
    chn_np = Counter()
    for v in vehicles:
        if v["quadrant"] == "Churner" and v["_mkt"]:
            chn_np[f'{v["_mkt"]["make"].title()} {v["_mkt"]["nameplate"].title()}'] += 1
    chn_list = "".join(f"<li><b>{esc(k)}</b> — {c} in stock</li>" for k, c in chn_np.most_common(8))

    date_str = datetime.datetime.strptime(cfg["report_date"], "%Y-%m-%d").strftime("%B %d, %Y")

    # consolidated historical performance section (only if provided)
    hist = cfg.get("historical")
    hist_html = ""
    if hist:
        hs = hist["stores"]
        h_inv = sum(s["inventory"] for s in hs); h_vdp = sum(s["vdps"] for s in hs)
        h_conn = sum(s["connections"] for s in hs); h_leads = sum(s.get("leads", 0) for s in hs)
        hrows = "".join(
            f'<tr><td>{esc(s["store"])}</td><td class="num">{s["inventory"]}</td><td class="num">{s["vdps"]:,}</td>'
            f'<td class="num">{s["connections"]}</td><td class="num">{s.get("leads","&mdash;")}</td><td class="num">{s["badge"]*100:.0f}%</td></tr>' for s in hs)
        hist_html = f"""<div class="section">
  <h2>They've already proven it on Cars.com — Park Place's own results</h2>
  <p style="font-size:13px;margin:0 0 12px">{esc(hist["period"])}, the <b>same inventory</b> generated this on Cars.com:</p>
  <div class="hero">
    <div class="kpi"><div class="v">{h_inv}</div><div class="l">Used vehicles listed<br>(consolidated, 3 stores)</div></div>
    <div class="kpi"><div class="v">{h_vdp:,}</div><div class="l">VDPs / month</div></div>
    <div class="kpi"><div class="v">{h_leads}</div><div class="l">Direct leads / month<br>(phone · email · chat)</div></div>
    <div class="kpi"><div class="v">{h_conn}</div><div class="l">Total connections / month</div></div>
  </div>
  <table class="tbl-even" style="margin-top:14px"><thead><tr><th>Store</th><th class="num">Inventory</th><th class="num">VDPs/mo</th><th class="num">Connections/mo</th><th class="num">Leads/mo</th><th class="num">Price-badge rate</th></tr></thead>
  <tbody>{hrows}
  <tr style="font-weight:700;background:#faf7fc"><td>Total</td><td class="num">{h_inv}</td><td class="num">{h_vdp:,}</td><td class="num">{h_conn}</td><td class="num">{h_leads}</td><td class="num">&mdash;</td></tr></tbody></table>
  <p class="note" style="margin-top:14px"><b>Proof the demand is real</b> — same stores, same listings. Even under-merchandised (price-badge rates as low as {min(s["badge"] for s in hs)*100:.0f}%), the used lot pulled <b>{h_leads} direct leads/month</b> and {h_vdp:,} VDPs (the balance of connections were map views, website and walk-in activity). Today's projection is benchmarked against an active comparable and current DFW market demand — not this thin tail.</p>
</div>
"""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(cfg['prospect_name'])} — Your Inventory on Cars.com</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
*{{box-sizing:border-box}} body{{font-family:'Poppins',sans-serif;margin:0;color:{DARK};background:#f4f4f7;line-height:1.5}}
.wrap{{max-width:1080px;margin:0 auto;background:#fff;box-shadow:0 1px 14px rgba(0,0,0,.08)}}
header{{background:{PURPLE};color:#fff;padding:30px 40px}}
header h1{{margin:0 0 4px;font-size:25px;font-weight:600}} header p{{margin:0;opacity:.85;font-size:14px}}
.section{{padding:26px 40px;border-bottom:1px solid #eee}}
h2{{color:{PURPLE};font-size:18px;margin:0 0 14px}}
.hero{{display:flex;gap:14px;flex-wrap:wrap}}
.kpi{{flex:1;min-width:160px;background:#fff;border:1px solid #e7e7ee;border-top:4px solid {TEAL};border-radius:8px;padding:16px}}
.kpi .v{{font-size:27px;font-weight:700;color:{PURPLE}}} .kpi .l{{font-size:12px;color:#666;margin-top:3px}}
table{{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}}
th{{background:{PURPLE};color:#fff;text-align:left;padding:8px 12px;font-weight:600;font-size:12.5px}}
th.num,td.num{{text-align:center;font-variant-numeric:tabular-nums}}
td{{padding:8px 12px;border-bottom:1px solid #eee;overflow:hidden;text-overflow:ellipsis}}
/* even numeric columns: label col fixed, the rest split evenly */
.tbl-even th:first-child,.tbl-even td:first-child{{width:28%}}
.tbl-q th:nth-child(1){{width:18%}} .tbl-q th:nth-child(2),.tbl-q th:nth-child(3){{width:13%}}
.tbl-bench th:nth-child(1){{width:30%}} .tbl-bench th:nth-child(2){{width:11%}} .tbl-bench th:nth-child(3),.tbl-bench th:nth-child(4){{width:14%}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:middle}}
.small{{font-size:11px;color:#777}} .note{{background:#f0faf7;border-left:4px solid {TEAL};padding:12px 16px;font-size:13px;border-radius:4px}}
.rev{{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px}}
.rev .box{{flex:1;min-width:150px;text-align:center;border:1px solid #e7e7ee;border-radius:8px;padding:14px}}
.rev .box .v{{font-size:22px;font-weight:700}} .rev .mid{{border-color:{TEAL};background:#f0faf7}}
ul{{margin:8px 0 0 0;padding-left:20px;font-size:13px}} li{{margin:3px 0}}
.disc{{font-size:11px;color:#888;line-height:1.6}}
.chartbox{{position:relative;height:440px}}
.chips-legend{{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}}
.legend-btn{{cursor:pointer;border:1px solid #ddd;background:#fff;border-radius:20px;padding:4px 11px;font:600 11px Poppins,Arial;color:#444;display:flex;align-items:center;gap:6px}}
.legend-btn i{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.legend-btn.on{{border-color:var(--c);box-shadow:0 0 0 2px color-mix(in srgb,var(--c) 28%,transparent)}}
.chips{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:10px}}
.chip{{cursor:pointer;border:1.5px solid var(--c);color:var(--c);background:#fff;border-radius:20px;padding:4px 11px;font:600 11.5px Poppins,Arial;transition:background .12s,color .12s}}
.chip span{{opacity:.65;font-weight:500}}
.chip:hover{{background:color-mix(in srgb,var(--c) 12%,#fff)}}
.chip.sel{{background:var(--c);color:#fff}} .chip.sel span{{opacity:.85}}
.chip-detail{{font-size:12px;color:#555;background:#faf7fc;border-radius:6px;padding:13px 15px;min-height:18px}}
.chip-detail .sw{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:7px;vertical-align:middle}}
.chip-detail .tlabel{{font-weight:700;color:{PURPLE};font-size:12.5px;margin-bottom:9px}}
.chip-detail .trow{{display:flex;flex-wrap:wrap;gap:26px}}
.chip-detail .trow>div{{font-size:11px;color:#777}}
.chip-detail .trow>div span{{display:block;font-size:20px;font-weight:800;color:{TEAL};line-height:1.15}}
.chip-detail .thint{{margin-top:9px;font-size:11px;color:#999}}
.chip-detail #clearSel{{display:inline-block;margin-top:10px;font-size:11px;font-weight:600;color:#b52929;cursor:pointer;text-decoration:underline}}
</style></head><body><div class="wrap">

<header>
  <h1>{esc(cfg['prospect_name'])} — How Your Inventory Would Perform on Cars.com</h1>
  <p>{esc(cfg['dma'])} &nbsp;•&nbsp; Modeled from live inventory ({grand_total:,} vehicles — {new_total:,} new + {used_total} used, 3 stores) &nbsp;•&nbsp; {date_str}</p>
</header>

<div class="section">
  <div class="hero">
    <div class="kpi"><div class="v">{grand_total:,}</div><div class="l">Total vehicles (new + used)<br>{new_total:,} new · {used_total} used</div></div>
    <div class="kpi"><div class="v">{proj_vdp_total:,.0f}</div><div class="l">Projected VDPs / month<br>on Cars.com</div></div>
    <div class="kpi"><div class="v">{proj_conn_total:,.0f}</div><div class="l">Projected connections / month<br>on Cars.com</div></div>
    <div class="kpi"><div class="v">{proj_leads_total:,.0f}</div><div class="l">Projected leads / month<br>(phone · email · chat)</div></div>
    <div class="kpi"><div class="v">${mid/1000:,.0f}K</div><div class="l">Projected incremental gross / month<br>(midpoint)</div></div>
  </div>
</div>

<div class="section">
  <h2>Your used lot on the Demand Signals "Churners" quadrant</h2>
  <p style="font-size:13px;margin:0 0 12px">Each bubble is a <b>used</b> nameplate you currently stock, placed by where it sits in the DFW used market — horizontal = market supply, vertical = market demand (VDPs). Bubble size = how many you have. The upper-right quadrant is <b style="color:{TEAL}">Churners</b>: the cars buyers are actively shopping AND that move at volume. <b>{matched} of {used_total}</b> of your used vehicles matched a DFW demand nameplate. (New inventory isn't plotted — the used market is where the demand signal lives.)</p>
  <div class="chartbox"><canvas id="q"></canvas></div>
</div>

<div class="section">
  <h2>Inventory mix by demand quadrant</h2>
  <table class="tbl-q"><thead><tr><th>Quadrant</th><th class="num">Vehicles</th><th class="num">% of lot</th><th>What it means</th></tr></thead>
  <tbody>{quad_rows}</tbody></table>
  <p style="font-size:13px;margin:14px 0 4px">Your <b>Churner</b> nameplates — the proven movers you already stock — colored by quadrant. <b>Click chips to build a group</b>: each highlights on the chart above and the KPI total below updates live. Use the quadrant filters or "show all" to explore every nameplate.</p>
  <div class="chips-legend" id="legend"></div>
  <div class="chips" id="chips"></div>
  <a id="chipToggle" style="display:inline-block;margin:2px 0 10px;font-size:12px;font-weight:700;color:{PURPLE};cursor:pointer;text-decoration:none;border-bottom:2px solid {TEAL};padding-bottom:1px"></a>
  <div class="chip-detail" id="chipTotals"></div>
</div>

<div class="section">
  <h2>Projected monthly performance on Cars.com</h2>
  <table class="tbl-even"><thead><tr><th>Store</th><th class="num">New</th><th class="num">Used</th><th class="num">Total</th><th class="num">Proj. VDPs/mo</th><th class="num">Proj. connections/mo</th><th class="num">Proj. leads/mo</th></tr></thead>
  <tbody>{store_rows}
  <tr style="font-weight:700;background:#faf7fc"><td>Total</td><td class="num">{new_total:,}</td><td class="num">{used_total}</td><td class="num">{grand_total:,}</td><td class="num">{proj_vdp_total:,.0f}</td><td class="num">{proj_conn_total:,.0f}</td><td class="num">{proj_leads_total:,.0f}</td></tr>
  </tbody></table>
  <p class="small" style="margin-top:8px">Projection covers your <b>full {grand_total:,}-vehicle inventory</b> (new + used) at the blended all-stock per-vehicle rate ({blend_vdp:.1f} VDPs · {blend_conn:.3f} connections / vehicle / month). The demand quadrant above details where your {used_total} used vehicles sit. <b>Leads</b> = phone + email + chat (the direct-contact subset of connections), here {lead_share*100:.0f}% of projected connections.</p>
</div>

<div class="section">
  <h2>Revenue framing</h2>
  <p style="font-size:13px;margin:0 0 6px">These stores are currently <b>dark on Cars.com</b>, so all of it is net-new: <b>{proj_leads_total:,.0f} direct leads/month</b> plus the broader {clicks_total:,.0f} click/transfer engagements. Closing the leads at a luxury rate and converting a small slice of the clicks:</p>
  <div class="rev">
    <div class="box"><div class="v">${lo/1000:,.0f}K</div><div class="small">Conservative<br>({rv['close_range'][0]*100:.0f}% lead close · {rv['click_close_range'][0]*100:.1f}% click · ${rv['gpu_range'][0]/1000:.0f}K GPU)</div></div>
    <div class="box mid"><div class="v" style="color:{PURPLE}">${mid/1000:,.0f}K</div><div class="small">Midpoint<br>({rv['close_rate']*100:.0f}% lead close · {rv['click_close_rate']*100:.0f}% click · ${rv['gpu']/1000:.1f}K GPU)</div></div>
    <div class="box"><div class="v">${hi/1000:,.0f}K</div><div class="small">Upper<br>({rv['close_range'][1]*100:.0f}% lead close · {rv['click_close_range'][1]*100:.1f}% click · ${rv['gpu_range'][1]/1000:.0f}K GPU)</div></div>
  </div>
  <p class="small" style="margin-top:10px">Monthly incremental gross = (leads × lead-close rate + click/transfer engagements × click-conversion) × avg gross-per-unit. Midpoint ≈ <b>${mid*12/1000:,.0f}K/year</b> incremental.</p>
</div>

{hist_html}
</div>
<script>
const SC = {json.dumps(scatter)};
const MEDV = {med_veh:.0f}, MEDD = {med_vdp:.0f};
const quadPlugin = {{ id:'quad', beforeDraw(c){{
  const {{ctx, chartArea:a, scales:{{x,y}}}}=c; if(!a) return;
  const px=x.getPixelForValue(MEDV), py=y.getPixelForValue(MEDD);
  ctx.save();
  ctx.fillStyle='rgba(0,168,142,.06)'; ctx.fillRect(px,a.top,a.right-px,py-a.top);      // churner UR
  ctx.fillStyle='rgba(142,68,173,.05)'; ctx.fillRect(a.left,a.top,px-a.left,py-a.top);  // niche UL
  ctx.fillStyle='rgba(192,57,43,.05)'; ctx.fillRect(px,py,a.right-px,a.bottom-py);      // lot sitter LR
  ctx.strokeStyle='#bbb'; ctx.setLineDash([5,4]); ctx.beginPath();
  ctx.moveTo(px,a.top); ctx.lineTo(px,a.bottom); ctx.moveTo(a.left,py); ctx.lineTo(a.right,py); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle='#00A88E'; ctx.font='bold 13px Poppins,Arial';
  ctx.fillText('CHURNERS',a.right-90,a.top+18);
  ctx.fillStyle='#8E44AD'; ctx.fillText('NICHE',a.left+8,a.top+18);
  ctx.fillStyle='#C0392B'; ctx.fillText('LOT SITTERS',px+8,a.bottom-10);
  ctx.fillStyle='#E08E0B'; ctx.fillText('RARITY',a.left+8,a.bottom-10);
  ctx.restore();
}}}};
const qchart = new Chart(document.getElementById('q'),{{
  type:'bubble',
  data:{{datasets:[{{data:SC, backgroundColor:SC.map(p=>p.color+'cc'), borderColor:SC.map(p=>p.color), borderWidth:1}}]}},
  options:{{plugins:{{legend:{{display:false}},
    tooltip:{{callbacks:{{label:c=>{{const p=c.raw;return p.label+'  ('+p.count+' in stock) — '+p.quad+'  | mkt supply '+p.x.toLocaleString()+', mkt VDPs '+p.y.toLocaleString();}}}}}}}},
    scales:{{x:{{title:{{display:true,text:'DFW market supply (used vehicles listed) →'}},type:'linear'}},
            y:{{title:{{display:true,text:'DFW market demand (VDPs) →'}}}}}}}},
  plugins:[quadPlugin]
}});

// ---- interactive color-coded nameplate chips (multi-select group calculator) ----
const CHIPS = {json.dumps(chips)};
const QC = {json.dumps(QUAD_COLORS)};
const REV = {{close:{rv['close_rate']}, gpu:{rv['gpu']}}};
const LEAD = {lead_share};
const TOTAL = {{veh:{n}, vdp:{proj_vdp:.0f}, conn:{proj_conn:.0f}}};
const QORDER = ['Churner','Niche','Lot Sitter','Rarity','Unmatched'];
(function(){{
  const legend=document.getElementById('legend'), box=document.getElementById('chips'),
        totals=document.getElementById('chipTotals'), toggle=document.getElementById('chipToggle');
  let activeQuad='Churner';
  const selected=new Set();
  const counts={{}}; CHIPS.forEach(c=>counts[c.quad]=(counts[c.quad]||0)+c.count);
  const qLabel={{'Unmatched':'Trade / other'}};
  const quads=QORDER.filter(q=>counts[q]); const lbtns={{}};
  const fmt=x=>Math.round(x).toLocaleString();
  quads.forEach(q=>{{
    const lb=document.createElement('button'); lb.className='legend-btn'; lb.style.setProperty('--c',QC[q]);
    lb.innerHTML=`<i style="background:${{QC[q]}}"></i>${{qLabel[q]||q}} <b>${{counts[q]}}</b>`;
    lb.onclick=()=>{{ activeQuad = activeQuad===q?null:q; sync(); }};
    legend.appendChild(lb); lbtns[q]=lb;
  }});
  toggle.onclick=()=>{{ activeQuad = activeQuad ? null : 'Churner'; sync(); }};
  function sync(){{
    quads.forEach(q=>lbtns[q].classList.toggle('on', q===activeQuad));
    toggle.textContent = activeQuad ? `Show all ${{CHIPS.length}} nameplates →` : `← Show Churners only`;
    render();
  }}
  function render(){{
    box.innerHTML='';
    CHIPS.filter(c=>!activeQuad||c.quad===activeQuad).forEach(c=>{{
      const b=document.createElement('button'); b.className='chip'+(selected.has(c.label)?' sel':''); b.style.setProperty('--c',c.color);
      b.innerHTML=`${{c.label}} <span>· ${{c.count}}</span>`;
      b.onclick=()=>pick(c); box.appendChild(b);
    }});
    updateTotals(); highlight();
  }}
  function pick(c){{ selected.has(c.label) ? selected.delete(c.label) : selected.add(c.label); render(); }}
  function updateTotals(){{
    const items=CHIPS.filter(c=>selected.has(c.label));
    let veh,vdp,conn,lbl,extra='';
    if(items.length){{
      veh=items.reduce((s,c)=>s+c.count,0); vdp=items.reduce((s,c)=>s+c.pvdp,0); conn=items.reduce((s,c)=>s+c.pconn,0);
      lbl=`${{items.length}} nameplate${{items.length>1?'s':''}} selected`;
      if(items.length===1){{const c=items[0]; extra=c.x?` &nbsp;·&nbsp; DFW market: ${{Number(c.x).toLocaleString()}} listed, ${{Number(c.y).toLocaleString()}} VDPs`:` &nbsp;·&nbsp; trade-in, outside the DFW demand set`;}}
    }} else {{ veh=TOTAL.veh; vdp=TOTAL.vdp; conn=TOTAL.conn; lbl='All used inventory'; }}
    const gross=conn*REV.close*REV.gpu;
    totals.innerHTML=`<div class="tlabel">${{lbl}}${{extra}}</div>
      <div class="trow">
        <div><span>${{fmt(veh)}}</span>used vehicles</div>
        <div><span>${{fmt(vdp)}}</span>proj. VDPs / mo</div>
        <div><span>${{fmt(conn)}}</span>proj. connections / mo</div>
        <div><span>${{fmt(conn*LEAD)}}</span>proj. leads / mo</div>
        <div><span>$${{fmt(gross/1000)}}K</span>est. gross / mo</div>
      </div>`
      + (items.length ? `<a id="clearSel">Clear selection</a>` : `<div class="thint">Click nameplates to build a group — these totals update live.</div>`);
    if(items.length) document.getElementById('clearSel').onclick=()=>{{ selected.clear(); render(); }};
  }}
  function highlight(){{
    const ds=qchart.data.datasets[0]; const any=selected.size>0;
    ds.data = SC.map(p=>({{...p, r: selected.has(p.label)?Math.min(36,p.r+10):p.r}}));
    ds.borderColor = SC.map(p=> selected.has(p.label)?'#111':p.color);
    ds.borderWidth = SC.map(p=> selected.has(p.label)?3:1);
    ds.backgroundColor = SC.map(p=> p.color + ((any && !selected.has(p.label))?'44':'cc'));
    qchart.update();
  }}
  sync();
}})();
</script>
</body></html>"""

# ----------------------------------------------------------------------------
# Pitch-slide variant — single page, styled to match park_place_pitch_v2.html
# ----------------------------------------------------------------------------
def build_pitch_slide(cfg, vehicles, rates, blend_vdp, blend_conn):
    n = len(vehicles)
    by_store = Counter(v.get("store", "?") for v in vehicles)
    by_quad = Counter(v["quadrant"] for v in vehicles)
    proj_vdp = sum(v["proj_vdp"] for v in vehicles)
    proj_conn = sum(v["proj_conn"] for v in vehicles)
    new_by_store = cfg.get("new_by_store", {})
    new_total = sum(new_by_store.values())
    used_total = n
    grand_total = used_total + new_total
    proj_vdp_total = grand_total * blend_vdp
    proj_conn_total = grand_total * blend_conn
    lead_share = cfg["revenue"]["lead_share_of_conn"]   # Leads = phone+email+chat subset of connections
    proj_leads_total = proj_conn_total * lead_share
    rv = cfg["revenue"]
    clicks_total = proj_conn_total - proj_leads_total
    g = lambda c, ck, gpu: (proj_leads_total*c + clicks_total*ck) * gpu   # blended: lead close + small click conversion
    lo  = g(rv["close_range"][0], rv["click_close_range"][0], rv["gpu_range"][0])
    mid = g(rv["close_rate"], rv["click_close_rate"], rv["gpu"])
    hi  = g(rv["close_range"][1], rv["click_close_range"][1], rv["gpu_range"][1])
    churner_pct = 100*by_quad["Churner"]/n
    date_str = datetime.datetime.strptime(cfg["report_date"], "%Y-%m-%d").strftime("%B %Y")

    # quadrant stacked bar
    seg = []
    for q in ["Churner", "Niche", "Lot Sitter", "Rarity", "Unmatched"]:
        if by_quad.get(q, 0):
            seg.append(f'<div style="width:{100*by_quad[q]/n:.1f}%;background:{QUAD_COLORS[q]}" title="{q}: {by_quad[q]}"></div>')
    bar = "".join(seg)

    chips_data = build_chips(vehicles)
    _churn = [c for c in chips_data if c["quad"] == "Churner"]
    _top = _churn[:10]
    _more = len(_churn) - len(_top)
    top_chips = "".join(f'<span class="tag on">{esc(c["label"])} &middot; {c["count"]}</span> ' for c in _top)
    if _more > 0:
        top_chips += f'<span class="tag" style="border-color:#bbb;color:#888">+{_more} more churners</span>'
    report_name = Path(cfg["out_html"]).name

    srows = ""
    for s in ["Dallas", "Fort Worth", "Arlington"]:
        used_n = sum(1 for v in vehicles if v.get("store") == s)
        new_n = new_by_store.get(s, 0)
        tot = used_n + new_n
        if not tot: continue
        sd = tot * blend_vdp; sc = tot * blend_conn
        srows += (f'<tr><td class="b">{s}</td><td class="r">{new_n:,}</td><td class="r">{used_n:,}</td><td class="r">{tot:,}</td>'
                  f'<td class="r">{sd:,.0f}</td><td class="r">{sc:,.0f}</td><td class="r">{sc*lead_share:,.0f}</td></tr>')

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>{esc(cfg['prospect_name'])} — Inventory Performance Projection</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Poppins',sans-serif;font-size:11px;color:#1a1a2e;background:#fff;padding:28px 32px;max-width:960px;margin:0 auto}}
.hdr{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:18px;padding-bottom:12px;border-bottom:3px solid #6B2D8B}}
.hdr h1{{font-size:21px;font-weight:800;color:#6B2D8B;line-height:1.1}} .hdr p{{font-size:10px;color:#666;margin-top:4px}}
.pill{{display:inline-block;background:#00A88E;color:#fff;font-size:8px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;padding:3px 9px;border-radius:20px}}
.hero{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:#ede0f5;border:1px solid #ede0f5;border-radius:6px;overflow:hidden;margin-bottom:18px}}
.hc{{background:#fff;padding:13px 15px}} .hc .num{{font-size:27px;font-weight:800;color:#6B2D8B;line-height:1}} .hc .num.teal{{color:#00A88E}}
.hc .lbl{{font-size:9px;font-weight:600;color:#444;margin-top:4px;line-height:1.35}}
.sec{{margin-bottom:16px}} .sec-title{{font-size:9px;font-weight:700;color:#6B2D8B;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ede0f5}}
.qbar{{display:flex;height:22px;border-radius:4px;overflow:hidden;margin-bottom:8px}}
.qkey{{font-size:8.5px;color:#666}} .qkey span{{display:inline-block;margin-right:12px}} .qkey i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:middle}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
thead tr{{background:#6B2D8B;color:#fff}} thead th{{padding:5px 9px;text-align:left;font-weight:600;font-size:8.5px}}
th.r,td.r{{text-align:right}} tbody tr:nth-child(even){{background:#faf6fd}} tbody td{{padding:5px 9px;border-bottom:1px solid #f0e8fa;color:#222}} td.b{{font-weight:600}}
.tot td{{background:#f0e8f8!important;font-weight:700}}
.note{{padding:10px 13px;border-radius:0 5px 5px 0;font-size:10px;line-height:1.55;background:#edf8f5;border-left:3px solid #00A88E;color:#333}} .note strong{{color:#00875f}}
.tag{{display:inline-block;font-size:7.5px;font-weight:700;padding:2px 7px;border-radius:20px;border:1px solid;white-space:nowrap;margin:0 2px 4px 0}}
.tag.on{{background:#e8f7f4;color:#00875f;border-color:#00A88E}}
.legend-btn{{cursor:pointer;border:1px solid #ddd;background:#fff;border-radius:20px;padding:3px 10px;font:600 9px Poppins,sans-serif;color:#444;display:inline-flex;align-items:center;gap:5px;margin:0 4px 4px 0}}
.legend-btn i{{width:9px;height:9px;border-radius:50%;display:inline-block}}
.legend-btn.on{{border-color:var(--c);box-shadow:0 0 0 2px color-mix(in srgb,var(--c) 28%,transparent)}}
.chip{{cursor:pointer;border:1.5px solid var(--c);color:var(--c);background:#fff;border-radius:20px;padding:2px 9px;font:700 8.5px Poppins,sans-serif;margin:0 3px 5px 0;transition:background .12s,color .12s}}
.chip span{{opacity:.6;font-weight:500}}
.chip:hover{{background:color-mix(in srgb,var(--c) 12%,#fff)}}
.chip.sel{{background:var(--c);color:#fff}}
.chip-detail{{font-size:9px;color:#555;background:#faf6fd;border-radius:5px;padding:8px 11px;margin-top:8px;min-height:14px}}
.chip-detail .sw{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:middle}}
.stat-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}} .stat-box{{background:#faf6fd;border-radius:5px;padding:10px 12px;text-align:center}}
.stat-box .sv{{font-size:21px;font-weight:800;color:#00A88E;line-height:1}} .stat-box.mid .sv{{color:#6B2D8B}} .stat-box .sl{{font-size:8.5px;color:#666;margin-top:3px}}
.ask{{background:linear-gradient(135deg,#6B2D8B 0%,#4a1f63 100%);color:#fff;border-radius:6px;padding:15px 20px;margin-top:16px;display:flex;justify-content:space-between;align-items:center;gap:20px}}
.ask strong{{font-size:13px;font-weight:700;display:block;margin-bottom:5px;color:#e8d5f5}} .ask p{{font-size:10.5px;line-height:1.5;color:#ddd}}
.ask .av{{font-size:25px;font-weight:800;color:#fff;line-height:1;white-space:nowrap}} .ask .al{{font-size:8px;color:#c9a0e0;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;text-align:right}}
.fn{{font-size:8px;color:#bbb;line-height:1.5;border-top:1px solid #eee;padding-top:8px;margin-top:12px}}
@media print{{*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}body{{padding:18px 22px}}}}
</style></head><body>

<div class="hdr">
  <div><h1>Your Inventory on Cars.com — Modeled Performance</h1>
  <p>{esc(cfg['prospect_name'])} · {esc(cfg['dma'])} · {grand_total:,} vehicles ({new_total:,} new + {used_total} used) across 3 stores</p></div>
  <div style="text-align:right"><span class="pill">Demand Signals Projection</span><p style="margin-top:6px;color:#888">{date_str}</p></div>
</div>

<div class="hero">
  <div class="hc"><div class="num">{grand_total:,}</div><div class="lbl">Total vehicles (new + used)<br>{new_total:,} new · {used_total} used</div></div>
  <div class="hc"><div class="num teal">{proj_vdp_total:,.0f}</div><div class="lbl">Projected VDPs / month<br>on Cars.com</div></div>
  <div class="hc"><div class="num">{proj_conn_total:,.0f}</div><div class="lbl">Projected connections / month<br>on Cars.com</div></div>
  <div class="hc"><div class="num">{proj_leads_total:,.0f}</div><div class="lbl">Projected leads / month<br>phone · email · chat</div></div>
  <div class="hc"><div class="num teal">${mid/1000:,.0f}K</div><div class="lbl">Projected incremental gross / mo<br>≈ ${mid*12/1000:,.0f}K / year</div></div>
</div>

<div class="sec">
  <div class="sec-title">Your used lot on the DFW demand map</div>
  <div class="qbar">{bar}</div>
  <div class="qkey">
    <span><i style="background:{QUAD_COLORS['Churner']}"></i>Churner {by_quad.get('Churner',0)}</span>
    <span><i style="background:{QUAD_COLORS['Lot Sitter']}"></i>Lot Sitter {by_quad.get('Lot Sitter',0)}</span>
    <span><i style="background:{QUAD_COLORS['Rarity']}"></i>Rarity {by_quad.get('Rarity',0)}</span>
    <span><i style="background:{QUAD_COLORS['Niche']}"></i>Niche {by_quad.get('Niche',0)}</span>
    <span><i style="background:{QUAD_COLORS['Unmatched']}"></i>Other/Trade {by_quad.get('Unmatched',0)}</span>
  </div>
  <div class="note" style="margin-top:10px"><strong>{churner_pct:.0f}% of your used inventory are Churners</strong> — the exact vehicles DFW shoppers are actively viewing <em>and</em> buying at volume. These are the cars that earn engagement on Cars.com from day one.</div>
  <p style="font-size:9.5px;font-weight:600;color:#444;margin:11px 0 6px">Your top proven movers (Churners you already stock):</p>
  <div>{top_chips}</div>
  <a href="{report_name}" style="display:inline-block;margin-top:11px;font-size:10px;font-weight:700;color:#6B2D8B;text-decoration:none;border-bottom:2px solid #00A88E;padding-bottom:2px">Explore all {len(chips_data)} nameplates ({n} vehicles), color-coded &amp; filterable, on the interactive demand map &rarr;</a>
</div>

<div class="sec">
  <div class="sec-title">Projected monthly performance on Cars.com</div>
  <table><thead><tr><th>Store</th><th class="r">New</th><th class="r">Used</th><th class="r">Total</th><th class="r">VDPs / mo</th><th class="r">Connections / mo</th><th class="r">Leads / mo</th></tr></thead>
  <tbody>{srows}
  <tr class="tot"><td>Total</td><td class="r">{new_total:,}</td><td class="r">{used_total}</td><td class="r">{grand_total:,}</td><td class="r">{proj_vdp_total:,.0f}</td><td class="r">{proj_conn_total:,.0f}</td><td class="r">{proj_leads_total:,.0f}</td></tr>
  </tbody></table>
</div>

<div class="sec">
  <div class="sec-title">What that's worth — incremental gross / month (net-new; stores are dark today)</div>
  <div class="stat-row">
    <div class="stat-box"><div class="sv">${lo/1000:,.0f}K</div><div class="sl">Conservative · {rv['close_range'][0]*100:.0f}% lead close + {rv['click_close_range'][0]*100:.1f}% click · ${rv['gpu_range'][0]/1000:.0f}K GPU</div></div>
    <div class="stat-box mid"><div class="sv">${mid/1000:,.0f}K</div><div class="sl">Midpoint · {rv['close_rate']*100:.0f}% lead close + {rv['click_close_rate']*100:.0f}% click · ${rv['gpu']/1000:.1f}K GPU</div></div>
    <div class="stat-box"><div class="sv">${hi/1000:,.0f}K</div><div class="sl">Upper · {rv['close_range'][1]*100:.0f}% lead close + {rv['click_close_range'][1]*100:.1f}% click · ${rv['gpu_range'][1]/1000:.0f}K GPU</div></div>
  </div>
</div>

<div class="ask">
  <div><strong>Put your inventory back in front of in-market DFW shoppers.</strong>
  <p>Your used lot is {churner_pct:.0f}% proven Churners, and your full {grand_total:,}-vehicle inventory would generate an estimated {proj_conn_total:,.0f} new connections every month that you're leaving on the table today.</p></div>
  <div><div class="av">{proj_conn_total:,.0f}</div><div class="al">Net-new connections / mo</div></div>
</div>

<div class="fn">Modeled from {grand_total:,} vehicles ({new_total:,} new + {used_total} used) scraped live from the Park Place store sites, {date_str}. Used-lot demand quadrant from admin.cars.com Demand Signals (DFW, Used). Per-vehicle rate is an all-stock blend of an active comparable (MB of Plano) and the current DFW Mercedes-Benz market, applied to the full inventory. Projection, not a guarantee — actual results depend on merchandising, pricing, and response speed. Connections = all Cars.com engagement events (listing &amp; deep-link clicks, website transfers, phone, email, chat); Leads = the phone + email + chat subset (direct contacts), modeled at {lead_share*100:.0f}% of connections.</div>

</body></html>"""

# ----------------------------------------------------------------------------
def main():
    cfg = CONFIG
    inv = json.loads(Path(cfg["inventory_json"]).read_text())
    vehicles = inv["vehicles"]
    # clean: doc-fee price artifact -> null
    for v in vehicles:
        if v.get("price") in (225, 225.0): v["price"] = None

    mc = load_csv(cfg["market_comparison_csv"])
    lookup, med_veh, med_vdp, market_rows = build_market(mc, cfg["primary_make"])
    dq_lookup = build_dq_lookup(load_csv(cfg["demand_quadrants_csv"]))
    rates, blend_vdp, blend_conn = per_veh_rates(cfg["legs"], cfg["weights"])
    project(vehicles, lookup, dq_lookup, blend_vdp, blend_conn, cfg["quad_mult"])

    html_out = build_html(cfg, vehicles, market_rows, med_veh, med_vdp, rates, blend_vdp, blend_conn)
    Path(cfg["out_html"]).write_text(html_out)
    Path(cfg["out_slide"]).write_text(build_pitch_slide(cfg, vehicles, rates, blend_vdp, blend_conn))

    # console summary
    bq = Counter(v["quadrant"] for v in vehicles)
    print(f"Vehicles: {len(vehicles)}  | quadrant mix: {dict(bq)}")
    print(f"Median split: supply={med_veh:.0f} vehicles, demand={med_vdp:.0f} VDPs  | market nameplates={len(market_rows)}")
    print(f"Blended base rates: {blend_vdp:.2f} VDPs/veh/mo, {blend_conn:.3f} conn/veh/mo")
    print(f"Projected: {sum(v['proj_vdp'] for v in vehicles):,.0f} VDPs/mo, {sum(v['proj_conn'] for v in vehicles):,.0f} connections/mo")
    print(f"Report -> {cfg['out_html']}")
    print(f"Slide  -> {cfg['out_slide']}")

if __name__ == "__main__":
    main()
