---
name: project_dealer_market_report_engine
description: "jlr_swh_market_report.py generalized into dealer_market_report.py — profile-driven, works for any dealer"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7f2adbfc-94d5-4a03-9dbb-2c38b11d4d89
---

**`~/Documents/scripts/dealer_market_report.py`** (generalized 2026-07-17 from the JLR-only `jlr_swh_market_report.py`, which is left in place untouched as a reference/fallback) — combines Cars.com LEI + market share + price comparison + a CarGurus HTML dashboard into one HTML performance report, for any dealer.

**Per-dealer config lives in a `PROFILES` dict** (like `[[dark_prospect_report_config_pattern]]` but for a many-dealer tool rather than one-shot): dealer name/match-hints, franchise makes + model hints (e.g. Land Rover implied by "Range Rover"), franchise dealer-name regex for the competitor set, `combine_stores` (merges co-located franchise stores that show up as separate rows, e.g. Jaguar Houston Central + Land Rover Houston Central), aging/benchmark day thresholds, Google Sheet URL, and the period label/month list. Run with `--profile <name>` (built-ins in `PROFILES`) or `--profile-json path.json` for a dealer with no built-in profile yet.

**One structural gap that's inherent, not a bug:** there's no live CSV parser for the quarter's Performance Trends KPIs (VDPs/Connections totals) — those are hand-curated per period into `PROFILES[name]['perf_trends']`. When the reporting period changes, update that dict (see `~/.claude/commands/jlr-swh-report.md` → "Updating Q2 Numbers").

**Dropped as dead code during the generalization** (verified unused via grep before removing): `_JLR_COMP_BRANDS`/`_LUXURY_BRANDS` (defined, never read), a CarGurus "90-day engagement" block (`cg_vdps_90`/`cg_conns_90`/`carscom_days`, computed then never used — the receiving param was even named `_unused_days`), and a fabricated CarGurus deal-ratings fallback (hardcoded JLR percentages returned for ANY dealer when regex extraction failed — replaced with an empty dict + warning unless a profile explicitly opts in via `cargurus_fallback_deal_ratings`).

**Verified no regression:** re-ran against the original JLR SW Houston input files (still in `~/Downloads`) with `--profile jlr_swh` — all 5 KPI values and the 5-row competitor table matched the last known-good `jlr_swh_market_report_2026-06-09.html` output exactly (66%/58%/64%/21%/126 days).

See [[jlr_swh_report_skill]] for the skill wiring and [[project_tools_menu]] for where this shows up in the tools reference page.
