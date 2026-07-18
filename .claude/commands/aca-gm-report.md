# ACA Monthly GM Performance Email — Monthly Workflow

Sends personalized Cars.com performance highlight emails to each ACA store GM.
Mirrors the format Cassie Berry automated for Indigo/Doherty stores.
Script: `~/Documents/scripts/aca_gm_report.py`

---

## Automated (Cowork / headless) execution

When run without arguments or via the Cowork scheduler, execute these steps automatically without pausing for input:

1. Determine the target month (previous calendar month):
```bash
python3 -c "from datetime import datetime, timedelta; d = datetime.now().replace(day=1) - timedelta(days=1); print(d.strftime('%B %Y'))"
```

2. Check that the required Market Opp CSV exists:
```bash
ls ~/Documents/Tableau/aca_market_opp_*.csv | sort | tail -1
```
If no file is found, stop and report: "ACA GM report skipped — Market Opp CSV not found in ~/Documents/Tableau/. Download it from admin.cars.com first."

3. Run the full send:
```bash
python3 ~/Documents/scripts/aca_gm_report.py --month "<MONTH FROM STEP 1>" --send
```

4. Report the result: stores sent, stores skipped, any errors.

---

## Manual Step 1 — Download the Market Opportunities CSV

Place the file in `~/Documents/Tableau/` using the naming convention below.

1. Go to admin.cars.com → ACA group → **Market Opportunities**
2. Click the **Store** tab
3. Filter **Date** to the target month
4. Click **Download Crosstab** → select **"By Store"** sheet → **CSV**
5. Save as `aca_market_opp_{YYYY_MM}.csv` (e.g., `aca_market_opp_2026_05.csv`)

This single file contains **SRPs, VDPs, Connections, Website Transfers, Reviews, and Rating** per store — everything the script needs.

> **Encoding note:** Admin.cars.com exports are UTF-16LE. The script handles this automatically via `read_csv_auto()`.

> **Sales Attribution:** Run `aca_sales_attr_scraper.py` before sending to populate the attribution block. See scraper usage below.

---

## Manual Step 2 — Run the Sales Attribution scraper (optional but recommended)

```bash
python3 ~/Documents/scripts/aca_sales_attr_scraper.py --month "May 2026" --cdp-port 9222 --delay 1.0
```

Requires Chrome running with `--remote-debugging-port=9222` and an active JumpCloud SSO session. Output: `~/Documents/Tableau/aca_sales_attr_YYYY_MM.csv`.

If the scraper isn't run, the attribution block falls back to Connections + Website Transfers from the Market Opp CSV.

---

## Manual Step 3 — Test run (one email to yourself)

```bash
python3 ~/Documents/scripts/aca_gm_report.py --month "May 2026"
```

This sends **one test email** to `jcrawley@cars.com`. Check your inbox and verify:
- Header shows correct month and store name
- All 4 metric tiles populated (SRPs, VDPs, Connections, Website Transfers)
- Attribution block shows units influenced, connections, % new (or fallback)
- Reviews and Rating tiles populated
- Subject line format: `[TEST] Cars.com May 2026 Performance Highlights | Store Name | CCID`

---

## Manual Step 4 — Full send

```bash
python3 ~/Documents/scripts/aca_gm_report.py --month "May 2026" --send
```

Sends to all active ACA store GMs (~52 stores with SRPs > 0). `dmcjunkins@carscommerce.inc` is CC'd on every email.

---

## Optional: Draft mode

```bash
python3 ~/Documents/scripts/aca_gm_report.py --month "May 2026" --draft
```

---

## Optional: Override CSV paths

```bash
python3 ~/Documents/scripts/aca_gm_report.py \
  --month "May 2026" \
  --market-opp ~/Documents/Tableau/my_kpi_file.csv \
  --sales-attr ~/Documents/Tableau/my_sales_file.csv \
  --send
```

---

## Optional: Test a specific store to a specific address

```bash
python3 ~/Documents/scripts/aca_gm_report.py --month "May 2026" --store "Audi Lakeland" --to dmcjunkins@carscommerce.inc
```

---

## Column mapping (first run)

On first run, the script prints all CSV column headers. If any metric tile shows "N/A" for all stores, check the printed column map output — the column name in the CSV may differ. Update `_find_col()` candidates in the script if needed.

Key columns in the Market Opp CSV (as of 2026-04):
- `Total SRP Imps` → SRPs
- `Total VDP Imps` → VDPs
- `Total Connections` → Connections
- `Visit Dealer Web Contact` → Website Transfers
- `Reviews Received` → Reviews
- `Avg. Rating Reviews Received` → Rating
- `Legacy Id` → CCID

---

## GM list source

Contacts are read live from the Danielle GM List Google Sheet (ACA tab).
Sheet ID: `1oZa3ZjDO-oyQ7oCHXOzad14r--o5XdW7rPPpw3BF1i4`

Group-level rows are automatically skipped. Stores with 0 SRPs are skipped (not active on marketplace).
