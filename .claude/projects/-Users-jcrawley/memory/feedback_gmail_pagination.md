---
name: Gmail inbox has multiple pages
description: Gmail paginates emails — always check all pages (Older button) before declaring inbox cleanup complete
type: feedback
originSessionId: 1df3510b-d41c-45e4-8b55-64c070922b46
---
Always check ALL Gmail pages when doing inbox cleanup — don't stop at the first visible page.

**Why:** During an email archive session, I only processed page 1 and missed 34+ emails on subsequent pages. Gmail paginates ~50 emails per page and the "Older" button loads more. Also, the a11y snapshot may show fewer "row" elements than actual emails — use checkbox elements to get the full count.

**How to apply:** After loading Gmail inbox, immediately check for Older/Newer buttons and page count. Process all pages before reporting completion. Use checkbox elements (not row elements) to count emails accurately.
