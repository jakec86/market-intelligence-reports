---
name: sheet-sharing-confirm
description: "Never auto-share a new Sheet/Doc with a colleague (even internal) without asking each time, regardless of earlier verification-scope approval"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 45f5ce84-91b4-4396-b164-642a69e19ce9
---

Do not call share_spreadsheet (or any Drive/Sheets sharing action) on a newly created tracking document without asking first, even when an earlier approved plan step said "create/share the tracking sheet."

**Why:** During the ACA ReviewBuilder automation build (2026-07-16), Jake had approved "go all the way through verification, including creating/sharing the tracking sheet" as part of a broader plan. When it came time to actually share the new Engagement Tracking sheet with Danielle McJunkins (internal AE, not external), Jake rejected the tool call and said to keep it private for now. A prior plan-level approval for "sharing" as a category doesn't cover the specific act of granting a specific person access to a specific document — that's still a "visible to others / affects shared state" action per the risk-executing-actions guidance, and deserves its own confirmation at the moment it actually happens.

**How to apply:** Treat "share this with X" as its own checkpoint every time, separate from whatever broader plan step it was nested under — ask "should I share [doc] with [person] now?" immediately before the share call, even if the plan already said sharing would happen eventually. Default to keeping new tracking artifacts private to the user (jcrawley) until they explicitly say to share. See [[project_pb_link_tracker]] and the ACA ReviewBuilder automation project for related context.
