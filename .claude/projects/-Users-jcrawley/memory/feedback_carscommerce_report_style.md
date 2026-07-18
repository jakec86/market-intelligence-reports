---
name: feedback-carscommerce-report-style
description: "Cars Commerce brand styling spec for HTML reports — colors, layout patterns, component types to use on all future MAE/dealer reports"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 44895112-a081-42f6-8bc5-b468bfe648f2
---

Always apply Cars Commerce brand styling to HTML reports. Do not use plain text or unstyled Google Docs when producing dealer-facing or internal analysis reports.

**Why:** User requested Cars.com style and themes on 2026-05-13 and asked it be noted for future runs.

**How to apply:** Use this CSS token set and component patterns for every HTML report going forward.

## Brand Tokens (CSS Variables)

```css
--purple-dark: #4A1A72
--purple:      #6B2D8B   /* primary Cars.com purple */
--purple-mid:  #8B44AB
--purple-light:#F2EBF8
--purple-tint: #FAF6FD
--teal:        #00A88E   /* positive/success accent */
--teal-light:  #E6F7F4
--red:         #C62828   /* critical/alert */
--red-light:   #FFEBEE
--orange:      #E65100   /* warning */
--orange-light:#FFF3E0
--yellow:      #F57F17   /* low-priority action */
--yellow-light:#FFFDE7
--green:       #2E7D32   /* positive trend */
--green-light: #E8F5E9
--gray-900:    #1A1A1A   /* near-black top bar */
--gray-700:    #424242   /* body text */
--gray-500:    #757575   /* secondary text */
--gray-200:    #EEEEEE   /* borders */
--gray-100:    #F5F5F5   /* page background */
--font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
```

## Page Structure

1. **Top bar** — `background: #1A1A1A`, "Cars Commerce | Account Intelligence" in white
2. **Report header** — `linear-gradient(135deg, #4A1A72, #6B2D8B, #8B44AB)` with white text; report type, dealer name, meta row
3. **Content area** — `max-width: 960px`, gray-100 background, 40px horizontal padding
4. **Sections** — purple uppercase label + horizontal rule via `::after`

## Key Components

- **TL;DR block** — white card, 4px left border in purple, "THE SHORT VERSION" label
- **KPI scorecard** — 3-column grid, cards with colored top border: teal=good, orange=warn, red=crit; root cause card has red-light background
- **Tables** — purple thead, alternating purple-tint rows, dark footer for totals
- **DMA comparison cards** — dealer value in red, market value in teal, gap below separator
- **Problem cards** — numbered circles (red/orange/yellow), left border color-coded
- **Q&A blocks** — purple question label, prose answer
- **Filter split** — 2-col grid, red top border for Remove, teal for Keep
- **Recommendations** — 4-col grid: priority badge | action | impact | timeline
- **Signal classes** — `.ss` teal (star/good), `.sw` orange (warning), `.sc` red (critical)
- **MoM indicators** — `.up` green, `.down` red, `.flat` gray-500

## Upload Pattern

Use `mcp__claude_ai_Google_Drive__create_file` with:
- `contentMimeType: "text/html"`
- `disableConversionToGoogleType: true`
- `textContent: <full HTML string>`

This preserves CSS styling. Do NOT use `text/plain` (converts to unstyled Google Doc).
