---
name: feedback-hendrick-filter
description: Hendrick PBT basicFilter owns sort state — never use sortRange API against it or set userEnteredFormat.backgroundColor on data rows
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ca589fff-9f98-4381-a976-02db7636b893
---

The Hendrick Price Badge Tool tab has an active basicFilter with sortSpecs that physically manages the display order: green-J rows first (where J col has conditional-format pure green from `AND(J<=threshold,J>0)`), then SAM ascending.

**Why:** Calling `sortRange` API against a sheet with basicFilter sortSpecs corrupts the `hiddenByFilter` state, hiding all data rows except a few. Similarly, setting `userEnteredFormat.backgroundColor` on rows blocks the conditional format on col J from displaying pure green `{green: 1}`, which breaks the filter's color sort.

**How to apply:**
- `safe_sort_pbt()` for Hendrick: only do Pass 1 (push empty rows to bottom via stock# sort) and Pass 2 (SAM sort). Do NOT set background colors — the CF handles green on col J automatically.
- If the filter ever gets corrupted (all rows show as hiddenByFilter): `clearBasicFilter` then `setBasicFilter` with original specs to reset.
- The filter spec to restore: range rows 2-11002 cols A-J; sortSpecs: [{dimIdx:9, DESC, bgColor:{green:1}}, {dimIdx:0, ASC}]; filterSpecs: [{colIdx:0, hiddenValues:['']}]
