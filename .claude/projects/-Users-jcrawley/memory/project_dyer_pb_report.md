---
name: project_dyer_pb_report
description: "Dyer & Dyer Volvo weekly Price Badge Report — onboarded 2026-06-12, pre-send, Thu 8 AM; remaining TODOs"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b430de4-c66a-46ca-9fc4-3d25ccc164f7
---

Dyer & Dyer Volvo Cars onboarded as a recurring PB report 2026-06-12 (Marielle approved). Single-store Nalley-layout pipeline. Threshold **$1000**, weekly **Thursdays 8:00 AM MST**.

- **Sheet:** `1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8` (already structured/populated; cars.com Dealer id 10730). The one-time Inventory Engagement Report `1ntpeO3gy5` (shared with Marielle) is a separate retired artifact.
- **Recipients:** Roman Byczek (Roman.Byczek@dyeranddyervolvo.com) + Victor Traitel (Victor.Traitel@dyeranddyervolvo.com) — in `email_final_to`. **PRE-SEND**: `email_to=jcrawley@cars.com` until Jake approves the auto-generated format, then flip `email_final_to`→`email_to`.
- **Tableau custom view:** `DyerDyerVolvo` (GUID `df8e4b1f-0a39-49e8-a08a-c20b4b4192f4`). **admin.cars.com UUID:** `f4cb3cc7-1b08-5d24-a78d-1e877a122410` (Chamblee GA 30341).
- **Built + tested:** `pb_dealers.py` `dyer` entry (threshold/recipients/`email_link_url`), skill `~/.claude/commands/dyer-pb-report.md` (UUID + view baked in), plist `~/Library/LaunchAgents/com.jcrawley.dyer-pb-report.plist` (Thu 8 AM, **NOT loaded yet**), registered in `~/.claude/CLAUDE.md`. Tracker `dyer` key → this sheet (see [[project_pb_link_tracker]]). First supervised run 2026-06-12 succeeded: 8/37 within $1k, 12 Great, 92% At Market; pre-send email landed in Jake's inbox.
- **Also fixed:** `pb_report.py` dem-signal closing line was hardcoded "nearly a third has room" — now scales to actual off-market % (≤15 / ≤40 / >40 bands). Applies to all dealers.
- **LIVE 2026-06-12:** Jake approved the format; `email_to` flipped to Roman+Victor (no `email_final_to`); launchd `com.jcrawley.dyer-pb-report` loaded (Thu 8 AM). `--send` now goes straight to the dealer. Mac wakes via `pmset repeat wakeorpoweron MTWRF 07:00:00`.
- **Runner node (added 2026-06-12, prevents the startup hang):** Dyer is now in `run-report.sh`'s `case` (`*dyer*) DEALER=dyer`) with its own `~/.claude/schedules/mcp-config-dyer.json` → `dyer-profile`. CRITICAL pattern: a dealer MUST have BOTH the case entry AND a matching `mcp-config-<dealer>.json` whose `--user-data-dir` profile name equals `<dealer>-profile` — otherwise it falls back to shared `pb-profile` while cleanup (`pkill -f "<dealer>-profile"`) scrubs the wrong profile, leaving a stale `SingletonLock` that hangs the headless launch for the full 30-min watchdog (root cause of the 2026-06-12 6 AM Nalley triple-timeout). See [[project_pb_report_production]].

- **Google Task (added 2026-06-12):** "Dyer & Dyer Volvo - LEI Report" in the **Priority Tasks** list (id `MTEwNTMwMDQxOTQ5MDA4MzkyMzY6MDow`), notes = raw sheet URL, due Thu Jun 18 — mirrors Nalley's "Nalley Lexus Galleria - LEI Report". Skill Step 5 completes it via `task_search "Dyer & Dyer Volvo"` (Google Tasks search is **substring**, not token-AND — "Dyer LEI" / "Nalley LEI" both return 0; Nalley's run only completes its task because the agent falls back to searching "Nalley"). **Not auto-recurring** (Tasks API can't set recurrence) — it's a single dated task; after a run completes it, the next cycle's task must be recreated (set recurrence in the Tasks UI, or extend the skill to create next Thursday's task on completion).

Related: [[project_pb_report_production]], [[project_pb_link_tracker]].
