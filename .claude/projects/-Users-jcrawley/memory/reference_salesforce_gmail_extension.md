---
name: reference-salesforce-gmail-extension
description: Salesforce Gmail extension logs outbound emails to SF automatically — used for HCC4 and other client emails
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7283b1ef-19ff-4923-84dd-82f2df7755c4
---

Jake uses the **Salesforce Gmail extension** (inbox panel) to log and track outbound emails to clients directly from Gmail.

When sending client emails (e.g. HCC4 VDP Report to Brian Cunningham), the extension panel shows:
- **Related To:** account (e.g. Herb Chambers Companies)
- **People:** contact (e.g. Brian Cunningham)
- **Log on Send** toggle — enabled logs the email to SF on send
- **Email Tracking** toggle — enables open/click tracking

No manual SF action needed — as long as "Log on Send" is toggled on before sending, the email is automatically logged to the correct SF account + contact record.
