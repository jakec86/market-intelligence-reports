/**
 * PB Report Link Tracker — Google Apps Script Web App (multi-report router)
 * Emails jcrawley@cars.com when a shared report link is opened, then redirects
 * the visitor to the live Sheet.
 *
 * WHY A WEB APP (not an onOpen trigger):
 *   Apps Script onOpen does NOT fire for view-only users and cannot see the
 *   identity of anyone outside the cars.com Workspace. A redirect web app is the
 *   only reliable way to be notified when an EXTERNAL person opens a report.
 *
 * HOW "OUTSIDE THE ORG" IS SATISFIED:
 *   You keep using the raw Sheet URLs yourself and only ever hand out the tracked
 *   link (…/exec?report=<key>&r=<recipient>). So every notification = an outside open.
 *
 * ONE WEB APP, MANY REPORTS:
 *   ?report=<key>  selects which sheet (see REPORTS below)
 *   ?r=<recipient> is the per-person token you assign when you build the link
 *
 *   …/exec?report=dyer&r=marielle
 *   …/exec?report=nalley&r=grayson_caudill
 *   …/exec?report=hendrick&r=anne_lewis
 *
 * DEPLOY (via clasp): see ~/Documents/scripts/pb_link_tracker/DEPLOY.md
 */

const NOTIFY_TO    = 'jcrawley@cars.com';
const LOG_SHEET_ID = '';   // optional: a Spreadsheet ID to append a row per open; '' = skip

// Short key → { url, name }.  Add a new line here to track another report.
const REPORTS = {
  dyer: {
    // Recurring PB pipeline sheet (pb_dealers.py "dyer"). The one-time Inventory
    // Engagement Report 1ntpeO3gy5… is a separate, retired artifact.
    url:  'https://docs.google.com/spreadsheets/d/1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8/edit?gid=565895707#gid=565895707',
    name: 'Dyer & Dyer Volvo — Price Badge Report',
  },
  nalley: {
    url:  'https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8/edit?gid=565895707#gid=565895707',
    name: 'Nalley Lexus Galleria — Price Badge Report',
  },
  hendrick: {
    url:  'https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707',
    name: 'Hendrick Automotive — Price Badge Report',
  },
  // ── Herb Chambers GM monthly touchpoint (6 stores) — added 2026-06-15 ──
  hc_seekonk_honda: {
    url:  'https://docs.google.com/spreadsheets/d/12B1r6uvZ7B9nuFTBcqUIgyhxXNbQv4jyIiOpYzhQh8w/edit?gid=565895707#gid=565895707',
    name: 'Herb Chambers Honda of Seekonk — Price Badge Report',
  },
  hc_boston_bmwmini: {
    url:  'https://docs.google.com/spreadsheets/d/1bHQG0Ceb6NEkLBOOgN3L1EhbazuO6i5hsvgZWqPdPLI/edit?gid=565895707#gid=565895707',
    name: 'Herb Chambers BMW MINI of Boston — Price Badge Report',
  },
  hc_boston_jlr: {
    url:  'https://docs.google.com/spreadsheets/d/1l3C0s3oC94fT_a_OqvbWtKT_kGt1tZA0oQnJUq0qnu0/edit?gid=565895707#gid=565895707',
    name: 'Jaguar Land Rover Boston — Price Badge Report',
  },
  hc_exotics: {
    url:  'https://docs.google.com/spreadsheets/d/13B2_DcZPoeFg1sNEMVBRFikV-ouXuQwnKlwhqlsiIo8/edit?gid=565895707#gid=565895707',
    name: 'Herb Chambers Exotics — Price Badge Report',
  },
  hc_medford_bmw: {
    url:  'https://docs.google.com/spreadsheets/d/1sy_nWQNy1DGMZRPu2P9lXtvekAfgbLnNFOwVkhqg2Pk/edit?gid=565895707#gid=565895707',
    name: 'BMW of Medford — Price Badge Report',
  },
  hc_porsche: {
    url:  'https://docs.google.com/spreadsheets/d/1-u7DO9PvJuSyQK7cpjhBIEZt16dgNyGWG_km-Y4KbbQ/edit?gid=565895707#gid=565895707',
    name: 'Herb Chambers Porsche — Price Badge Report',
  },
};
const DEFAULT_REPORT = 'dyer';

/**
 * Run this ONCE from the Apps Script editor (Run ▸ authorizeScopes) right after
 * the first `clasp push`. It forces Google's OAuth consent for the scopes the
 * web app needs (send mail + sheets). clasp itself never triggers that consent,
 * so without this step the deployed /exec link can't send you notifications.
 */
function authorizeScopes() {
  MailApp.getRemainingDailyQuota();   // triggers script.send_mail consent
  Logger.log('Authorized — the /exec web app is ready to notify on opens.');
}

function doGet(e) {
  const params    = (e && e.parameter) || {};
  const key       = REPORTS[params.report] ? params.report : DEFAULT_REPORT;
  const report    = REPORTS[key];
  const recipient = params.r || 'unknown';

  // STAGE 1 — landing page, NO email.
  // Email security scanners (SafeLinks/Mimecast/Gmail preview) fetch URLs but do
  // not click buttons, so firing only on the button click filters out false opens.
  if (params.open !== '1') {
    // ONE click → opens the Sheet directly (target="_top", guaranteed) AND fires
    // the open-ping via a keepalive fetch so the notification still sends as the
    // page navigates away. Auto top-navigation from the sandbox iframe is blocked
    // by the browser, so we DON'T rely on a server-side redirect.
    // Scanner-safe: SafeLinks/Mimecast fetch the bare link (this page) but never
    // click the button, so no ping fires and no false "open" is recorded.
    const exec  = ScriptApp.getService().getUrl();
    const ping  = exec + '?open=1&report=' + encodeURIComponent(key) + '&r=' + encodeURIComponent(recipient);
    const sheet = report.url;
    return HtmlService.createHtmlOutput(
      '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<title>' + report.name + '</title>' +
      '<style>body{font-family:Arial,Helvetica,sans-serif;color:#212121;max-width:520px;margin:14% auto;text-align:center}' +
      '.btn{display:inline-block;background:#6B2D8B;color:#fff;text-decoration:none;padding:14px 30px;border-radius:6px;font-size:16px;margin-top:20px}</style>' +
      '</head><body><h2>' + report.name + '</h2>' +
      '<p>Your latest report is ready to view.</p>' +
      '<a class="btn" target="_top" href="' + sheet + '" ' +
        "onclick=\"try{fetch('" + ping + "',{mode:'no-cors',keepalive:true});}catch(e){}\">Open the Report &rarr;</a>" +
      '</body></html>'
    );
  }

  // STAGE 2 — human clicked "Open": notify + log + redirect.
  const when = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "EEE MMM d, yyyy 'at' h:mm a z");

  try {
    MailApp.sendEmail({
      to: NOTIFY_TO,
      subject: 'Report opened — ' + report.name + ' — ' + recipient,
      htmlBody:
        '<p><b>' + report.name + '</b> was just opened.</p>' +
        '<table cellpadding="4" style="font-family:Arial,sans-serif;font-size:14px">' +
        '<tr><td><b>Recipient tag</b></td><td>' + recipient + '</td></tr>' +
        '<tr><td><b>Report</b></td><td>' + report.name + '</td></tr>' +
        '<tr><td><b>When</b></td><td>' + when + '</td></tr>' +
        '</table>' +
        '<p style="color:#888;font-size:12px">Anyone with this tracked link is outside cars.com (you use the raw Sheet URL yourself). ' +
        'Google does not expose the visitor’s IP or identity, so the recipient tag is the per-person token you assigned to the link.</p>'
    });
  } catch (err) { /* never block the redirect on a mail error */ }

  if (LOG_SHEET_ID) {
    try {
      SpreadsheetApp.openById(LOG_SHEET_ID).getSheets()[0].appendRow([new Date(), key, recipient, report.name]);
    } catch (err) {}
  }

  return HtmlService.createHtmlOutput(
    '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<style>body{font-family:Arial,Helvetica,sans-serif;color:#212121;max-width:520px;margin:14% auto;text-align:center}' +
    '.btn{display:inline-block;background:#6B2D8B;color:#fff;text-decoration:none;padding:14px 30px;border-radius:6px;font-size:16px;margin-top:16px}</style>' +
    '</head><body>' +
    '<script>try{window.top.location.href=' + JSON.stringify(report.url) + ';}catch(e){}</script>' +
    '<h3>Opening your report&hellip;</h3>' +
    '<p>If it doesn’t open automatically:</p>' +
    '<a class="btn" target="_top" href="' + report.url + '">Open the Report &rarr;</a>' +
    '</body></html>'
  );
}
