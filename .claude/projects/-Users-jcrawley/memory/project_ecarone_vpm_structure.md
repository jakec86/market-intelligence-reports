---
name: ecarone-vpm-sheet-structure-convention
description: "Live layout, formulas, and VPM-vs-total convention for the eCarOne VPM Performance tab — supplements the /ecarone-vpm-report skill which is partly stale"
metadata: 
  node_type: memory
  type: project
  originSessionId: c16932d1-6723-4e23-9a13-1e4a2bca21dd
---

As of the June 2026 run, the eCarOne VPM Results sheet (gid 247007646, tab "VPM Performance") differs from the `/ecarone-vpm-report` skill description. Verify the live sheet before trusting the skill's row numbers/coordinates.

**Layout:** The data is now a **Google Sheets Table named "VPM Lift MoM"** spanning roughly B1:K (header row 1, monthly data rows 2+). An **Averages row** sits directly below the last month. There are **no embedded Tableau screenshots and no chart** on this tab — so the skill's Step 2b (insert images at B10/B28) and Step 4 (chart) are **obsolete** for the current layout. Don't insert images unless asked; they'd land on live data.

**Columns / formulas (per data row):**
- B = Month (text, e.g. "May"); C–H = **hardcoded values**; I/J/K = formulas.
- C `NON VPM Imp`, D `VPM Imp`, E `Total Impr`, F `NON VPM Leads`, G `VPM Leads`, H `Total Leads`
- I `=D/E` (% VPM of total Imp), J `=(E-C)/C` (VPM Incremental Imp Lift), K `=(H-F)/F` (Leads Lift)
- Averages row: label "Averages" in col I; J/K = `=AVERAGE(J3,J4,...,J{last})` with **explicit cell refs** (starts at row 3 — excludes the partial "September 22-30" row 2). A boundary-insert does NOT auto-extend these — **manually append the new row's ref** (e.g. add `,J10`).

**Convention (critical):** Map Tableau verbatim then subtract — NON VPM Imp (C) = Tableau "Total Cars.com VDPs" − "VPM VDPs"; Total Impr (E) = Tableau "Total Cars.com VDPs". Same for Leads (F = Total − VPM, H = Total). **QC gate:** col I (`=D/E`) must equal Tableau's "% of VPM VDPs" exactly. The convention discriminator on EXISTING data is **stored `D/C`** (not D/E): if `D/C` ≈ Tableau's VPM% the row is OLD additive (C held the full Total); if `D/E` matches, it's correct. (E==C+D holds in BOTH conventions, so it can't discriminate.) **As of the June 2026 run all rows (Sep 2025–May 2026) are reconciled to the corrected convention** — Sep–Feb were converted arithmetically (new_C=C−D, new_E=old_C, new_F=F−G, new_H=old_F), preserving each month's recorded totals (NOT restated from current Tableau, which has restated older months). Reconcile script: `~/Documents/scripts/ecarone_vpm_reconcile.py`.

**Tableau source:** VDP and Leads views show **all months as columns**; read "Total Cars.com VDPs" + "VPM VDP's" (VDP view) and "Total Cars.com Leads" + "VPM Total Leads" (Leads view) from the table at the bottom. URL filter `Dealer Name + ID=eCarOne - 6000362`.

**Sheets API auth (no MCP write tool needed):** `Credentials.from_authorized_user_file("~/.claude/tokens/sheets_token.json", ["https://www.googleapis.com/auth/spreadsheets"])`, refresh if expired, `build("sheets","v4",...)`. **GOTCHA:** writing values via `values().batchUpdate` (USER_ENTERED) can STRIP a cell's number format — in the June run column E lost its `#,##0` and a subsequent `copyPaste PASTE_FORMAT` propagated the comma-less format to other rows. **After any value write, re-assert `#,##0` on count columns C:H** via a `repeatCell` with `fields="userEnteredFormat.numberFormat"`. For "canonical" formatting, copy `PASTE_FORMAT` from a known-good row (row 7 Feb) onto drifted rows rather than hand-transcribing a spec.

**Editing without Sheets API:** if no google-sheets MCP write tool is loaded, edit via Playwright on the live sheet. Reliable input = select cell via Name box (`#t-name-box`), then type digits + Tab/Enter (Sheets replaces on type). Read formulas via `#t-formula-bar-input` textContent. `getByText`-based fills are unreliable for numbers. To add a month: copy prior row → paste into new row (carries formulas+format), then overwrite B–H. See [[ecarone-vpm-sheet-formatting-standard]] — canonical formatting should ideally be applied via `repeatCell` API, not copy/paste (minor drift risk).
