# Save a Tableau Custom View — Workflow

Use this whenever a Playwright-based Tableau workflow requires filters that trigger slow recomputes (All DMAs, large dealer groups). A saved custom view loads pre-filtered in ~20 seconds, eliminating filter interaction entirely.

---

## When to Use

- DMA filter needs to be expanded beyond the default (Detroit) — especially "All"
- Maj dealer name filter applies to a large group (e.g. Hendrick, Sonic, Asbury)
- Filter steps are causing tab-glass timeouts or browser crashes in automation
- Any view that will run on a recurring schedule

## Steps

1. **Open the view in your real browser** (not Playwright) — authenticate via JumpCloud SSO as normal.

2. **Apply all required filters** via the UI:
   - DMA: click (All) or select specific markets
   - Maj dealer name / Dealer Name: select the target group or store
   - Stock type, Make, Model: any additional filters needed
   - Walk away while recomputes finish — this is the one-time cost.

3. **Save the Custom View:**
   - Click the **Custom View** button in the toolbar (looks like a bookmark/eye icon, labeled "View: Original" or current view name)
   - Click **Save**
   - Give it a descriptive name: e.g. `HendrickPBReport`, `NalleyLexusGalleriaPBReport`
   - Check **Make it my default** if you want it to load by default
   - Click **Save**

4. **Copy the URL** from your browser address bar — it will contain the view GUID:
   ```
   https://us-west-2b.online.tableau.com/#/site/cars/views/{workbook}/{viewId}/{CustomViewName}?:iid=1
   ```
   Drop the `?:iid=1` suffix — that's session-specific. The stable URL is everything before it.

5. **Update the skill** that uses this view:
   - Replace the base LEI URL with the custom view URL
   - Remove all filter interaction steps (DMA, dealer name, etc.)
   - Add a note: "Do NOT click any filters — pre-applied in custom view"
   - Update the Key Facts table with the new URL

---

## Known Custom Views

| View Name | Dealer | URL |
|---|---|---|
| NalleyLexusGalleriaPBReport | Nalley Lexus Galleria | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/eaf9a030-bda1-4bc9-a771-574c63bacb9d/NalleyLexusGalleriaPBReport` |
| HendrickPBReport | Hendrick Automotive Group | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/8a3a0039-6729-4f23-98bb-099bca061385/HendrickPBReport` |

## Notes

- Custom views are personal — only visible to the account that saved them (jcrawley@cars.com)
- If a custom view stops loading (404 or wrong data), re-save it: the view GUID changes when re-saved
- The base LEI view URL is: `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2`
- When adding a new dealer workflow, save the custom view BEFORE wiring up automation
