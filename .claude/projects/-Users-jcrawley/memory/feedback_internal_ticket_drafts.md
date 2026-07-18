---
name: feedback_internal_ticket_drafts
description: Internal tickets and BI requests go in chat as plain/markdown text for copy-paste into Atlassian — not as Gmail drafts
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6f48af2-1d47-4da6-8692-7732f1724976
---

When the user asks to draft a message for an internal team (BI, product, eng, etc.) or explicitly says it will be pasted into an Atlassian ticket (Jira/Confluence), do NOT create a Gmail draft. Output the content directly in chat in clean markdown.

**Why:** Internal comms go into Atlassian tickets, not email. A Gmail draft is the wrong artifact and wastes a step.

**How to apply:** If the request is clearly internal (BI team, eng team, product team, Jira bug report, Confluence page) or the user says "copy/paste into ticket," output the content as a clean markdown block in chat. Only use Gmail draft for external client-facing messages.
