# Book-of-Business Health Scan — /book-scan

Weekly automated scan across all accessible dealer groups. Surfaces investigation
flags, expiring products, and upsell signals. Powered by `biz_scan.py` — no MCP
dependency, runs cleanly via launchd.

**Usage:**
```
/book-scan                          # full scan, all groups
/book-scan sonic,aca                # specific groups only
/book-scan --email                  # also draft Gmail digest
/book-scan --dry-run                # Tableau only, skip SF queries
```

---

## Steps

### Step 1 — Run the Scan

```bash
cd ~/Documents/scripts
python3 biz_scan.py {args}
```

Where `{args}` is built from the user's input:
- Group filter → `--groups sonic,aca`
- `--email` → pass through
- `--dry-run` → pass through
- No args → run everything

The script prints live progress (Tableau pulls, SF queries) then the full triage.

### Step 2 — Surface Key Findings

After the script completes, read the console output and highlight:

1. **Critical trends** (CRITICAL badge — 3+ consecutive weeks flagged)
   - Name the store, how many weeks, top scenario
   - These are your highest-priority retention risks

2. **New HIGH flags** (NEW badge this week)
   - Top 3-5, with scenario and signal
   - These need attention before next scan

3. **Expiring products** (≤30 days = CRITICAL, ≤90 days = WARN)
   - Name, product, days remaining, MRR
   - These need renewal conversations initiated now

4. **Upsell signals**
   - Bright spots (both metrics growing) with low MRR
   - Frame: "performing well, growth package conversation opportunity"

### Step 3 — Open HTML Digest (optional)

```bash
open ~/Documents/Reports/InvestigationScans/biz_scan_latest.html
```

The HTML digest has the full flag table, expiration list, and upsell candidates
in Cars Commerce brand styling.

### Step 4 — Email Draft (if --email)

If user requested an email draft, use Gmail MCP to compose a draft:

**To:** (ask user or leave blank for self-review)
**Subject:** `Book-of-Business Scan — {date} | {N} HIGH flags across {N} stores`

**Body structure:**
```html
<p>Weekly scan complete — {N} stores reviewed across {group_count} groups.</p>

<h3>Needs Attention This Week</h3>
<ul>
  <!-- CRITICAL trends first (3+ weeks), then NEW HIGH flags -->
  <!-- Each: store name, scenario, signal, suggested action -->
</ul>

<h3>Expiring Products (≤30 days)</h3>
<ul><!-- Critical expirations only --></ul>

<h3>Upsell Signals</h3>
<ul><!-- Top 3 bright spots with growth headroom --></ul>

<p><a href="file:///Users/jcrawley/Documents/Reports/InvestigationScans/biz_scan_{date}.html">
Full HTML Digest</a></p>

<p>Cheers,<br>Jake</p>
```

Draft only — never send.

### Step 5 — Next Actions

After surfacing the findings, offer:

```
Next actions:
  [1] Run /prep brief for a specific flagged store
  [2] Run /auto-research deep dive on top flagged store
  [3] Run /investigate-stores {group} --brief for talking points
  [4] Open HTML digest in browser
  [Enter] Done
```

---

## Scheduling

This scan runs automatically every Monday at 7:00 AM via launchd:
```
com.jcrawley.biz-scan.plist
```

**To check last run:**
```bash
tail -50 ~/.claude/logs/book-scan.log
```

**To trigger manually (same as scheduled run):**
```bash
launchctl start com.jcrawley.biz-scan
```

**To view latest HTML digest:**
```bash
open ~/Documents/Reports/InvestigationScans/biz_scan_latest.html
```

---

## Failure Handling

| Failure | Action |
|---|---|
| `TABLEAU_PAT_SECRET not set` | Check `~/.zshrc` or settings.json env; re-run after fixing |
| Tableau 401 | Run `/recover/tableau-401` then retry |
| Group returns 0 rows | Noted inline — skipped, other groups continue |
| SF CLI fails | Run with `--dry-run` to get Tableau-only results |
| No history file | First run — all flags marked NEW, history saved for next week |

---

## Key Reference

- **Script:** `~/Documents/scripts/biz_scan.py`
- **History:** `~/.claude/scan_history/biz_scan_latest.json`
- **Reports:** `~/Documents/Reports/InvestigationScans/`
- **Latest digest:** `~/Documents/Reports/InvestigationScans/biz_scan_latest.html`
- **Logs:** `~/.claude/logs/book-scan.log`
- **Related:** `/investigate-stores` (on-demand any scope), `/prep` (single store brief)
