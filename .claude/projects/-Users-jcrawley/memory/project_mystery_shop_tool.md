---
name: mystery-shop-tool
description: "Cars.com Mystery Shop Evaluation tool — location, live URL, benchmark sourcing"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4f958b03-7d81-432b-a08a-219026e217a7
---

Cars.com Mystery Shop Evaluation Tool — single-file React app (no build step) for scoring dealer lead-response quality on a 100-pt rubric with PDF export.

- **Source:** `~/Documents/mystery-shop/` — its own git repo, remote `github.com/jakec86/mystery-shop` (Jake's **personal** GitHub), branch `main`.
- **Live site:** https://jakec86.github.io/mystery-shop/ (GitHub Pages from `main` root; push to `main` = deploy). Publicly accessible.
- **Benchmark data** lives in the `BENCHMARKS` object (`index.html` ~line 393) + coaching insights in `estimateImpact()` (~line 366). Sourced from **Pied Piper PSI Internet Lead Effectiveness** annual study. As of 2026-06: National avg **71**, top brand **Infiniti 82** (2026 PSI study); plus a "Turbo Speed" insight from Pied Piper's 2026 **Dealer Group** ILE study (phone AND text/email answered within 15 min — industry avg 31%, top groups 80%+).
- No customer PII in the code: shop data is browser `localStorage` only, never committed.
- **2026-06-17 decision:** keep it on personal `jakec86`, NOT moved to `carsdotcom` org. If revisited, the blocker is SSO-authorizing the work PAT (`jcrawley-cp`) for the `carsdotcom` org.
