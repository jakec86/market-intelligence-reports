# Dealer Market Share Demand Analysis

## Data Sources

| Report | Source | Make Filter | ZIP Level |
|--------|--------|-------------|-----------|
| Market Share Analysis | admin.cars.com Demand Signals (crosstab) | Yes — make/model/stock type | No — DMA level only |
| ZIP Demand Map | Tableau view `39464986` ("Searches by Zip Code") | No — all-make only | Yes |

> **Known limitation:** No single available source provides both ZIP-level data AND make filtering. The Tableau ZIP view's `vf_make` parameter is silently ignored — confirmed by comparing filtered vs. unfiltered API responses (identical row counts, no make column in output). Make labels on ZIP maps are cosmetic only.

Run a comprehensive market share and demand score analysis for any dealer store. Produces a color-coded Google Sheet with inventory-level demand scoring using Cars.com's quadrant framework plus dealer-level share performance.

**Required input:** Dealer name or CCID (ask if not provided)

---

## Workflow Overview

1. Look up dealer on admin.cars.com and Salesforce
2. Pull Demand Signals market share data (crosstab download)
3. Compute DMA Quadrant for each make/model (median-based, matching admin.cars.com)
4. Calculate VDP Index, Connection Index, and Share Index for every make/model/stock type
5. Assign 2D Signal classification (Quadrant x Share Index)
6. Export to a Google Sheet with live formulas and conditional formatting
7. Sort by Share Index descending for instant visual prioritization

---

## Step 1 — Identify the Dealer

- If user provides a **CCID**, search admin.cars.com: `/dealers/all/reports?query={CCID}`
- If user provides a **dealer name**, search admin.cars.com by name or use Salesforce: `FIND {name} IN Name Fields RETURNING Account (Name, CCID__c, BillingCity, BillingState, Account_Status__c, Type, Website, Phone)`
- Capture: **dealer name, CCID, UUID, city, state, DMA, franchise type**

---

## Step 2 — Pull Demand Signals Market Share

Navigate to: `https://admin.cars.com/dealers/{UUID}/reports/demand_signals`

1. Wait for Tableau iframe to fully load (~8 seconds)
2. Confirm DMA name, month, and KPI tiles (Inventory, VDPs, Connections) are visible
3. Click **"Download Crosstab"** button inside the Tableau iframe
4. Select **"Market Comparison"** sheet
5. Select **CSV** format
6. Click **Download**
7. Read the downloaded CSV file (UTF-16 encoded, tab-delimited)

The CSV contains columns: Make, Model, Stock type, DMA market name, FALSE, TRUE, Dealer vehicles, Market vehicles, Vehicle share (%), Dealer VDPs, Market VDPs, VDP share (%), Dealer connections, Market connections, Connections share (%)

---

## Step 3 — Compute DMA Quadrants

Cars.com's Demand Signals report classifies every make/model into quadrants using **DMA median splits**. We replicate this from the Market Comparison CSV data:

### Calculate DMA Medians
Using the **Market vehicles** and **Market VDPs** columns from the CSV (these are DMA-level totals per make/model):

```
Median Vehicles = MEDIAN of all Market vehicles values (excluding zeros)
Median VDPs = MEDIAN of all Market VDPs values (excluding zeros)
```

### Assign Quadrant
For each make/model row:

| Market Vehicles | Market VDPs | Quadrant |
|-----------------|-------------|----------|
| >= Median | >= Median | **Churner** |
| >= Median | < Median | **Lot Sitter** |
| < Median | >= Median | **Rarity** |
| < Median | < Median | **Niche** |

### Quadrant Definitions (from admin.cars.com)
- **Churner** — High inventory, high demand. Popular vehicles shoppers actively search for.
- **Lot Sitter** — High inventory, low demand. Vehicles with more supply than shopper interest.
- **Rarity** — Low inventory, high demand. In-demand vehicles with limited market availability.
- **Niche** — Low inventory, low demand. Specialty vehicles with targeted buyer interest.

---

## Step 4 — Calculate Share Indices

For each row in the CSV, compute:

### VDP Index
```
VDP Index = VDP Share % / Vehicle Share %
```
- Measures: are shoppers viewing this dealer's listings proportional to their inventory presence?

### Connection Index
```
Connection Index = Connections Share % / Vehicle Share %
```
- Measures: are shoppers converting (leads) proportional to their inventory presence?

### Share Index
```
Share Index = (VDP Index × 0.4) + (Connection Index × 0.6)
```
- Weighted toward connections since they're closer to actual leads
- If Vehicle Share % = 0, all indices = 0

**Share Index = 1.0** means capturing engagement proportional to inventory. Above 1.0 = outperforming market share. Below 1.0 = underperforming market share.

---

## Step 5 — Assign 2D Signal Classification

Combine the Quadrant (market context) with Share Index (dealer performance) into an actionable signal:

| Quadrant | Share Index >= 1.0 | Share Index < 1.0 |
|----------|-------------------|-------------------|
| **Churner** | **Market Leader** | **Underperformer** |
| **Lot Sitter** | **Well Positioned** | **Oversaturated** |
| **Rarity** | **Niche Winner** | **Hidden Gem** |
| **Niche** | **Specialty** | **Low Priority** |

### Signal Definitions

**Market Leader** — Churner + outperforming. High-volume model where the dealer commands outsized engagement. Protect this position.

**Underperformer** — Churner + underperforming. High-volume model that should be driving proportional engagement but isn't. Investigate merchandising, pricing, photos. This is the #1 lever — fixing Churner underperformers has the highest ROI because the demand already exists.

**Well Positioned** — Lot Sitter + outperforming. Despite market oversupply, this dealer's listings still capture more than their fair share. Strong merchandising in a competitive segment.

**Oversaturated** — Lot Sitter + underperforming. Too much supply chasing too little demand, and the dealer isn't standing out. Consider reducing inventory depth or improving listing quality to differentiate.

**Niche Winner** — Rarity + outperforming. Low-supply, high-demand model where the dealer dominates. These are the unicorns — stock more if sourcing allows.

**Hidden Gem** — Rarity + underperforming share. The demand exists in the market but the dealer isn't capturing their share. Often a merchandising/pricing issue on otherwise desirable inventory.

**Specialty** — Niche + outperforming. Low-volume specialty model where the dealer does well with targeted buyers. Stable but don't over-invest.

**Low Priority** — Niche + underperforming. Low demand and low share — not worth significant attention. Typical for single-unit oddball inventory.

---

## Step 6 — Create Google Sheet

### Sheet Structure

**Tab 1: "Demand Analysis"** — Full dataset with 18 columns:

| Column | Header | Source |
|--------|--------|--------|
| A | Make | CSV |
| B | Model | CSV |
| C | Stock Type | CSV |
| D | Dealer Vehicles | CSV |
| E | Market Vehicles | CSV |
| F | Vehicle Share % | CSV |
| G | Dealer VDPs | CSV |
| H | Market VDPs | CSV |
| I | VDP Share % | CSV |
| J | Dealer Connections | CSV |
| K | Market Connections | CSV |
| L | Connections Share % | CSV |
| M | VDP Index | Formula: `=ARRAYFORMULA(IF(F2:F=0,0,ROUND(I2:I/F2:F,2)))` |
| N | Connection Index | Formula: `=ARRAYFORMULA(IF(F2:F=0,0,ROUND(L2:L/F2:F,2)))` |
| O | Share Index | Formula: `=ARRAYFORMULA(ROUND((M2:M*0.4)+(N2:N*0.6),2))` |
| P | Quadrant | Formula (see below) |
| Q | Signal | Formula (see below) |
| R | Action | Brief recommendation per signal type |

#### Quadrant Formula (Column P)

First compute medians in helper cells (e.g., S1 and T1):
- S1: `=MEDIAN(E2:E)` (Median Market Vehicles — exclude zeros if needed with MEDIAN(IF(E2:E>0,E2:E)))
- T1: `=MEDIAN(H2:H)` (Median Market VDPs — exclude zeros if needed)

Then in P2:
```
=ARRAYFORMULA(
  IF(E2:E="","",
    IF(AND(E2:E>=$S$1, H2:H>=$T$1), "Churner",
      IF(AND(E2:E>=$S$1, H2:H<$T$1), "Lot Sitter",
        IF(AND(E2:E<$S$1, H2:H>=$T$1), "Rarity",
          "Niche")))))
```

Note: ARRAYFORMULA doesn't support AND() natively in Google Sheets. Use multiplication instead:
```
=ARRAYFORMULA(
  IF(E2:E="","",
    IF((E2:E>=$S$1)*(H2:H>=$T$1), "Churner",
      IF((E2:E>=$S$1)*(H2:H<$T$1), "Lot Sitter",
        IF((E2:E<$S$1)*(H2:H>=$T$1), "Rarity",
          "Niche")))))
```

#### Signal Formula (Column Q)
```
=ARRAYFORMULA(
  IF(P2:P="","",
    IF(P2:P="Churner", IF(O2:O>=1,"Market Leader","Underperformer"),
      IF(P2:P="Lot Sitter", IF(O2:O>=1,"Well Positioned","Oversaturated"),
        IF(P2:P="Rarity", IF(O2:O>=1,"Niche Winner","Hidden Gem"),
          IF(O2:O>=1,"Specialty","Low Priority"))))))
```

#### Action Formula (Column R)
```
=ARRAYFORMULA(
  IF(Q2:Q="","",
    IF(Q2:Q="Market Leader","Protect — strong position",
      IF(Q2:Q="Underperformer","Fix — check pricing/photos/merchandising",
        IF(Q2:Q="Well Positioned","Maintain — standing out despite oversupply",
          IF(Q2:Q="Oversaturated","Reduce depth or improve listings",
            IF(Q2:Q="Niche Winner","Stock more if sourcing allows",
              IF(Q2:Q="Hidden Gem","Improve listings — demand exists",
                IF(Q2:Q="Specialty","Stable — don't over-invest",
                  "Deprioritize — low demand, low return")))))))))
```

**Tab 2: "Summary"** — Analysis tables:

1. **Quadrant Distribution** — Count and % of models in each quadrant
2. **Signal Distribution** — Count of models per signal type, ordered by priority
3. **High-Impact Underperformers** — Churner models with Share Index < 1.0 and 5+ dealer vehicles (the biggest opportunities)
4. **Bright Spots** — Market Leaders and Niche Winners with highest Share Index
5. **DMA Context** — Median vehicles and VDPs used for quadrant splits

### Naming Convention
```
{Dealer Name} ({CCID}) - Demand Analysis
```

---

## Step 7 — Conditional Formatting

Apply conditional formatting to column Q via Apps Script (Extensions > Apps Script):

```javascript
function addConditionalFormatting() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Demand Analysis");
  var lastRow = sheet.getLastRow();
  var range = sheet.getRange("Q2:Q" + lastRow);
  var rules = [];

  // Market Leader — dark green bg, white bold text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Market Leader")
    .setBackground("#006100").setFontColor("#ffffff").setBold(true)
    .setRanges([range]).build());

  // Niche Winner — blue bg, white bold text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Niche Winner")
    .setBackground("#1155cc").setFontColor("#ffffff").setBold(true)
    .setRanges([range]).build());

  // Well Positioned — green bg, dark green text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Well Positioned")
    .setBackground("#b6d7a8").setFontColor("#274e13")
    .setRanges([range]).build());

  // Hidden Gem — light blue bg, dark blue text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Hidden Gem")
    .setBackground("#9fc5e8").setFontColor("#073763")
    .setRanges([range]).build());

  // Specialty — light gray bg, dark gray text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Specialty")
    .setBackground("#d9d9d9").setFontColor("#434343")
    .setRanges([range]).build());

  // Underperformer — orange bg, dark red text, bold
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Underperformer")
    .setBackground("#f6b26b").setFontColor("#990000").setBold(true)
    .setRanges([range]).build());

  // Oversaturated — yellow bg, dark yellow text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Oversaturated")
    .setBackground("#ffe599").setFontColor("#7f6000")
    .setRanges([range]).build());

  // Low Priority — light gray bg, medium gray text
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Low Priority")
    .setBackground("#efefef").setFontColor("#999999")
    .setRanges([range]).build());

  sheet.setConditionalFormatRules(rules);

  // Also format Quadrant column (P) with subtle backgrounds
  var quadRange = sheet.getRange("P2:P" + lastRow);
  var quadRules = sheet.getConditionalFormatRules();

  quadRules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Churner")
    .setBackground("#e6f4ea").setFontColor("#137333")
    .setRanges([quadRange]).build());

  quadRules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Lot Sitter")
    .setBackground("#fef7e0").setFontColor("#7f6000")
    .setRanges([quadRange]).build());

  quadRules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Rarity")
    .setBackground("#e8f0fe").setFontColor("#1a73e8")
    .setRanges([quadRange]).build());

  quadRules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo("Niche")
    .setBackground("#f3f3f3").setFontColor("#666666")
    .setRanges([quadRange]).build());

  sheet.setConditionalFormatRules(quadRules);
}
```

---

## Step 8 — Sort & Finalize

1. Sort the Demand Analysis sheet by **Share Index (column O) descending**
2. After sorting, re-enter ARRAYFORMULAs in M2, N2, O2, P2, Q2, R2 if any rows show blank formula columns
3. Verify the signal color gradient flows from Market Leader/Niche Winner (green/blue) at top through to Low Priority (gray) at bottom
4. Hide helper cells S1/T1 or move them to a "Config" tab

---

## Step 9 — Summary Analysis

After building the sheet, provide a written summary covering:

### Quadrant Distribution
- How many models fall into each quadrant
- What this says about the dealer's market position (e.g., heavy in Niche = exotic/specialty dealer; heavy in Churners = mainstream franchise)

### High-Impact Opportunities
- List every **Underperformer** (Churner + Share Index < 1.0) with 5+ dealer vehicles
- These are the #1 priority — high-demand models where the dealer is leaving engagement on the table
- Include units, Share Index, and a one-line diagnosis

### Hidden Gems
- **Rarity** models with Share Index < 1.0
- Market demand exists but dealer isn't capturing it — usually a merchandising/pricing fix

### Bright Spots
- **Market Leaders** and **Niche Winners** — what's working and why
- Note which models the dealer dominates relative to market share

### The Takeaway
- 2-3 sentence executive summary of the dealer's competitive position
- The single biggest lever for improvement (almost always: fix Churner Underperformers)
- Frame recommendations using the Quadrant language dealers already see on admin.cars.com

---

## Optional Add-Ons (if requested)

- **Price Comparison:** Navigate to the Price Comparison tab for VIN-level pricing. Market Price bands: Above Market (>105%), At Market (95%-105%), Under Market (<95%). Days Live slider available.
- **Performance Trends:** Navigate to `/reports/performance_trends` for 13-month trend data
- **Reputation Health:** Navigate to `/reports/reputation_health` for Cars.com rating, response rate
- **Third-party reviews:** Check CarGurus, AutoTrader, Edmunds, DealerRater, Yelp, Carfax via Google search
- **Salesforce data:** Pull account status, products, owner from SF

### ZIP-Level Market Demand Map

Produces a geographic heat map of where market demand originates in the dealer's DMA.

```bash
python3 ~/Documents/scripts/generate_market_report.py \
  --dma "{DMA name from Step 1}" \
  --quarters 4 \
  --dealer-name "{Dealer Name}" \
  --dealer-address "{Street Address, City, State}"
```

Output: `~/Documents/Reports/{dma-slug}/market_intelligence_{dma-slug}_{date}.html`

**Important:** ZIP data is all-make only — `vf_make` is silently ignored by this Tableau view. Any `--makes` argument is cosmetic (used in the report title/filename only). Use `--quarters 4` to normalize to trailing year and reduce partial-coverage ZIP skew.

---

## Defaults

- **DMA filter:** (All) — uses whichever DMA admin.cars.com assigns to the dealer
- **Month:** Current month (default selection in Demand Signals)
- **Stock type filter:** (All) — includes New, CPO, and Used
- **Share Index weighting:** VDP 40%, Connections 60%
- **Quadrant split:** DMA medians of Market Vehicles and Market VDPs (matching admin.cars.com methodology)
- **Signal threshold:** Share Index >= 1.0 = outperforming, < 1.0 = underperforming
