---
name: project-pb-report-production
description: "PB report production status, file paths, custom view URLs, and key fixes from 2026-05-22 build-out"
metadata: 
  node_type: memory
  type: project
  originSessionId: 85ca47c6-5c92-4c4c-9c30-2fd17d6f34b0
---

Both Nalley and Hendrick PB reports are fully automated end-to-end (Tableau → sheet → send).

**Status as of 2026-05-22:** Production-ready. Tested and approved.

**Custom View URLs (pre-filtered, no recompute):**
- Nalley: `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/eaf9a030-bda1-4bc9-a771-574c63bacb9d/NalleyLexusGalleriaPBReport`
- Hendrick: `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/8a3a0039-6729-4f23-98bb-099bca061385/HendrickPBReport`

**Why:** DMA=All recompute for Hendrick was 5+ min / browser-crashing. Custom views load pre-filtered in ~20s.

**Dealer-specific LEI filenames (prevents collision):**
- Nalley: `~/.playwright-mcp/nalley_lei.csv`
- Hendrick: `~/.playwright-mcp/hendrick_lei.csv`
After Tableau download, immediately `mv` from the default `Low-Engaged-Inventory-Report---Local-v2.csv`.

**pb_report.py key fixes:**
- `--send` flag: creates draft then sends immediately via `drafts().send()`
- `--to` override: test mode only — also clears CC automatically
- `_pick_top_vehicles()`: SAM-diverse top 5 (one per SAM first, then fill)
- LEI deduplication by stock number before sheet import
- Hendrick column mapping: col B=Store, col C=Vehicle (configured via `pbt_store_col`/`pbt_vehicle_col`)
- Nalley email format: MMYT (Stk/VIN) → drop $X for Badge
- Hendrick email format: SAM / Store — Vehicle → drop $X for Badge

**Email recipients (baked into pb_report.py config):**
- Nalley To: gcaudill1@nalleycars.com, jbrown1@nalleycars.com, zibrahimbegovic@asburyauto.com, rsaeed@nalleycars.com; CC: sdharanendra@asburyauto.com
- Hendrick To: anne.Lewis@hendrickauto.com; From: jcrawley@carscommerce.inc

**Schedules (LaunchAgents, loaded and active):**
- Nalley: Mon + Fri at 6:00 AM MST (`com.jcrawley.nalley-pb-report.plist`)
- Hendrick: Mon at 6:00 AM MST (`com.jcrawley.hendrick-pb-report.plist`)
- Playwright runs headless (`--headless` in scheduled mcp-config.json)

**Before leaving for extended absence:**
- Run `caffeinate -s &` to prevent sleep
- Screen lock must stay off (IT-managed — cannot disable; headless Playwright handles this)
