#!/usr/bin/env python3
"""
build_evening_brief.py
Generates an HTML evening intelligence brief email and saves to /tmp/evening_brief.html
Also saves a plain-text version to /tmp/evening_brief.txt
"""

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evening Intelligence Brief — Monday, April 13, 2026</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f2f5;font-family:'Segoe UI',Poppins,Helvetica,Arial,sans-serif;">

<!-- Outer wrapper -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f2f5;">
<tr><td align="center" style="padding:24px 12px;">

<!-- Email container 680px -->
<table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0" style="max-width:680px;width:100%;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">

<!-- ============ HEADER ============ -->
<tr>
<td style="background:linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%);padding:40px 40px 32px 40px;text-align:center;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:13px;letter-spacing:2.5px;text-transform:uppercase;color:#7b8794;padding-bottom:10px;">Cars Commerce &middot; Customer Success</td></tr>
  <tr><td style="font-size:28px;font-weight:700;color:#ffffff;line-height:1.25;padding-bottom:8px;">Evening Intelligence Brief</td></tr>
  <tr><td style="font-size:16px;color:#c5cdd8;padding-bottom:6px;">Monday, April 13, 2026</td></tr>
  <tr><td style="font-size:13px;color:#7b8794;">End-of-day update &middot; Mountain Time</td></tr>
  </table>
</td>
</tr>

<!-- ============ BODY ============ -->
<tr>
<td style="background-color:#ffffff;padding:0 40px 40px 40px;">

<!-- ── Section 1: Completed Today ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:32px;">
<tr>
<td style="border-left:4px solid #28a745;padding:20px 24px;background-color:#f8faf8;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#28a745;font-weight:700;padding-bottom:8px;">Completed Today</td></tr>

  <!-- Item 1 -->
  <tr><td style="padding-bottom:14px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="28" valign="top" style="padding-top:2px;color:#28a745;font-size:16px;font-weight:700;">&#10003;</td>
      <td style="font-size:14px;color:#1a1a2e;line-height:1.55;">
        <strong>Herb Chambers DealerRater Employee Updates</strong><br>
        325 total changes (161 added, 111 removed, 53 titles updated) across 24 stores. Consolidated into review sheet:
        <a href="https://docs.google.com/spreadsheets/d/1_reFTgGXE1_AzHPFYbEuz8sJ06EejjKyHbg0j2Shm8s/edit" style="color:#0f3460;text-decoration:underline;">HC DealerRater Employee Updates &mdash; Q2 2026</a>
        &mdash; 7 tabs: Summary, Added, Removed, Titles Updated, Current DR Rosters, Website Staff, No Website Data
      </td>
    </tr>
    </table>
  </td></tr>

  <!-- Item 2 -->
  <tr><td style="padding-bottom:14px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="28" valign="top" style="padding-top:2px;color:#28a745;font-size:16px;font-weight:700;">&#10003;</td>
      <td style="font-size:14px;color:#1a1a2e;line-height:1.55;">
        <strong>Price Badge Reports (Hendrick + Nalley)</strong><br>
        Hendrick: J1=8%, 4,313 vehicles, 48 stores. Nalley: J1=34%, 57 vehicles, 148 demand signals. Both Gmail drafts created.
      </td>
    </tr>
    </table>
  </td></tr>

  <!-- Item 3 -->
  <tr><td>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="28" valign="top" style="padding-top:2px;color:#28a745;font-size:16px;font-weight:700;">&#10003;</td>
      <td style="font-size:14px;color:#1a1a2e;line-height:1.55;">
        <strong>Sonic Value Prep</strong><br>
        Discussed with Sharon on Friday (4/10).
      </td>
    </tr>
    </table>
  </td></tr>

  </table>
</td>
</tr>
</table>

<!-- ── Section 2: Prep for Wednesday ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
<tr>
<td style="border-left:4px solid #6366f1;padding:20px 24px;background-color:#f8f7ff;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#6366f1;font-weight:700;padding-bottom:4px;">Prep: Reporting Needs &mdash; Wed 3p MT</td></tr>
  <tr><td style="font-size:13px;color:#555;padding-bottom:14px;line-height:1.5;">Meeting with Brook Barker (organizer, Dealer Inspire), Maya Patel, Nora Gaughan. Topic: &ldquo;Reporting Needs&rdquo;</td></tr>

  <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.6;padding-bottom:10px;">
    <strong style="color:#6366f1;">Come prepared with:</strong> What reports do you run regularly? What data gaps exist? What&rsquo;s manual that could be automated?
  </td></tr>

  <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.6;padding-bottom:10px;">
    <strong style="color:#6366f1;">Talking points:</strong>
  </td></tr>
  <tr><td style="padding-left:16px;padding-bottom:12px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:4px;">&bull; Price Badge automation progress (Tableau &rarr; Google Sheets &rarr; Gmail, partially automated)</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:4px;">&bull; Market Intelligence reports via GitHub Pages</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:4px;">&bull; Herb Chambers DR employee audit workflow</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;">&bull; Dealer Health Dashboard vision (Streamlit + SF + Claude analysis)</td></tr>
    </table>
  </td></tr>

  <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.6;padding-bottom:10px;">
    <strong style="color:#6366f1;">Frame as:</strong> &ldquo;Here&rsquo;s what I&rsquo;ve built, here&rsquo;s what&rsquo;s working, here&rsquo;s what I still need from the reporting side&rdquo;
  </td></tr>

  <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.6;">
    <strong style="color:#6366f1;">Opportunity:</strong> Pitch the Atlan/Redshift direct SQL approach as the unlock for self-serve reporting
  </td></tr>
  </table>
</td>
</tr>
</table>

<!-- ── Section 3: SF Health Scores ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
<tr>
<td style="border-left:4px solid #f59e0b;padding:20px 24px;background-color:#fffbf0;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#f59e0b;font-weight:700;padding-bottom:4px;">New Insight</td></tr>
  <tr><td style="font-size:17px;font-weight:700;color:#1a1a2e;padding-bottom:14px;">SF Health Score &rarr; Dashboard Integration</td></tr>

  <tr><td style="padding-left:0;padding-bottom:0;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; Today&rsquo;s GTM AMA (10a) covered Health Scores and Retention Records &mdash; explore as data source for Dealer Health Dashboard</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; SF Health Score fields could replace or supplement the blocked Tableau metrics</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; Could be a faster path than waiting for Atlan access &mdash; query via existing SF CLI (<code style="background:#f0f0f0;padding:1px 5px;border-radius:3px;font-size:13px;">sf data query</code>)</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; <strong>Action:</strong> Investigate what Health Score fields exist on Account object, check if Retention Records are a standard or custom object</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;">&bull; <em>Note:</em> Atlan API token + Redshift credentials still pending (requested 4/10 in #data_governance_communications) &mdash; recommended to hold on CDP scraper build until access comes through</td></tr>
    </table>
  </td></tr>
  </table>
</td>
</tr>
</table>

<!-- ── Section 4: eLearnings ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
<tr>
<td style="border-left:4px solid #0ea5e9;padding:20px 24px;background-color:#f0f9ff;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#0ea5e9;font-weight:700;padding-bottom:4px;">eLearnings &amp; Quiz Prep</td></tr>

  <tr><td style="padding-left:0;padding-bottom:0;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; Check Cars Commerce University / LMS for any overdue modules</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; <strong>Upcoming:</strong> Major Account Masterclass (Fri 10a) &mdash; review prerequisites</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;padding-bottom:8px;">&bull; <strong>Tip:</strong> For quiz prep, screenshot key slides and compile a quick cheatsheet before each module. Focus on: product names/tiers, pricing thresholds, badge definitions, connection types vs lead types</td></tr>
    <tr><td style="font-size:14px;color:#1a1a2e;line-height:1.7;">&bull; <strong>Cheatsheet topics to review:</strong> DealerRater Connections vs Premium Listings tiers, AccuTrade features, Dealer Inspire website packages, FUEL IMV/pricing methodology</td></tr>
    </table>
  </td></tr>
  </table>
</td>
</tr>
</table>

<!-- ── Section 5: Project & Growth Tracker ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
<tr>
<td style="border-left:4px solid #14b8a6;padding:20px 24px;background-color:#f0fdfa;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#14b8a6;font-weight:700;padding-bottom:4px;">Active Projects &amp; Account Growth</td></tr>
  <tr><td style="padding-top:10px;">
    <!-- Data table -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
    <!-- Table header -->
    <tr style="background-color:#14b8a6;">
      <td style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;border-radius:4px 0 0 0;">Project</td>
      <td style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;">Status</td>
      <td style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;">Next Step</td>
      <td style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;border-radius:0 4px 0 0;">Impact</td>
    </tr>
    <!-- Row 1 -->
    <tr style="background-color:#ffffff;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Dealer Health Dashboard</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">SF+Claude working, Tableau blocked</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Wait for Atlan access; explore SF Health Scores</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Self-serve dealer analysis for team</td>
    </tr>
    <!-- Row 2 -->
    <tr style="background-color:#f8fdfb;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Herb Chambers DR Updates</td>
      <td style="padding:8px 10px;font-size:13px;color:#28a745;border-bottom:1px solid #e5e7eb;font-weight:600;">COMPLETE</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Review sheet ready; updates applied in METAL</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">24 stores current on DealerRater</td>
    </tr>
    <!-- Row 3 -->
    <tr style="background-color:#ffffff;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Price Badge Reports</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Automated Mon/Fri</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Review/send drafts (Hendrick + Nalley)</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Weekly dealer engagement tool</td>
    </tr>
    <!-- Row 4 -->
    <tr style="background-color:#f8fdfb;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Asbury Portfolio Analysis</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Data collected</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">CPL/CPC calculations, prospect tier list</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">~$264K MRR group growth strategy</td>
    </tr>
    <!-- Row 5 -->
    <tr style="background-color:#ffffff;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Market Intelligence Reports</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Live on GitHub Pages</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Continue building for new prospects</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Prospect-facing competitive intel</td>
    </tr>
    <!-- Row 6 -->
    <tr style="background-color:#f8fdfb;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;border-bottom:1px solid #e5e7eb;font-weight:600;">Sonic Inventory Tiers</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Prep complete</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Follow up from Sharon 1:1</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;border-bottom:1px solid #e5e7eb;">Sonic value conversation support</td>
    </tr>
    <!-- Row 7 -->
    <tr style="background-color:#ffffff;">
      <td style="padding:8px 10px;font-size:13px;color:#1a1a2e;font-weight:600;">Atlan/Redshift Access</td>
      <td style="padding:8px 10px;font-size:13px;color:#f59e0b;font-weight:600;">Pending (requested 4/10)</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;">Follow up mid-week if no response</td>
      <td style="padding:8px 10px;font-size:13px;color:#555;">Unlocks direct SQL &rarr; replaces all scraping</td>
    </tr>
    </table>
  </td></tr>
  </table>
</td>
</tr>
</table>

<!-- ── Section 6: Week Ahead ── -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
<tr>
<td style="border-left:4px solid #6366f1;padding:20px 24px;background-color:#f8f7ff;border-radius:0 8px 8px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#6366f1;font-weight:700;padding-bottom:12px;">Week Ahead</td></tr>
  <tr><td>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
    <!-- Header -->
    <tr style="background-color:#6366f1;">
      <td width="60" style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;border-radius:4px 0 0 0;">Day</td>
      <td style="padding:8px 10px;font-size:12px;font-weight:700;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;border-radius:0 4px 0 0;">Events</td>
    </tr>
    <!-- TUE -->
    <tr style="background-color:#ffffff;">
      <td style="padding:10px;font-size:13px;color:#6366f1;font-weight:700;border-bottom:1px solid #e5e7eb;vertical-align:top;">TUE</td>
      <td style="padding:10px;font-size:13px;color:#1a1a2e;line-height:1.6;border-bottom:1px solid #e5e7eb;">ACA NY/PA Stores Review (12p) &middot; ACA External Projects Call (1p)</td>
    </tr>
    <!-- WED -->
    <tr style="background-color:#f8f7ff;">
      <td style="padding:10px;font-size:13px;color:#6366f1;font-weight:700;border-bottom:1px solid #e5e7eb;vertical-align:top;">WED</td>
      <td style="padding:10px;font-size:13px;color:#1a1a2e;line-height:1.6;border-bottom:1px solid #e5e7eb;">Revenue Forecast Reminder &middot; <strong>Reporting Needs (3p)</strong> &mdash; Brook Barker, Maya, Nora</td>
    </tr>
    <!-- THU -->
    <tr style="background-color:#ffffff;">
      <td style="padding:10px;font-size:13px;color:#6366f1;font-weight:700;border-bottom:1px solid #e5e7eb;vertical-align:top;">THU</td>
      <td style="padding:10px;font-size:13px;color:#1a1a2e;line-height:1.6;border-bottom:1px solid #e5e7eb;">ACA Recurring Projects (9a) &middot; ACA Stand Up (9:30a) &middot; Checkpoint Series (11a) &middot; <strong>Danielle PTO</strong></td>
    </tr>
    <!-- FRI -->
    <tr style="background-color:#f8f7ff;">
      <td style="padding:10px;font-size:13px;color:#6366f1;font-weight:700;vertical-align:top;">FRI</td>
      <td style="padding:10px;font-size:13px;color:#1a1a2e;line-height:1.6;">Coffee Chat (9a) &middot; <strong>Major Account Masterclass (10a)</strong> &middot; Brook/Jacob (10:30a) &middot; Revenue Forecast Due</td>
    </tr>
    </table>
  </td></tr>
  </table>
</td>
</tr>
</table>

<!-- Spacer before footer -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td style="height:24px;"></td></tr>
</table>

</td>
</tr>

<!-- ============ FOOTER ============ -->
<tr>
<td style="background-color:#1a1a2e;padding:20px 40px;text-align:center;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="font-size:12px;color:#7b8794;line-height:1.5;">Generated by Claude Code &middot; Apr 13, 2026 &middot; jcrawley@cars.com</td></tr>
  </table>
</td>
</tr>

</table>
<!-- /Email container -->

</td></tr>
</table>
<!-- /Outer wrapper -->

</body>
</html>
"""

PLAIN_TEXT = """\
===============================================================
  EVENING INTELLIGENCE BRIEF
  Monday, April 13, 2026
  End-of-day update · Mountain Time
  Cars Commerce · Customer Success
===============================================================

--- COMPLETED TODAY ---

[✓] Herb Chambers DealerRater Employee Updates
    325 total changes (161 added, 111 removed, 53 titles updated)
    across 24 stores. Consolidated into review sheet:
    HC DealerRater Employee Updates — Q2 2026
    https://docs.google.com/spreadsheets/d/1_reFTgGXE1_AzHPFYbEuz8sJ06EejjKyHbg0j2Shm8s/edit
    7 tabs: Summary, Added, Removed, Titles Updated, Current DR
    Rosters, Website Staff, No Website Data

[✓] Price Badge Reports (Hendrick + Nalley)
    Hendrick: J1=8%, 4,313 vehicles, 48 stores.
    Nalley: J1=34%, 57 vehicles, 148 demand signals.
    Both Gmail drafts created.

[✓] Sonic Value Prep
    Discussed with Sharon on Friday (4/10).


--- PREP: REPORTING NEEDS — WED 3P MT ---

Meeting with Brook Barker (organizer, Dealer Inspire), Maya Patel,
Nora Gaughan. Topic: "Reporting Needs"

Come prepared with: What reports do you run regularly? What data
gaps exist? What's manual that could be automated?

Talking points:
  • Price Badge automation progress (Tableau → Google Sheets →
    Gmail, partially automated)
  • Market Intelligence reports via GitHub Pages
  • Herb Chambers DR employee audit workflow
  • Dealer Health Dashboard vision (Streamlit + SF + Claude analysis)

Frame as: "Here's what I've built, here's what's working, here's
what I still need from the reporting side"

Opportunity: Pitch the Atlan/Redshift direct SQL approach as the
unlock for self-serve reporting


--- NEW INSIGHT: SF HEALTH SCORE → DASHBOARD INTEGRATION ---

  • Today's GTM AMA (10a) covered Health Scores and Retention
    Records — explore as data source for Dealer Health Dashboard
  • SF Health Score fields could replace or supplement the blocked
    Tableau metrics
  • Could be a faster path than waiting for Atlan access — query
    via existing SF CLI (sf data query)
  • Action: Investigate what Health Score fields exist on Account
    object, check if Retention Records are a standard or custom
    object
  • Note: Atlan API token + Redshift credentials still pending
    (requested 4/10 in #data_governance_communications) —
    recommended to hold on CDP scraper build until access comes
    through


--- eLEARNINGS & QUIZ PREP ---

  • Check Cars Commerce University / LMS for any overdue modules
  • Upcoming: Major Account Masterclass (Fri 10a) — review
    prerequisites
  • Tip: For quiz prep, screenshot key slides and compile a quick
    cheatsheet before each module. Focus on: product names/tiers,
    pricing thresholds, badge definitions, connection types vs
    lead types
  • Cheatsheet topics to review: DealerRater Connections vs Premium
    Listings tiers, AccuTrade features, Dealer Inspire website
    packages, FUEL IMV/pricing methodology


--- ACTIVE PROJECTS & ACCOUNT GROWTH ---

Project                     | Status                        | Next Step                                | Impact
----------------------------|-------------------------------|------------------------------------------|---------------------------------------
Dealer Health Dashboard     | SF+Claude working, Tab blocked| Wait for Atlan; explore SF Health Scores  | Self-serve dealer analysis for team
Herb Chambers DR Updates    | COMPLETE                      | Review sheet ready; updates in METAL      | 24 stores current on DealerRater
Price Badge Reports         | Automated Mon/Fri             | Review/send drafts (Hendrick + Nalley)    | Weekly dealer engagement tool
Asbury Portfolio Analysis   | Data collected                | CPL/CPC calculations, prospect tier list  | ~$264K MRR group growth strategy
Market Intelligence Reports | Live on GitHub Pages          | Continue building for new prospects        | Prospect-facing competitive intel
Sonic Inventory Tiers       | Prep complete                 | Follow up from Sharon 1:1                 | Sonic value conversation support
Atlan/Redshift Access       | Pending (requested 4/10)      | Follow up mid-week if no response         | Unlocks direct SQL → replaces scraping


--- WEEK AHEAD ---

TUE  ACA NY/PA Stores Review (12p) · ACA External Projects Call (1p)
WED  Revenue Forecast Reminder · *Reporting Needs (3p)* — Brook Barker, Maya, Nora
THU  ACA Recurring Projects (9a) · ACA Stand Up (9:30a) · Checkpoint Series (11a) · *Danielle PTO*
FRI  Coffee Chat (9a) · *Major Account Masterclass (10a)* · Brook/Jacob (10:30a) · Revenue Forecast Due


===============================================================
Generated by Claude Code · Apr 13, 2026 · jcrawley@cars.com
===============================================================
"""


def main():
    with open("/tmp/evening_brief.html", "w") as f:
        f.write(HTML)

    with open("/tmp/evening_brief.txt", "w") as f:
        f.write(PLAIN_TEXT)

    print("Done")


if __name__ == "__main__":
    main()
