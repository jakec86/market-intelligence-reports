---
name: project-pb-report-distribution
description: "How Hendrick PB report is actually used — Anne distributes to SAMs, open tracking confirms engagement"
metadata: 
  node_type: memory
  type: project
  originSessionId: ca589fff-9f98-4381-a976-02db7636b893
---

Anne Lewis (Senior Manager, Marketing Solutions) is NOT the end actor — she is the distribution hub.

**Workflow:**
Jake → Anne (1 email) → Anne forwards to SAMs → SAMs reprice vehicles → badges improve

**What this means:**
- Anne doesn't need to understand every vehicle — she needs the email to be easy to forward
- SAMs are the actors. They receive the forwarded email and filter the 4,695-row sheet to find their stores
- Open tracking is already in place so Jake/team can see the email is being opened (engagement confirmation)

**Current friction for SAMs:** Each SAM receives a 4,695-row Google Sheet and must filter to their own stores (e.g., Tyler Marovich covers Audi Northlake + BMW of McKinney + others). That's real friction.

**Highest-impact improvement identified (2026-06-05):**
Per-SAM emails instead of one group email to Anne. Each SAM gets only their vehicles — green rows at top, their stores only. Tyler Marovich sees ~40 vehicles instead of 4,695. Would require:
1. Extract unique SAMs from PBT after import
2. Build per-SAM summaries from the data already in the script
3. Email each SAM directly (Anne CC'd or kept as the single recipient with per-SAM sections)

**Confirmed (2026-06-05):** Anne's forwarding is intentional — she controls timing and message to her SAMs. Direct SAM emails would bypass her. Do NOT send directly to SAMs.

**Right improvement:** Per-SAM sections WITHIN Anne's single email. Each section has SAM name, their vehicle count, and their specific callouts. Anne forwards the whole email; SAMs find their name immediately without filtering a spreadsheet. She still controls the send and adds her own intro.

**Implementation:** Change `pb_report.py` email generation for Hendrick to group `within_threshold` vehicles by SAM, render one section per SAM in the HTML body. Data already available (SAM, store, vehicle, diff, target price all in the PBT post-sort).
