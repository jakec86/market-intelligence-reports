---
name: reference_dr_admin_form
description: DealerRater admin portal — correct form submission pattern for adding/editing employees (discovered 2026-05-15)
metadata: 
  node_type: memory
  type: reference
  originSessionId: d036cb08-7c00-4c8d-935d-25fc1bae66f0
---

## DealerRater Admin Employee Form — Submission Pattern

**Admin URL pattern:** `https://www.dealerrater.com/dp/{DR_ID}/profile/employees`
**New employee form:** `https://www.dealerrater.com/dp/{DR_ID}/profile/employees/0`

### Correct fill + submit sequence

1. Use **Playwright native** fill methods — never JS `element.value = x` (bypasses framework change events, leaves form fields invalid on submit):
   - `browser_type` for text inputs: `#FirstName`, `#LastName`, `#Email`, `#Position`
   - `browser_select_option` for `#Department` (triggers select change event properly)

2. Department value mapping:
   - Sales titles → `Sales`
   - Service Advisor / BDC → `Service`
   - GM / Sales Manager / Finance Manager → `Management`

3. Submit via `browser_evaluate`:
   ```javascript
   () => {
     document.querySelector('label[for="userRoleNone"]').click();
     historicAccountPrompt();
     return 'submitted';
   }
   ```
   - `historicAccountPrompt()` POSTs to `/json/dealeremployees/verifyrecoverableprofile?DealerId={DR_ID}&EmailAddress={email}`
   - If email is new (no existing DR account), calls `SaveEmployee()` → jQuery Validate → form submit
   - Do NOT click the save button directly (jQuery handler works but form state may be incomplete)

4. **Success indicator:** page redirects to `/dp/{DR_ID}/profile/employees?showSaved=True`

### Delete pattern

```javascript
// Selector confirmed working 2026-05-15
document.querySelector('a.hidden-xs[href="javascript: DeleteEmployee();"]').click()
// If strict mode violation (multiple matches), use querySelectorAll and find by row context
```

### Important: do not remove these accounts

- Cars Commerce admin accounts (e.g., `jacobm@atlanticcoastautomotive.com`, any `@carscommerce.inc`)
- Any account with ADMINISTRATOR role visible in the admin UI — confirm with user first

### Auth

METAL SSO = Cars Commerce Google SSO (`@cars.com` or `@carscommerce.inc` account). Same Google account used for Gmail/Tableau portal.
