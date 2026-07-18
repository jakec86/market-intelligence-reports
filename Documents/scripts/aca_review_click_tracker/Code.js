/**
 * ACA ReviewBuilder Tone-Picker Click Tracker — Google Apps Script Web App
 *
 * Each GM email has ONE tracked link ("Preview & Choose Your Message"), not
 * one per option — reduced from 3 links to 1 deliberately: fewer external
 * links in the email body helps spam/security-gateway scoring, and
 * script.google.com/macros links in particular get extra scrutiny from
 * gateways like Mimecast since that exact URL pattern is a known
 * phishing-abuse vector (a legitimate Google domain used to host arbitrary
 * redirect/collection pages) — so cutting 3 of them down to 1 is a real,
 * not cosmetic, deliverability mitigation. That single link lands on a page
 * showing all 3 full drafts with their own "Confirm & Use This Message"
 * buttons, which is where the actual per-option selection/logging happens.
 *
 * Logging + notify: logs the selection to the "Engagements" tab of the ACA
 * ReviewBuilder Engagement Tracking sheet and notifies Jake + Danielle. A
 * separate local script (aca_review_config_writer.py) reads that log and
 * writes the selection into the dealer's live DealerRater ReviewBuilder
 * settings — this script never touches DealerRater directly.
 *
 * Kept as a SEPARATE deployment from pb_link_tracker/Code.js (do not merge):
 *   - different/riskier notify list (adds an external-facing AE)
 *   - different structured log schema (dealer id + option, not [time, key, recipient, name])
 *   - pb_link_tracker is a live dependency for other real dealer-facing reports
 *     (Dyer, Nalley, Hendrick, Herb Chambers) — isolating blast radius.
 *
 * WHY TWO STAGES (same reasoning as pb_link_tracker):
 *   Email security scanners (Mimecast/SafeLinks/Gmail preview) fetch links but
 *   never click buttons. A single-stage doGet would log a false "GM selected
 *   option 2" from a scanner prefetch, which would then get auto-applied to a
 *   live customer-facing template. Logging only fires on an actual button
 *   click (fetch fired from onclick, not from page load).
 *
 * URL shapes:
 *   List page (the one link in the email):
 *     …/exec?legacy_id=<id>&dealer=<name>
 *   Confirm (fired by a button click on the list page, not visited directly):
 *     …/exec?legacy_id=<id>&dealer=<name>&option=<1|2|3>&ack=1
 *
 * DEPLOY (via clasp): see ./DEPLOY.md
 */

// TESTING: Danielle excluded until the real GM batch goes out (avoid confusing
// test-click notifications in her inbox) — switch back to the two-address array
// before enabling the live launchd schedule / sending real GM emails.
const NOTIFY_TO = ['jcrawley@cars.com'].join(',');
const LOG_SHEET_ID = '1ZlEcGNZo0CMGb5BTyW_lbJc09lh5FzCgqbM8bIdPrHM';
const ENGAGEMENTS_TAB = 'Engagements';

// Must stay in sync with aca_review_shared.py::MESSAGE_OPTIONS (subject +
// message) — this is what renders the full draft on the list page.
const OPTION_DETAILS = {
  '1': {
    subject: "You made history today!",
    message: "Hi [FirstName]! We need to talk about what happened after you left. The moment we finalized your new ride, the showroom turned into a party. We're talking confetti cannons, a localized “human wave,” and the biggest miracle of all — our General Manager actually smiled. (Trust us, he never smiles.) Earning your business was the highlight of our month! Since you're officially a legend around here now, would you mind sharing the love with a quick review on [ReviewDestination]? It takes 60 seconds and helps us keep the celebration going. Thanks for being awesome! — The [DealerName] Team",
  },
  '2': {
    subject: "Breaking News: You're a local celebrity!",
    message: "Hi [FirstName]! Word travels fast. The second you drove off the lot in your new ride, the mood here shifted from “business as usual” to “Super Bowl halftime show.” Our team is currently debating whether to retire your name to the rafters. There's a rumor that our General Manager — a man who usually has the facial expressions of a stone gargoyle — was actually seen doing a victory dance in his office. We're still checking the security tapes to confirm, but the vibes are definitely at an all-time high. You officially made our day. Since you're the talk of the dealership, would you mind keeping the momentum going by leaving us a review on [ReviewDestination]? It takes about a minute, and it's the only way we can justify keeping the disco ball spinning around here. Thanks for being a total rockstar! — The [DealerName] Team",
  },
  '3': {
    subject: "We're still cleaning up the confetti!",
    message: "Hi [FirstName]! The second you drove off in your new ride, this place turned into a stadium! We're talking standing ovations, high-fives across the showroom, and — get this — our General Manager was actually caught doing a celebratory moonwalk. Considering he's usually as stoic as a brick wall, it was a literal historic event. You're basically a celebrity here now. Could you keep the good vibes rolling by leaving us a quick review on [ReviewDestination]? It takes 30 seconds and keeps our GM's rare smile from disappearing. Thanks for being the MVP today! — The [DealerName] Team",
  },
};

function personalize_(text, dealer) {
  return text
    .replace(/\[DealerName\]/g, dealer)
    .replace(/\[FirstName\]/g, 'there')
    .replace(/\[ReviewDestination\]/g, 'DealerRater');
}

/**
 * Run this ONCE from the Apps Script editor (Run ▸ authorizeScopes) right
 * after the first `clasp push`. Forces Google's OAuth consent for the scopes
 * this web app needs (send mail + sheets) — clasp itself never triggers that
 * consent, so without this step the deployed /exec link can't notify or log.
 */
function authorizeScopes() {
  MailApp.getRemainingDailyQuota();
  SpreadsheetApp.openById(LOG_SHEET_ID).getSheets();
  Logger.log('Authorized — the /exec web app is ready to log and notify.');
}

function pageShell_(bodyHtml, maxWidth) {
  return '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<style>body{font-family:Arial,Helvetica,sans-serif;color:#212121;max-width:' + maxWidth + 'px;margin:5% auto;padding:0 20px}' +
    '.btn{display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:12px 26px;border-radius:6px;font-size:14px;font-weight:700;margin-top:12px}' +
    '.eyebrow{color:#7c3aed;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.06em}' +
    '.email-card{background:#ffffff;border:1px solid #e0d9f5;border-radius:6px;overflow:hidden;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,0.06)}' +
    '.email-head{background:#f4f1fb;padding:12px 16px;border-bottom:1px solid #e0d9f5}' +
    '.email-subj-label{font-size:9px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px}' +
    '.email-subj{font-size:15px;font-weight:700;color:#1a1a2e}' +
    '.email-body{padding:16px;font-size:13px;color:#333;line-height:1.7}' +
    '.opt-label{font-size:11px;font-weight:700;color:#1a1a2e;margin:0 0 6px}' +
    '.center{text-align:center}</style></head><body>' + bodyHtml + '</body></html>';
}

function doGet(e) {
  const params = (e && e.parameter) || {};
  const legacyId = params.legacy_id || '';
  const dealer = params.dealer || 'Unknown Dealer';
  const option = ['1', '2', '3'].includes(params.option) ? params.option : '';

  if (!legacyId) {
    return HtmlService.createHtmlOutput('<p>Invalid or expired link.</p>');
  }

  // STAGE 2 — a specific option was confirmed (fired by a button click on the
  // list page below, never linked to directly): log + notify. No redirect
  // (nothing to navigate to).
  if (option && params.ack === '1') {
    const label = OPTION_DETAILS[option].subject;
    const when = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "EEE MMM d, yyyy 'at' h:mm a z");
    const eventId = Utilities.getUuid();

    try {
      MailApp.sendEmail({
        to: NOTIFY_TO,
        subject: 'ReviewBuilder tone selected — ' + dealer + ' — Option ' + option,
        htmlBody:
          '<p><b>' + dealer + '</b> selected a ReviewBuilder message tone via button click.</p>' +
          '<table cellpadding="4" style="font-family:Arial,sans-serif;font-size:14px">' +
          '<tr><td><b>Dealer</b></td><td>' + dealer + ' (legacy_id ' + legacyId + ')</td></tr>' +
          '<tr><td><b>Option</b></td><td>' + option + ' &mdash; &ldquo;' + label + '&rdquo;</td></tr>' +
          '<tr><td><b>Channel</b></td><td>button click</td></tr>' +
          '<tr><td><b>When</b></td><td>' + when + '</td></tr>' +
          '</table>' +
          '<p style="color:#888;font-size:12px">This will be applied to the dealer’s live DealerRater Sales Request Email automatically on the next scheduled run. See the Engagements tab: ' +
          'https://docs.google.com/spreadsheets/d/' + LOG_SHEET_ID + '/</p>'
      });
    } catch (err) { /* never block the confirmation page on a mail error */ }

    try {
      const sheet = SpreadsheetApp.openById(LOG_SHEET_ID).getSheetByName(ENGAGEMENTS_TAB);
      sheet.appendRow([
        eventId, new Date(), legacyId, dealer, 'button', option, '', label, eventId,
      ]);
    } catch (err) { /* never block the confirmation page on a log error */ }

    return HtmlService.createHtmlOutput(pageShell_(
      '<div class="center"><h2>Thanks &mdash; got it!</h2>' +
      '<p>We’ll update your ReviewBuilder sales-request message to &ldquo;' + label + '&rdquo; automatically, typically within one business day. No further action needed.</p>' +
      '</div>', 520
    ));
  }

  // STAGE 1 — list page, NO log, NO email yet. Shows all 3 full drafts
  // (formatted like real emails) with a per-option confirm button each. A
  // scanner/prefetch of this page is harmless — nothing is logged here.
  const exec = ScriptApp.getService().getUrl();
  const optionBlocks = ['1', '2', '3'].map(function (opt) {
    const details = OPTION_DETAILS[opt];
    const subject = personalize_(details.subject, dealer);
    const message = personalize_(details.message, dealer);
    const ping = exec + '?ack=1&legacy_id=' + encodeURIComponent(legacyId) +
                 '&dealer=' + encodeURIComponent(dealer) +
                 '&option=' + encodeURIComponent(opt);
    return '<div class="opt-label">Option ' + opt + '</div>' +
      '<div class="email-card">' +
        '<div class="email-head"><div class="email-subj-label">Subject</div><div class="email-subj">' + subject + '</div></div>' +
        '<div class="email-body">' + message + '</div>' +
      '</div>' +
      '<div class="center" style="margin-bottom:28px;">' +
      '<a class="btn" target="_top" href="' + ping + '" ' +
        "onclick=\"try{fetch('" + ping + "',{mode:'no-cors',keepalive:true});}catch(err){}\">Confirm &amp; Use This Message &rarr;</a>" +
      '</div>';
  }).join('');

  const timingNote =
    '<div style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;margin:0 0 20px;">' +
    '<div style="font-size:12px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">When to Send Requests</div>' +
    '<div style="font-size:12px;color:#444;line-height:1.5;">Requests go out <strong>the next day by default (recommended)</strong>. Want 7, 14, or 30 days instead? Reply-all to the original email and let us know, e.g. &ldquo;Option 2, 7 days.&rdquo; No reply needed if the next-day default works for you.</div>' +
    '</div>';

  return HtmlService.createHtmlOutput(pageShell_(
    '<div class="center"><div class="eyebrow">' + dealer + '</div>' +
    '<h2 style="margin:6px 0 4px;">Choose Your Customer Review-Request Message</h2>' +
    '<p style="color:#666;font-size:13px;">These are the exact emails your customers would receive after a sale — already reviewed and approved by ACA. Pick your favorite below, or reply-all to the original email with your option number (1, 2, or 3).</p>' +
    '</div>' + timingNote + optionBlocks, 560
  ));
}
