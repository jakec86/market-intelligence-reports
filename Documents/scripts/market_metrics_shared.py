#!/usr/bin/env python3
"""
Shared helpers for the weekly Marketplace Metrics (Contact Details) tracker.

Pulls admin.cars.com's "Connections & Contact Details" report (Tableau
workbook Connections13MoSummary). IMPORTANT (corrected 2026-07-17, see
project_market_metrics_weekly.md): this report exposes two DISTINCT
metrics, not one --

  - "Connections" (the report's KPI tiles / BarChart worksheet): the true
    full count, all lead types, but only available pre-aggregated by MONTH
    -- no per-record timestamp, no per-week grain, and the underlying-data
    API is permission-denied for this account.
  - "Contact Details" (the report's bottom panel: EmailContacts/
    PhoneContacts/ChatContacts/WebsiteContacts/OtherContacts worksheets):
    leads with actual recorded contact info/message content -- a narrower
    subset of Connections, but the ONLY place with real per-lead
    Submitted Date/Time timestamps, so the only metric this tracker can
    honestly report at weekly grain. Confirmed via cross-check against the
    report's own BarChart: e.g. one store's true July Web Transfer count
    was 81 (BarChart) vs 5 (WebsiteContacts) for the same window -- do not
    try to reconcile these or treat Contact Details as a stand-in for
    total Connections. Track and label it as Contact Details, honestly.

Extraction mechanism (verified working 2026-07-17): the report exposes
real Tableau PARAMETERS -- FromDate, ToDate, and "Lead Group Choice 2"
(single-select, values: Email Lead / Phone Lead / Chat Lead / Web Transfer /
Other (map view, vdp print) -- no "All" option exists). Setting
FromDate/ToDate genuinely constrains the window; setting "Lead Group Choice
2" switches which of the 5 per-type worksheets populates (confirmed: e.g.
setting it to "Phone Lead" makes PhoneContacts non-empty and the other 4
empty). Loop the 5 values once per store with a WIDE FromDate/ToDate window
(FIRST_WEEK_START through today), pull each type's full per-record
Submitted Date/Time list in one pass, then bucket into Mon-Sun weeks in
Python -- 5 parameter switches per store, not 5-per-week.

PII (Name/Email/phone/etc.) lives on the same worksheet rows but is never
requested here -- the JS extraction snippet below filters each worksheet
down to its Submitted Date/Time column index before returning from
evaluate(), so no PII field ever crosses back into Python.
"""

import json
import os
from datetime import datetime, timedelta

UUID_CACHE_PATH = os.path.expanduser("~/.claude/market_metrics_uuid_cache.json")

TRACKING_SHEET_ID = "1oNeDOhANTwpiku6lEF8oNUpnu-kOmrYJb-YmUrXPatw"
SOURCE_TAB = "Sheet1"
METRICS_TAB = "Weekly Contact Details"

CONNECTION_TYPES = ["Email", "Phone", "Chat", "Website", "Other"]  # fixed column order

# Clean type label -> the report's own "Lead Group Choice 2" parameter value
TYPE_PARAM_VALUES = {
    "Email": "Email Lead",
    "Phone": "Phone Lead",
    "Chat": "Chat Lead",
    "Website": "Web Transfer",
    "Other": "Other (map view, vdp print)",
}

# Clean type label -> the worksheet that populates when its param value is active
TYPE_WORKSHEETS = {
    "Email": "EmailContacts",
    "Phone": "PhoneContacts",
    "Chat": "ChatContacts",
    "Website": "WebsiteContacts",
    "Other": "OtherContacts",
}

METRICS_HEADER = (
    ["CCID", "Store Name", "Week Start", "Week End", "Total Contact Details"]
    + CONNECTION_TYPES
    + ["Partial Week?"]
)


def build_extract_js(from_date_iso, to_date_iso):
    """JS run inside the admin.cars.com page (Playwright page.evaluate /
    chrome-devtools evaluate_script) once the report's tableau-viz has
    loaded. Sets FromDate/ToDate once, then cycles the 5 Lead Group Choice 2
    values, pulling each type's Submitted Date/Time column after its
    matching worksheet populates."""
    type_param_json = json.dumps(TYPE_PARAM_VALUES)
    type_ws_json = json.dumps(TYPE_WORKSHEETS)
    return """
async () => {
  const typeParams = %s;
  const typeWorksheets = %s;
  const viz = document.querySelector('tableau-viz');
  if (!viz) return { error: 'no tableau-viz element' };

  let wb = null;
  for (let i = 0; i < 20; i++) {
    try {
      const candidate = viz.workbook;
      if (candidate && candidate.activeSheet && candidate.activeSheet.worksheets && candidate.activeSheet.worksheets.length) {
        wb = candidate;
        break;
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 1000));
  }
  if (!wb) return { error: 'timed out waiting for workbook' };

  try {
    await wb.changeParameterValueAsync('FromDate', %s);
    await wb.changeParameterValueAsync('ToDate', %s);
    await new Promise(r => setTimeout(r, 1500));
  } catch (e) {
    return { error: `failed to set date parameters: ${e}` };
  }

  const out = {};
  for (const [type, paramValue] of Object.entries(typeParams)) {
    try {
      await wb.changeParameterValueAsync('Lead Group Choice 2', paramValue);
      await new Promise(r => setTimeout(r, 1500));
      const wsName = typeWorksheets[type];
      const ws = wb.activeSheet.worksheets.find(w => w.name === wsName);
      if (!ws) return { error: `worksheet not found: ${wsName}` };
      const dt = await ws.getSummaryDataAsync({maxRows: 20000, ignoreSelection: true});
      const idx = dt.columns.findIndex(c => c.fieldName === 'Submitted Date/Time');
      out[type] = idx === -1 ? [] : dt.data.map(row => row[idx].value);
    } catch (e) {
      return { error: `extraction failed for type ${type}: ${e}` };
    }
  }
  return { ready: true, timestamps_by_type: out };
}
""" % (type_param_json, type_ws_json, json.dumps(from_date_iso), json.dumps(to_date_iso))


def load_uuid_cache():
    with open(UUID_CACHE_PATH) as f:
        return json.load(f)


def save_uuid_cache(cache):
    with open(UUID_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def report_url(uuid):
    return f"https://admin.cars.com/dealers/{uuid}/reports/connections_contact_details"


def uuid_lookup_url(ccid):
    return f"https://admin.cars.com/dealers/all/reports?query={ccid}"


def week_bounds(anchor_date, week_start=None):
    """Return (week_start, week_end) as date objects for the Mon-Sun week
    containing anchor_date, or for the week containing week_start if given."""
    d = week_start or anchor_date
    start = d - timedelta(days=d.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end


def iter_weeks(first_week_start, today):
    """Yield (week_start, week_end) for every Mon-Sun week from
    first_week_start through the week containing `today`, inclusive."""
    start, _ = week_bounds(first_week_start)
    while start <= today:
        end = start + timedelta(days=6)
        yield start, end
        start = end + timedelta(days=1)


def bucket_weekly_counts(timestamps_by_type, first_week_start, today):
    """timestamps_by_type: dict of {connection_type: ['YYYY-MM-DD HH:MM:SS', ...]}
    for one store, keys matching CONNECTION_TYPES.
    Returns list of dicts: week_start, week_end, total_contact_details,
    partial_week, and one count per CONNECTION_TYPES entry."""
    parsed_by_type = {
        t: [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").date() for ts in ts_list]
        for t, ts_list in timestamps_by_type.items()
    }
    out = []
    for start, end in iter_weeks(first_week_start, today):
        partial = today < end
        by_type_counts = {
            t: sum(1 for d in parsed_by_type.get(t, []) if start <= d <= end)
            for t in CONNECTION_TYPES
        }
        row = {
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "total_contact_details": sum(by_type_counts.values()),
            "partial_week": partial,
        }
        row.update(by_type_counts)
        out.append(row)
    return out
