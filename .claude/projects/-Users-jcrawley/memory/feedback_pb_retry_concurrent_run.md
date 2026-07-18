---
name: feedback_pb_retry_concurrent_run
description: "PB manual retry can collide with the scheduled Cowork run — check for sibling-dealer sends, not just this dealer's email"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 64f17948-4b17-49cf-b667-5701b00f6ed4
---

On a manual PB report retry (e.g. /hendricks-pb-report "retry attempt 2 of 3"), the initial "already sent today?" Gmail check can correctly return zero, yet the scheduled Cowork/automated run then fires *during* the retry and sends its own copy — producing a duplicate. On 2026-06-29 this caused two identical Hendrick PB emails to jcrawley@cars.com (07:32:34 = automated, 07:32:38 = my script), 4s apart. The tell was a Nalley PB send to real recipients at 07:32:01 that my session never initiated.

**Why:** The retry's dedup check only looks for *this* dealer's email at *session start*; the scheduled run is a separate process that can start mid-retry. Pre-send rule meant both Hendrick copies went only to Jake (no client double-send), so harm was contained.

**How to apply:** Before running a PB retry during a scheduled window, also look for sibling-dealer sends today (Nalley/Hendrick/Dyer) as evidence the automated batch is concurrently running. If it is, prefer to stop and let the scheduled run complete rather than running manually. Do NOT also mark the Google Task / log Salesforce on a retry when the automated run is active — it duplicates the activity record. See [[project_pb_report_production]] and [[project_pb_headless_oauth_401]].
