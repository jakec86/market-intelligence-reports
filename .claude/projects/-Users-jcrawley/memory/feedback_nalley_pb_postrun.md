---
name: Nalley PB Report — Post-Run Manual Steps
description: Two manual steps required after pb_report.py runs for Nalley: fill column K formulas and add email recipients to draft
type: feedback
originSessionId: a2cbd7ca-d3ed-4089-929c-88217665094f
---
After `pb_report.py --dealer nalley` completes, two manual steps are needed before the draft is ready to send:

1. **Column K formulas** — Check that the "Updated Price" formula (`=G-J`) in column K of the Price Badge Tool tab is filled down for all data rows. Formulas may need to be extended after each import if new rows exceed the previous range.

2. **Email draft recipients** — The `nalley` config in `pb_report.py` has `email_to: ""` (blank). The generated draft has no recipients. Add them manually before sending:
   - **To:** Grayson Caudill `gcaudill1@nalleycars.com`, Jason E. Brown `jbrown1@nalleycars.com`, Zlatan Ibrahimbegovic `zibrahimbegovic@asburyauto.com`, Rashad Saeed `rsaeed@nalleycars.com`
   - **Cc:** Shashank Dharanendra `sdharanendra@asburyauto.com`
   - ⚠️ Do NOT use `@nalleyauto.com` — those addresses bounce. Confirmed from sent mail 2026-05-04.

**Why:** The script's nalley config was left with an empty `email_to` field; `@nalleyauto.com` guesses bounced on 2026-05-08 — correct domain is `@nalleycars.com` (primary contacts) and `@asburyauto.com` (Zlatan + Shashank).

**How to apply:** After every Nalley PB report run, remind the user to check column K fill and add recipients to the draft before sending.
