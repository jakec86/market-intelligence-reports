---
name: Sonic — Known Duplicate Admin CCIDs
description: CCIDs that look like new Sonic stores in Tableau AE Insights but are actually duplicate admin records for existing Sonic rooftops. Don't add to brand map.
type: reference
originSessionId: 4adc8f83-50db-468a-b0c1-eed587d83946
---
When cross-referencing Tableau AE Insights (parent=Sonic Automotive Group) vs the `/sonic-monthly-report` brand map, some CCIDs appear as "new Sonic stores" but are actually duplicate admin records for existing rooftops. Skip these:

| Duplicate CCID | Real store (keep this) | Real CCID | Confirmed |
|---|---|---|---|
| 6037235 | BMW Mini of Birmingham | 182765 | 2026-04-22 |

If Market Comparison returns 0 rows for a CCID that AE Insights attributes to Sonic, suspect duplicate first before adding to brand map.
