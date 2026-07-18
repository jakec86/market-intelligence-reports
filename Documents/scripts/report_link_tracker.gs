/**
 * Report Link Tracker — Google Apps Script Web App
 * Emails you when your shared report link is opened, then redirects to the Sheet.
 *
 * WHY A WEB APP (not an onOpen trigger):
 *   Apps Script onOpen does NOT fire for view-only users and cannot see the identity
 *   of anyone outside your Google Workspace domain. A redirect web app is the only
 *   reliable way to get notified when an external person opens the report.
 *
 * HOW "OUTSIDE THE ORG" IS SATISFIED:
 *   You keep using the raw Sheet URL yourself and only ever send the tracked link
 *   (below) to external recipients. So every notification this fires = an outside open.
 *
 * DEPLOY:
 *   1. script.google.com  ▸  New project  ▸  paste this file  ▸  Save
 *   2. Deploy ▸ New deployment ▸ select type "Web app"
 *        - Execute as:      Me (jcrawley@cars.com)
 *        - Who has access:  Anyone
 *   3. Authorize when prompted. Copy the /exec Web app URL.
 *   4. Share   <WEB_APP_URL>?r=<recipient>   instead of the raw Sheet link, e.g.
 *        https://script.google.com/macros/s/AKfy.../exec?r=marielle
 *        https://script.google.com/macros/s/AKfy.../exec?r=store_pricing_mgr
 */

const REPORT_URL   = 'https://docs.google.com/spreadsheets/d/1ntpeO3gy5-HCzIx5WqEgtBESOVIsbOU5sGI4Nls17TI/edit?gid=565895707#gid=565895707';
const NOTIFY_TO    = 'jcrawley@cars.com';
const REPORT_NAME  = 'Dyer & Dyer Volvo — Price Badge Report';
const LOG_SHEET_ID = '';   // optional: a Spreadsheet ID to append a row per open; '' = skip

function doGet(e) {
  const params    = (e && e.parameter) || {};
  const recipient = params.r || 'unknown';

  // STAGE 1 — landing page, NO email.
  // Email security scanners (SafeLinks/Mimecast/Gmail preview) fetch URLs but do not
  // click buttons, so firing only on the button click filters out most false opens.
  if (params.open !== '1') {
    const btn = '?open=1&r=' + encodeURIComponent(recipient);
    return HtmlService.createHtmlOutput(
      '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<title>' + REPORT_NAME + '</title>' +
      '<style>body{font-family:Arial,Helvetica,sans-serif;color:#212121;max-width:520px;margin:14% auto;text-align:center}' +
      '.btn{display:inline-block;background:#6B2D8B;color:#fff;text-decoration:none;padding:14px 30px;border-radius:6px;font-size:16px;margin-top:20px}</style>' +
      '</head><body><h2>' + REPORT_NAME + '</h2>' +
      '<p>Your latest report is ready to view.</p>' +
      '<a class="btn" href="' + btn + '">Open the Report &rarr;</a></body></html>'
    );
  }

  // STAGE 2 — human clicked "Open": notify + log + redirect.
  const when = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "EEE MMM d, yyyy 'at' h:mm a z");

  try {
    MailApp.sendEmail({
      to: NOTIFY_TO,
      subject: 'Report opened — ' + recipient,
      htmlBody:
        '<p><b>' + REPORT_NAME + '</b> was just opened.</p>' +
        '<table cellpadding="4" style="font-family:Arial,sans-serif;font-size:14px">' +
        '<tr><td><b>Recipient tag</b></td><td>' + recipient + '</td></tr>' +
        '<tr><td><b>When</b></td><td>' + when + '</td></tr>' +
        '</table>' +
        '<p style="color:#888;font-size:12px">Anyone with this tracked link is outside cars.com (you use the raw Sheet URL yourself). ' +
        'Google does not expose the visitor’s IP or identity, so the recipient tag is the per-person token you assigned to the link.</p>'
    });
  } catch (err) { /* never block the redirect on a mail error */ }

  if (LOG_SHEET_ID) {
    try {
      SpreadsheetApp.openById(LOG_SHEET_ID).getSheets()[0].appendRow([new Date(), recipient, REPORT_NAME]);
    } catch (err) {}
  }

  return HtmlService.createHtmlOutput(
    '<script>window.top.location.href=' + JSON.stringify(REPORT_URL) + ';</script>' +
    '<p style="font-family:Arial,sans-serif">Opening report… ' +
    'if it doesn’t load, <a target="_top" href="' + REPORT_URL + '">click here</a>.</p>'
  );
}
