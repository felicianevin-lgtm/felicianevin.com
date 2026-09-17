/**
 * felicianevin.com lead backend — Google Apps Script web app ($0)
 *
 * What it does on every form submission:
 *   1. Spam checks (honeypot, too-fast submit, basic validation)
 *   2. Logs the lead to the "Leads" tab of the bound Google Sheet
 *   3. Emails the lead to the BoldTrail Lead Dropbox so a Contact is created
 *   4. Emails Felicia's business inbox a plain summary
 *   5. Looks up the "Routing" tab and, for ACTIVE rows that match, emails the partner agent
 *
 * Setup: see backend/README.md. All settings live in the "Settings" tab — no code edits needed.
 */

// Leave '' when the script is bound to the Sheet (Extensions > Apps Script). If it had to be created as a
// standalone project at script.google.com, paste the Sheet's ID here (the long string in its URL) in the
// editor copy only. Do not commit the real ID.
var SHEET_ID = '';

var TABS = { leads: 'Leads', routing: 'Routing', settings: 'Settings' };

var LEAD_COLUMNS = ['timestamp', 'intent', 'area', 'timeframe', 'name', 'email', 'phone', 'sms_consent', 'newsletter',
  'message', 'address', 'form', 'page', 'referrer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content',
  'routed_to', 'boldtrail_sent', 'status'];

/** Run once from the editor: builds the three tabs with headers and sample rows. */
function setup() {
  var ss = book();
  var leads = ss.getSheetByName(TABS.leads) || ss.insertSheet(TABS.leads);
  if (leads.getLastRow() === 0) leads.appendRow(LEAD_COLUMNS);
  leads.setFrozenRows(1);

  var routing = ss.getSheetByName(TABS.routing) || ss.insertSheet(TABS.routing);
  if (routing.getLastRow() === 0) {
    routing.appendRow(['active', 'partner_name', 'partner_email', 'intent (Buying/Selling/Both/any)', 'area_keywords (comma list, or any)', 'partner_dropbox_email (optional)', 'notes']);
    routing.appendRow([false, 'Partner agent (Placer)', '', 'any', 'roseville, rocklin, lincoln, granite bay, loomis, auburn, placer', '', 'Turn ON only after the broker-to-broker referral agreement is signed']);
    routing.appendRow([false, 'Partner agent (Sacramento)', '', 'any', 'sacramento, elk grove, folsom, el dorado', '', 'Turn ON only after the referral agreement is signed']);
  }
  routing.setFrozenRows(1);

  var settings = ss.getSheetByName(TABS.settings) || ss.insertSheet(TABS.settings);
  if (settings.getLastRow() === 0) {
    settings.appendRow(['key', 'value', 'what it is']);
    settings.appendRow(['boldtrail_dropbox', '', 'Your unique address from BoldTrail > Lead Engine > Lead Dropbox']);
    settings.appendRow(['notify_email', '', 'Business inbox that gets every lead summary']);
    settings.appendRow(['min_elapsed_ms', 3000, 'Submissions faster than this are treated as bots']);
    settings.appendRow(['allowed_origin_note', 'https://felicianevin.com', 'For reference only']);
  }
}

function doGet() {
  return json({ ok: true, service: 'felicianevin.com lead backend' });
}

function doPost(e) {
  try {
    var p = (e && e.parameter) || {};
    var cfg = readSettings();

    // --- spam checks: pretend success so bots learn nothing ---
    if (p.company) return json({ ok: true });
    if (Number(p.elapsed_ms || 0) < Number(cfg.min_elapsed_ms || 3000)) return json({ ok: true });

    var lead = {};
    LEAD_COLUMNS.forEach(function (k) { lead[k] = clean(p[k]); });
    lead.timestamp = new Date();
    if (!lead.name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(lead.email)) return json({ ok: false, error: 'invalid' });
    if (['Buying', 'Selling', 'Both', 'Other', 'Newsletter'].indexOf(lead.intent) === -1) lead.intent = 'Other';
    var isLead = lead.intent !== 'Other' && lead.intent !== 'Newsletter'; // 'Other' = general question / site feedback / privacy request: never a CRM lead, never routed
    lead.sms_consent = lead.sms_consent === 'yes' ? 'yes' : 'no';
    lead.newsletter = lead.newsletter === 'yes' ? 'yes' : 'no'; // the weekly routine reads this column to build the send list

    // --- routing ---
    var partners = isLead ? matchPartners(lead) : [];
    lead.routed_to = partners.map(function (r) { return r.name; }).join(', ');

    // --- BoldTrail Lead Dropbox ---
    lead.boldtrail_sent = 'no';
    if (cfg.boldtrail_dropbox && isLead) {
      MailApp.sendEmail({ to: cfg.boldtrail_dropbox, subject: 'Add Contact', body: dropboxBody(lead) });
      lead.boldtrail_sent = 'yes';
    }
    lead.status = 'new';

    // --- log ---
    var sheet = book().getSheetByName(TABS.leads);
    sheet.appendRow(LEAD_COLUMNS.map(function (k) { return lead[k]; }));

    // --- notify Felicia ---
    if (cfg.notify_email) {
      MailApp.sendEmail({
        to: cfg.notify_email,
        replyTo: lead.email,
        subject: (isLead ? 'New ' + lead.intent + ' lead // ' : lead.intent === 'Newsletter' ? 'Newsletter signup // ' : 'Website question // ') + (lead.area || 'area not given') + ' // ' + lead.name,
        body: summary(lead) + '\n\nRouted to: ' + (lead.routed_to || 'nobody (you only)') +
              '\nBoldTrail dropbox: ' + lead.boldtrail_sent
      });
    }

    // --- notify partners (ACTIVE rows only) ---
    partners.forEach(function (r) {
      MailApp.sendEmail({
        to: r.email,
        cc: cfg.notify_email || '',
        replyTo: cfg.notify_email || '',
        subject: 'Referral from Felicia Nevin // ' + lead.intent + ' // ' + (lead.area || 'CA'),
        body: 'Hi ' + r.name.split(' ')[0] + ',\n\nA new lead came in through felicianevin.com that fits your area. ' +
              'This is a referral under our referral agreement (Felicia Nevin, DRE #01961050, eXp Realty of California, Inc.).\n\n' +
              summary(lead) +
              (lead.sms_consent === 'yes'
                ? '\n\nCONSENT NOTE: They opted in to calls/texts from Felicia Nevin, eXp Realty, and "the eXp Realty partner agent Felicia connects me with." ' +
                  'Introduce yourself that way so it is no surprise. Check eXp DialSafe first, contact them 8am-9pm their time, honor STOP right away, ' +
                  'and get your own written consent before adding them to your own automated campaigns. (If you are not with eXp Realty, this consent does not cover you: reach out by hand only.)'
                : '\n\nCONSENT NOTE: This person did NOT opt in to calls or texts. Email first.') +
              '\n\nPlease reply to let me know you have it.\n\nBest,\nFelicia'
      });
      if (r.dropbox) MailApp.sendEmail({ to: r.dropbox, subject: 'Add Contact', body: dropboxBody(lead) });
    });

    return json({ ok: true });
  } catch (err) {
    console.error(err);
    return json({ ok: false, error: 'server' });
  }
}

/* ---------------- helpers ---------------- */

function book() { return SHEET_ID ? SpreadsheetApp.openById(SHEET_ID) : SpreadsheetApp.getActive(); }

function clean(v) { return String(v == null ? '' : v).replace(/[\r\n]+/g, ' ').trim().slice(0, 1000); }

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function readSettings() {
  var rows = book().getSheetByName(TABS.settings).getDataRange().getValues(), out = {};
  rows.slice(1).forEach(function (r) { if (r[0]) out[String(r[0]).trim()] = r[1]; });
  return out;
}

function matchPartners(lead) {
  var rows = book().getSheetByName(TABS.routing).getDataRange().getValues().slice(1);
  var area = (lead.area + ' ' + lead.address).toLowerCase(), out = [];
  rows.forEach(function (r) {
    var active = r[0] === true || String(r[0]).toLowerCase() === 'true';
    if (!active || !r[2]) return;
    var intent = String(r[3] || 'any').toLowerCase();
    if (intent !== 'any' && intent !== lead.intent.toLowerCase() && lead.intent !== 'Both') return;
    var kws = String(r[4] || 'any').toLowerCase().split(',').map(function (s) { return s.trim(); }).filter(String);
    var hit = kws.indexOf('any') !== -1 || kws.some(function (k) { return area.indexOf(k) !== -1; });
    if (hit) out.push({ name: String(r[1]), email: String(r[2]), dropbox: String(r[5] || '') });
  });
  return out.slice(0, 1); // first match wins — one lead, one partner
}

/** BoldTrail "Add Contact" email template: one field per line. */
function dropboxBody(lead) {
  var parts = lead.name.split(' '), first = parts.shift(), last = parts.join(' ');
  var lines = [
    'First Name: ' + first,
    'Last Name: ' + last,
    'Email: ' + lead.email,
    'Deal Type: ' + (lead.intent === 'Buying' ? 'Buyer' : 'Seller')
  ];
  if (lead.phone) lines.push('Phone: ' + lead.phone);
  if (lead.area) lines.push('Area: ' + lead.area);
  if (lead.address) lines.push('Seller Address: ' + lead.address);
  return lines.join('\n');
}

function summary(lead) {
  return [
    'Name: ' + lead.name,
    'Email: ' + lead.email,
    'Phone: ' + (lead.phone || '(none)'),
    'OK to call/text: ' + lead.sms_consent,
    'Weekly newsletter: ' + lead.newsletter,
    'Wants: ' + lead.intent,
    'Area: ' + (lead.area || '(not given)'),
    'Property address: ' + (lead.address || '(n/a)'),
    'Timeframe: ' + (lead.timeframe || '(not given)'),
    'Message: ' + (lead.message || '(none)'),
    'Source: ' + [lead.form, lead.page, lead.utm_source, lead.utm_campaign].filter(String).join(' | ')
  ].join('\n');
}
