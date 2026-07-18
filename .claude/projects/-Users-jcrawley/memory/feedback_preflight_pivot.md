---
name: Pre-flight — Pivot to Playwright Instead of Aborting
description: When MCP tools (Tableau, Gmail) fail pre-flight checks, pivot to Playwright rather than aborting the workflow
type: feedback
originSessionId: a2cbd7ca-d3ed-4089-929c-88217665094f
---
Do NOT abort the PB report workflow when Tableau MCP returns 401 or Gmail MCP disconnects. Instead, pivot to Playwright for the affected step.

**Why:** Playwright can handle both Tableau (LEI download) and Gmail (draft creation via web UI) directly. Aborting wastes the session when a working alternative exists.

**How to apply:** 
- Tableau 401 → proceed with Playwright for LEI crosstab download (already the primary method for Step 1)
- Gmail MCP down → use Playwright to open Gmail and compose/save draft, or wait for reconnect at Step 4
- Still abort for Playwright itself being unavailable (no fallback exists)
