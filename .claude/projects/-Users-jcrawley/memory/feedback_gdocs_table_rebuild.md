---
name: feedback-gdocs-table-rebuild
description: How to rebuild a Google Doc from scratch with real tables using the Docs REST API — the correct approach and the formulas for table index calculation
metadata:
  type: feedback
---

## Rule
When rebuilding a Google Doc with proper tables via the Docs REST API, use the **sequential insert + reverse-order table fill** approach. Never use cumulative index shifting — lower-index positions are unaffected by insertions at higher positions.

**Why:** Past attempt used cumulative shift calculation that incorrectly shifted lower markers when replacing higher ones, corrupting the document. HTML upload via Drive MCP converts to `text/html` file, NOT a Google Doc — does not render as Docs format.

## How to Apply

**Step 1 — Auth:** Use `docs_token.json` + `GOOGLE_CLIENT_ID/SECRET` from settings.json → `documents` scope for Docs API.

**Step 2 — Delete all content:**
```python
batch([{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": doc_end - 1}}}])
```

**Step 3 — Insert all text with ##MARKER## placeholders** where tables will go.

**Step 4 — Find marker positions** by scanning doc `body.content` paragraph elements.

**Step 5 — Replace markers with tables, BOTTOM TO TOP** (highest index first):
- For each marker: delete marker text, insertTable at that position, fill cells
- No cumulative shift needed — lower markers are unaffected by higher-index insertions

**Step 6 — Fill cells using the verified formula:**
```python
def para_idx(insert_idx, r, c, C):
    """Paragraph startIndex for cell(r,c) in a table inserted at location.index=insert_idx"""
    return insert_idx + 4 + r*(1 + C*2) + c*2
```
- `insert_idx` = the `location.index` passed to `insertTable`
- Fill cells BOTTOM-RIGHT to TOP-LEFT within each table (in the same batch)
- Verified empirically with 3x5 table at position 1034

**Step 7 — Style** with `updateTextStyle` and `updateParagraphStyle` in one final batchUpdate.

## Cars Commerce Style Constants (Google Docs API)
```python
PURPLE    = {"rgbColor": {"red":0.420,"green":0.176,"blue":0.545}}  # #6B2D8B
TEAL      = {"rgbColor": {"red":0.000,"green":0.659,"blue":0.557}}  # #00A88E
DARK_GRAY = {"rgbColor": {"red":0.302,"green":0.302,"blue":0.302}}
LIGHT_PURPLE_BG = {"rgbColor": {"red":0.953,"green":0.933,"blue":0.976}}  # H2 backgrounds
FONT = {"fontFamily": "Poppins", "weight": 400}
TABLE_HEADER_BG = PURPLE  # White text on purple header rows
ALT_ROW = {"rgbColor": {"red":0.980,"green":0.976,"blue":0.988}}  # alternating rows
```

## Why HTML Upload Doesn't Work
`mcp__claude_ai_Google_Drive__create_file` with `contentMimeType: text/html` returns `mimeType: text/html` — it does NOT convert to Google Doc format. Only `text/plain` auto-converts. For HTML → Google Doc, use Drive REST API v3 multipart upload with a token that has `drive` scope (not just `documents` scope). The local Drive token has `drive.readonly` only.

## For Future Builds
The `docs_token.json` has `documents` scope (edit existing docs). Creating NEW docs from HTML requires a `drive` write-scope token. Either: use the claude.ai Google Drive MCP `create_file` tool, OR add `drive` scope to the OAuth flow and save a new token.
