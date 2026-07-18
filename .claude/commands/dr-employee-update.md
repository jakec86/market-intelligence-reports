# DealerRater Employee Profile Update (Ad-Hoc)

Perform a DealerRater employee roster update for a single dealer based on a client-provided staff list (email, spreadsheet, or verbal). Handles removes, adds, and title changes via the DR admin portal.

---

## Overview

Used when a client contact (AE, GM, or dealer rep) sends a staff list and asks for DealerRater employee profiles to be updated. This is distinct from the Herb Chambers quarterly audit (which scrapes dealer websites). Here the source of truth is always the client-provided list.

**Report folder:** `~/Documents/Reports/{DealerName}/`
- Create folder if it doesn't exist
- Save a `dr_update_report.md` before making any changes

---

## Browser Tool — Chrome DevTools MCP (preferred) vs. Playwright (fallback)

**Prefer Chrome DevTools MCP** (`mcp__chrome-devtools__*`) because:
- Your regular Chrome session is already authenticated via METAL SSO — no login flow needed
- Works within existing tabs without opening a new browser context

**Fall back to Playwright MCP** (`mcp__playwright__*`) if:
- Chrome DevTools MCP is unavailable or disconnected
- Form fill / select interactions fail to trigger framework events (see Gotchas)
- A fresh browser context is needed for any reason

**Tool name mapping:**

| Action | Chrome DevTools MCP | Playwright MCP (fallback) |
|---|---|---|
| Navigate | `mcp__chrome-devtools__navigate_page` | `mcp__playwright__browser_navigate` |
| Type into field | `mcp__chrome-devtools__fill` | `mcp__playwright__browser_type` |
| Select option | `mcp__chrome-devtools__evaluate_script` (see note) | `mcp__playwright__browser_select_option` |
| Run JS | `mcp__chrome-devtools__evaluate_script` | `mcp__playwright__browser_evaluate` |
| Screenshot | `mcp__chrome-devtools__take_screenshot` | `mcp__playwright__browser_take_screenshot` |
| Click | `mcp__chrome-devtools__click` | `mcp__playwright__browser_click` |

> **Note on select with Chrome DevTools MCP:** `fill` doesn't reliably trigger framework change events on `<select>` elements. Use `evaluate_script` with a dispatched `change` event instead:
> ```javascript
> const el = document.querySelector('#Department');
> el.value = 'Sales';
> el.dispatchEvent(new Event('change', { bubbles: true }));
> ```
> If this still fails (title field or department stays blank on submit), fall back to Playwright `browser_select_option` for that step only.

---

## Pre-flight

1. Confirm Gmail MCP is connected — needed to find the client email if not already in hand
2. Check Chrome DevTools MCP: call `mcp__chrome-devtools__list_pages`
   - **If it returns pages:** Chrome DevTools MCP is working — proceed with it
   - **If it errors "browser is already running":** stale browser lock in `~/.cache/chrome-devtools-mcp/` — this is a session-level issue. Fall back to Playwright; do not attempt to fix mid-workflow
   - **If Playwright is the fallback:** confirm it's connected before proceeding
3. DR admin requires **METAL SSO** — verify `dealerrater.com/dp/` is already open and logged in
   - If using Chrome DevTools MCP: SSO is already active in your running Chrome session
   - If using Playwright: navigate to `dealerrater.com/dp/` and complete Google SSO (one-time per Playwright session)

---

## Step 1 — Get the Staff List

**If the user says "most recent email from [contact]":**
- Search Gmail for the contact's name/email to find the thread
- Extract the full staff list (names, titles, emails if provided)

**If the user provides the list directly:**
- Use as-is

---

## Step 2 — Look Up the Dealer's DR ID

Check in order:
1. Memory / prior reports (e.g., `~/Documents/Reports/{DealerName}/`)
2. Salesforce: `sf data query --query "SELECT Id, Name, CCID__c, DealerRater_ID__c FROM Account WHERE Name LIKE '%{name}%'" --target-org cars-commerce`
3. DR public search: `https://www.dealerrater.com/dealer/{dealer-name-slug}/`

Note the DR ID — it's the number in the admin URL: `https://www.dealerrater.com/dp/{DR_ID}/profile/employees`

---

## Step 3 — Scrape Current DR Roster

DR employee pages are JS-rendered. Navigate to the admin page and evaluate:

```javascript
// Chrome DevTools MCP
mcp__chrome-devtools__navigate_page: https://www.dealerrater.com/dp/{DR_ID}/profile/employees

mcp__chrome-devtools__evaluate_script: () => {
  return Array.from(document.querySelectorAll('.employee-row, .staff-row, tr[data-employee]'))
    .map(r => ({
      name: r.querySelector('.employee-name, .name')?.innerText?.trim(),
      title: r.querySelector('.employee-title, .position')?.innerText?.trim(),
      email: r.querySelector('.employee-email, .email')?.innerText?.trim()
    }));
}
```

If selectors don't return results, take a screenshot and inspect the DOM.

**Known admin employee row pattern (confirmed 2026-05-15):**
- Employee rows visible in admin at `/dp/{DR_ID}/profile/employees`
- Delete link selector: `a.hidden-xs[href="javascript: DeleteEmployee();"]`
- Each row shows name, title, email

---

## Step 4 — Generate the Diff

Compare current DR roster vs. client-provided target list:

- **TO REMOVE:** On DR but NOT on client list (by last name fuzzy match)
- **TO ADD:** On client list but NOT on DR
- **TITLE UPDATES:** Same person (name match), different title

**Do NOT remove:**
- Cars Commerce admin accounts (e.g., `jacobm@atlanticcoastautomotive.com`, `@carscommerce.inc` emails)
- Any account with ADMINISTRATOR role — confirm with user before touching
- Entries where name match is ambiguous — flag and ask

Save the diff to `~/Documents/Reports/{DealerName}/dr_update_report.md` before proceeding:

```markdown
# {Dealer Name} — DealerRater Employee Update
**Date:** {date}
**DR ID:** {id}
**CCID:** {ccid}
**Source:** {email/contact name}

## Current DR Roster
| Name | Title |
|---|---|
...

## Target Roster (from {contact})
| Name | Title |
|---|---|
...

## TO REMOVE
| Name | Reason |
...

## TO ADD
| Name | Title | Email |
...

## TITLE UPDATES
...
```

---

## Step 5 — Execute Changes on DealerRater Admin

### Removing employees

Navigate to `/dp/{DR_ID}/profile/employees`, find the row by name, and click the delete link:

```javascript
// Chrome DevTools MCP — find and click delete for a specific employee by name
mcp__chrome-devtools__evaluate_script: () => {
  const rows = document.querySelectorAll('tr');
  for (const row of rows) {
    if (row.innerText.includes('{Last Name}')) {
      row.querySelector('a.hidden-xs[href="javascript: DeleteEmployee();"]')?.click();
      return 'clicked';
    }
  }
  return 'not found';
}
```

Confirm deletion dialog if one appears (`mcp__chrome-devtools__handle_dialog`).

### Adding employees

For each employee to add:

1. Navigate to the new employee form:
   ```
   mcp__chrome-devtools__navigate_page: https://www.dealerrater.com/dp/{DR_ID}/profile/employees/0
   ```

2. Fill text fields (Chrome DevTools MCP `fill` triggers input events properly for text fields):
   ```
   mcp__chrome-devtools__fill: #FirstName → {first name}
   mcp__chrome-devtools__fill: #LastName → {last name}
   mcp__chrome-devtools__fill: #Email → {email}
   mcp__chrome-devtools__fill: #Position → {title}
   ```

3. Set the Department select with a dispatched change event:
   ```javascript
   mcp__chrome-devtools__evaluate_script: () => {
     const el = document.querySelector('#Department');
     el.value = '{Sales|Service|Management}';
     el.dispatchEvent(new Event('change', { bubbles: true }));
     return el.value;
   }
   ```

   **Department mapping:**
   | Title contains | Department value |
   |---|---|
   | Sales | `Sales` |
   | Service Advisor / BDC | `Service` |
   | General Manager / Sales Manager / Finance | `Management` |

4. Submit via JS:
   ```javascript
   mcp__chrome-devtools__evaluate_script: () => {
     document.querySelector('label[for="userRoleNone"]').click();
     historicAccountPrompt();
     return 'submitted';
   }
   ```
   > `historicAccountPrompt()` POSTs to `/json/dealeremployees/verifyrecoverableprofile`, checks for existing DR account by email, then calls `SaveEmployee()` → jQuery Validate → form submit. Do NOT click the save button directly.

5. **Success:** page redirects to `/dp/{DR_ID}/profile/employees?showSaved=True`

   > **If Department stays blank on submit:** Chrome DevTools MCP's dispatched change event may not have registered with the framework. Fall back to Playwright `browser_select_option` for the Department field only, then call `historicAccountPrompt()` via `browser_evaluate`.

### Recovering a disabled profile (previously removed employee)

If the email is already in DR's system (employee was removed before), DR shows a dialog:
> "This email address is associated with a disabled profile. Click Continue to re-enable the original profile and make edits or click Add New to create a new profile."

The dialog buttons are `<input>` elements (not `<button>`). Click **Continue** to restore the existing profile:
```javascript
Array.from(document.querySelectorAll('input')).find(el => el.value === 'Continue').click()
```

This redirects to `/dp/{DR_ID}/profile/employees/{employeeId}` (the edit page). **Important:** the recovery flow clears Position and Department — you must re-fill them on the edit page before saving.

On the edit page, the save function is `SaveEmployee()` directly (not `historicAccountPrompt()`):
```javascript
SaveEmployee()
```

**Success:** page stays at `/dp/{DR_ID}/profile/employees/{employeeId}` then redirects to `?showSaved=True`.

### Title updates

Navigate to the employee's edit page, update `#Position` and `#Department` the same way as above, then submit via `historicAccountPrompt()`.

---

## Step 6 — Verify

After all changes:
1. Navigate back to `/dp/{DR_ID}/profile/employees` and take a screenshot
2. Confirm all added employees appear, removed employees are gone
3. Check public page: `https://www.dealerrater.com/sales/{Store-Name}-Employees-{DR_ID}/`
   - Note: public page may take a few hours to reflect changes per DR banner message

---

## Step 7 — Confirm to Client

Draft a Gmail reply to the client contact confirming the updates:

```
Subject: Re: {original subject}

Hi {name},

All done! Here's a summary of what was updated on DealerRater for {store name}:

Removed (1):
- {Name}

Added (11):
- {Name} — {Title}
...

The public profile page may take a few hours to fully reflect the changes.

https://www.dealerrater.com/sales/{Store-Name}-Employees-{DR_ID}/

Let me know if anything looks off.

Jake
```

Use HTML format per email conventions. Use past-tense labels (Added / Removed, not To Add / To Remove).

---

## Known Patterns & Gotchas

- **Chrome DevTools MCP preferred but session-sensitive** — when it works, METAL SSO is already active and no login is needed. But it can fail on session start with "browser is already running for ~/.cache/chrome-devtools-mcp/chrome-profile" — this is a stale lock, not a transient error. If `list_pages` throws this, fall back to Playwright for the whole session; don't try to recover Chrome DevTools MCP mid-workflow
- **`<select>` elements need a dispatched change event** — `fill` alone won't trigger jQuery's change handler; use `evaluate_script` with `dispatchEvent(new Event('change', { bubbles: true }))`, or fall back to Playwright `browser_select_option`
- **JS value assignment (`element.value = x`) without dispatching events** — bypasses framework entirely; field appears set but form submits empty. Always dispatch or use native Playwright fill
- **`historicAccountPrompt()` is the correct submit trigger** — POSTs email check, then calls `SaveEmployee()` → jQuery Validate → form submit
- **DR admin includes Cars Commerce admin accounts** — never remove `@carscommerce.inc`, `@atlanticcoastautomotive.com`, or similar internal accounts
- **Admin-role accounts** — any ADMINISTRATOR account visible in admin UI should be confirmed before removal
- **Public page is JS-rendered** — use Chrome DevTools MCP evaluate (not WebFetch) to scrape DR employee pages when you need structured data
- **METAL SSO** = Cars Commerce Google SSO (`@cars.com` or `@carscommerce.inc`) — same login as Gmail, Tableau portal, etc.
- **Gmail MCP may drop mid-session** — note where you stopped; draft creation is idempotent (safe to re-run after reconnect)
