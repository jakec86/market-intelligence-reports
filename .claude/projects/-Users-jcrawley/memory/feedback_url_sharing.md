---
name: feedback-url-sharing
description: "Claude Code terminal doesn't render markdown hyperlinks — always give raw URLs in code blocks"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2346e834-37d0-461f-ac6e-4c1cb80fc197
---

Never use markdown hyperlink syntax `[text](url)` when sharing URLs — it doesn't render as clickable in the Claude Code terminal. Always provide raw URLs inside a code block so the user can copy them easily. For local actions, suggest `! open "url"` so it opens in the browser directly from the prompt.

**Why:** Claude Code runs in a terminal context; markdown link rendering only works in web-based chat UIs.

**How to apply:** Any time a URL needs to be shared (Google Sheets, Docs, admin.cars.com reports, etc.), use a fenced code block with the raw URL.
