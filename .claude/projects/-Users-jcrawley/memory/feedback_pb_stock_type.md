---
name: PB Report — Stock Type = Used Only
description: Hendrick and Nalley Price Badge reports must use "Used" stock type only — Cars.com does not provide Price Badging on New inventory
type: feedback
originSessionId: 1c9763c3-f674-4172-bbda-b16a9cd87d15
---
Always filter Stock type to **Used** only in the Tableau LEI view when running PB reports. Do not select All, New, or CPO.

**Why:** Cars.com Price Badging only applies to Used inventory. Including New or CPO vehicles inflates the denominator and makes the badge stats meaningless.

**How to apply:** In Step 1 of any PB report workflow, after setting DMA and Maj dealer filters, confirm Stock type = "Used" (the Tableau default). If it was changed to "All" in a prior step, revert it before downloading the crosstab.
