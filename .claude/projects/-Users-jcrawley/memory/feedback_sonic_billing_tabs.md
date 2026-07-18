---
name: Sonic & Hendrick Billing — Hide Source Tabs
description: After building the Overview pivot, hide all source data sheets so only Overview is visible
type: feedback
originSessionId: 03d05f28-537c-427b-8ddd-843e4a0e41e1
---
In the processed billing Excel output, hide all source sheets (Cars.com, eCarOne, etc.) so only the **Overview** tab is visible by default.

**Why:** Cleaner deliverable — recipients see the pivot summary immediately without extra tabs cluttering the view.

**How to apply:** In the `build_overview` step, after saving the workbook, iterate all non-Overview sheets and set `ws.sheet_state = 'hidden'` before calling `wb.save()`.
