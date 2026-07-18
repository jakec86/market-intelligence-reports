# Price Badge Report — Herb Chambers GM Monthly Touchpoint

Monthly **GM-facing Price Badge touchpoint** for the 6 active Herb Chambers stores: which used
vehicles are closest to earning a better price badge, with the exact reprice to get there. Each GM
gets their own store's report.

**Source: admin.cars.com Listings Optimizer "Live Inventory" crosstab** (per dealer, NOT RLS-limited
— covers stores missing from the Tableau LEI view). It pre-computes the current Price badge, the
`Reduce by` $ to the next badge, and the Good/Great target prices, so no sheet formulas are needed —
`pb_lo_report.py` computes everything and writes a clean values table to the cloned sheet.

**Cadence:** monthly (target 1st Wednesday 8 AM MT — scheduled only after format approval).
**Excludes current cancels:** Toyota of Boston, Cadillac of Warwick.

> **Pre-send review is ACTIVE.** Every config keeps `email_to=jcrawley@cars.com` + `email_final_to=<GM>`,
> so a run drops 6 drafts in Jake's inbox. Do NOT add `--send` or flip recipients until Jake approves
> the format + GM contacts.

---

## Store roster (key · CCID · GM · threshold · admin.cars UUID)

| Key | Store | GM email | CCID | $ thresh | Listings Optimizer UUID |
|---|---|---|---|---|---|
| `hc_seekonk_honda` | Honda of Seekonk | scott@herbchambers.com | 3544 | 500 | `e2f29d16-c231-5aa5-87cd-5be7bf2ea8af` |
| `hc_boston_bmwmini` | BMW MINI of Boston | msteffy@herbchambers.com | 3111 | 1000 | `3c100b29-91c1-567a-b2b3-51695ac7d6ae` |
| `hc_boston_jlr` | Jaguar Land Rover Boston | aelomri@herbchambers.com | 5397676 | 1000 | `94629331-a310-558d-84d0-2ac5b4e2405d` |
| `hc_exotics` | Exotics (RR/Bentley/Lambo) | btaylor@herbchambers.com | 159284 | 5000 | `d3d81440-779e-5637-9fe8-bcb026b9051f` |
| `hc_medford_bmw` | BMW of Medford | msteffy@herbchambers.com | 6000779 | 1000 | `5abef716-f7d8-46cf-9660-1b455a91dc19` |
| `hc_porsche` | Herb Chambers Porsche | jasonobrien@herbchambers.com (Rocco) | 178854 | 1000 | `e445f33b-fa6b-5246-b23e-dcf8ca1d0d97` |

Thresholds + recipients live in `pb_dealers.py`. Exotics uses $5000 (ultra-luxury; $1000 yields zero).

**GM-contact master (authoritative):** "Asbury Contact List/Stores" sheet → **"HC GM list"** tab
(`13313nPLQ34uTnWNEgqSbFI7gNdqJQ5s5OtwF8rj8QB8`, gid `1437565839`). Columns: Dealership · GM First/Last/Email ·
BDM First/Last/Email · Other Contacts. Reconcile `email_final_to` against this tab before any go-live.
Reconciled 2026-06-16: 5 of 6 confirmed; **JLR Boston corrected to aelomri@** (Elomri; prior jsaghbini@ is the
Sudbury GM). **Porsche (CCID 178854, Natick): Jake confirmed jasonobrien@ stays** — master's Porsche *Boston*
(jandrade@) / *Burlington* (MMoiseyev@) are different rooftops; the Natick store isn't in the master. **GM only —
no BDM CC** (master carries BDMs but Jake opted GM-only).

---

## Step 0 — Pre-flight

- **admin.cars.com SSO** — the Playwright persistent profile usually has a live JumpCloud session; if a
  login page appears, run the **JumpCloud / Tableau Login + MFA Sub-procedure** in `/nalley-pb-report`.
- **Playwright MCP** — confirm `mcp__playwright__browser_navigate` is available.
- Gmail/Sheets are handled by `pb_lo_report.py` via Python (Google API) — the local `google-sheets`
  MCP is unreliable here (TLS-interception cert error); the Python path works.

---

## Step 1 — Pull the Live Inventory crosstab for each store (sequential, ~12–15 min)

The download lands at `~/.playwright-mcp/Live-Inventory.csv` each time — rename immediately. For **each**
of the 6 keys, navigate to `https://admin.cars.com/dealers/<UUID>/reports/listings_optimizer`, then:

1. Wait ~8s for the embedded Tableau viz to render.
2. **Snapshot** → click the **"Navigate to 'Inventory'"** tab button (suffix `e88`, but the frame prefix
   `fNN` changes per load — re-snapshot to get the live ref; the suffix shifts once you're in the
   Inventory tab because the grid size differs).
3. Wait ~6s. **Snapshot** → click **"Download Crosstab"** (ref is data-dependent — grep the snapshot).
4. **Snapshot** the dialog → "Live Inventory" sheet is pre-selected → click the **CSV** radio → click **Download**.
5. Rename: `mv ~/.playwright-mcp/Live-Inventory.csv ~/.playwright-mcp/<key>_lo.csv`

> Refs are NOT stable across loads or stores — always re-snapshot (`browser_snapshot`) and grep the
> saved `.yml` for `"Navigate to 'Inventory'"`, `"Download Crosstab"`, and the dialog's `CSV` / `Download`
> refs before each click. If a store's "Live Inventory (N vehicles)" shows 0 used, it has lapsed — skip it.

Schema check (the loader validates this): `Stock num · VIN · Stock type · YMMT · Price badge ·
Price vs Market (%) · Days live · Photos · Price · Reduce by · Good badge target · Great badge target · …`

---

## Step 2 — Generate sheets + drafts

Run the LO generator per dealer (single-dealer; loop the 6 keys). Each clears the cloned sheet's Price
Badge Tool tab, writes a sorted values table, and drafts the email to Jake (pre-send):

```bash
for k in hc_seekonk_honda hc_boston_bmwmini hc_boston_jlr hc_exotics hc_medford_bmw hc_porsche; do
  python3 ~/Documents/scripts/pb_lo_report.py --dealer "$k" --lo ~/.playwright-mcp/${k}_lo.csv
done
```

Dry-run first (no remote: writes email HTML to `~/Documents/Reports/pb_dryrun_<key>_<date>.html`):
add `--dry-run`. After format approval, add `--send` and swap `email_final_to`→`email_to` per store.

---

## Step 3 — Review

Each run prints used count / within-threshold / already-Great + the top callouts, the sheet URL, and the
draft id. Confirm each draft in Gmail (subject, callouts, tracked sheet link), then send after approval.

---

## Failure recovery

Re-run a single store: `python3 ~/Documents/scripts/pb_lo_report.py --dealer <key> --lo ~/.playwright-mcp/<key>_lo.csv`.
Re-running creates a NEW draft — delete the prior one first if regenerating (Gmail `drafts().delete`).
