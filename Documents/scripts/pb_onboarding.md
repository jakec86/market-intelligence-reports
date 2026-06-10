# Price Badge Report — New Store Onboarding Checklist

Adding a store to the PB report automation takes 5 artifacts. No edits to
`pb_report.py` are needed — all per-dealer config lives in `pb_dealers.py`.

Pick the layout first:
- **Single store** (e.g. Nalley, Dyer): Nalley sheet layout — data starts row 4,
  `callout_style: "mmyt"`, `pbt_store_col: None`, Demand Signals included.
- **Multi-store group** (e.g. Hendrick): Hendrick sheet layout — data starts row 3,
  `callout_style: "sam"`, `pbt_store_col: 1`, a `pbt_filter` block, no Demand Signals.

---

## 1. Google Sheet

1. Make a copy of the matching template sheet:
   - Single store: [Nalley PB sheet](https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8) → File → Make a copy
   - Group: [Hendrick PB sheet](https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM) → File → Make a copy
2. Clear old data values from the Data Import tab(s) — **never clear or rewrite
   formula columns in the Price Badge Tool tab** (VLOOKUPs break; see memory
   `feedback_pb_formulas`).
3. Set the badge threshold in PBT cell **E1** ($500 or $1,000 — ask the AE).
4. Note the new **sheet ID** from the URL.

## 2. Tableau custom view

`vf_` URL filters are RLS-blocked, so each dealer needs a **saved custom view**
on the LEI workbook with all filters pre-applied:

1. Open `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2`
2. Set filters: **DMA** (the store's DMA, or All for groups), **Dealer Name** or
   **Maj dealer name** (deselect All → search → select → Apply), **Stock type = Used**
   (Cars.com doesn't badge New)
3. Save as custom view named `<Store>PBReport` → copy the custom-view URL
4. If Demand Signals are included: find the dealer's admin.cars.com UUID via
   `https://admin.cars.com/dealers/all/reports?query=<name_or_ccid>` and note the
   `/dealers/{UUID}/reports/demand_signals` URL

## 3. `pb_dealers.py` entry

Copy the `NEW STORE TEMPLATE` block at the bottom of
`~/Documents/scripts/pb_dealers.py`, fill in every field. Keep
`email_to: "jcrawley@cars.com"` until Jake approves the format (pre-send review
rule); put the client recipients in `email_final_to`.

## 4. Skill file

Copy the closest-matching skill as a starting point:
- Single store: `~/.claude/commands/nalley-pb-report.md`
- Group: `~/.claude/commands/hendricks-pb-report.md`

Update: custom-view URL, admin.cars.com UUID + Demand Signals step (or delete it),
CSV rename target (`<store>_lei.csv` — avoids collisions in `~/.playwright-mcp/`),
the `pb_report.py --dealer <key>` command, sheet link, QC benchmarks (leave TBD
until 2–3 runs establish ranges), and recipients. Register the new command in
`~/.claude/CLAUDE.md`'s skill table.

## 5. Schedule (launchd)

Copy `~/Library/LaunchAgents/com.jcrawley.nalley-pb-report.plist`, update the
label, skill argument, log paths, and `StartCalendarInterval`. Then:

```bash
launchctl load ~/Library/LaunchAgents/com.jcrawley.<store>-pb-report.plist
```

`run-report.sh` handles the rest (retries, 30-min timeout, failure alerts).
Remind: the Mac must be awake at the scheduled time — `caffeinate -s &` or a
`pmset` wake schedule.

---

## Test sequence (in order)

```bash
# 1. Zero-risk: parse + validate + stats + email preview, no remote calls
python3 ~/Documents/scripts/pb_report.py --dealer <key> --lei <lei.csv> [--dem <dem.csv>] --dry-run
open ~/Documents/Reports/pb_dryrun_<key>_*.html   # eyeball the email

# 2. Live sheet, draft to Jake only (no client exposure)
python3 ~/Documents/scripts/pb_report.py --dealer <key> --lei <lei.csv> [--dem <dem.csv>] --to jcrawley@cars.com

# 3. Full skill end-to-end in an interactive session
/<store>-pb-report

# 4. One supervised scheduled run before trusting the cron
```

After step 2, QC the sheet: title renamed to today, PBT formulas intact
(cols E–J populated, col K filled down), sort correct, Data Import tab hidden.

Only after Jake approves the format: move `email_final_to` → `email_to` in
`pb_dealers.py` and confirm `--send` is in the skill's run command.
