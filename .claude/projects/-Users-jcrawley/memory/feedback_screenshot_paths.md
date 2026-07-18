---
name: Screenshot Save Paths
description: Always use explicit paths when saving Playwright/Chrome DevTools screenshots — default dumps to ~ and creates clutter
type: feedback
originSessionId: d3bf650a-7583-410d-9f5a-71c01b71b16e
---
Always specify a full path when taking screenshots with Playwright or Chrome DevTools MCP tools. The default save location is `~` (home directory), which is what caused 230+ loose PNGs to accumulate across sessions.

**Why:** Cleaned up ~230 orphaned PNGs from `~` and `~/Desktop` on 2026-04-14. All were from past Playwright `take_screenshot` calls that used the default path.

**How to apply:** Every `take_screenshot` or similar call must use an explicit path like `~/Documents/Reference/screenshots/<project>/step_name.png`. Create the project subfolder if it doesn't exist. At the end of any session that used screenshots, verify no loose files landed in `~` or `~/Desktop`.
