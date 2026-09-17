# Lead backend setup (one time, about 10 minutes, $0)

Do this while signed into the **business** Google account (not the personal Gmail).

1. Create a new Google Sheet. Name it `felicianevin.com Leads`.
2. In the Sheet: **Extensions → Apps Script**. Delete the sample code, paste in all of `Code.gs`, save.
3. In the script editor, pick the function **setup** in the dropdown and click **Run**. Approve the permissions
   (it needs to edit this Sheet and send email as you). Three tabs appear: `Leads`, `Routing`, `Settings`.
4. Fill in the **Settings** tab:
   - `boldtrail_dropbox` — your unique address from BoldTrail → Lead Engine → Lead Dropbox
   - `notify_email` — the business inbox that should get every lead
5. **Deploy → New deployment → Web app.** Execute as: **Me**. Who has access: **Anyone**. Deploy. Copy the web app URL.
6. Paste that URL into `assets/site.js` on the line `var ENDPOINT = '';` and push the site.
7. Test: submit the form on the site. You should see (a) a new row in `Leads`, (b) a summary email,
   (c) a new contact in BoldTrail within a few minutes.

## Routing tab (who gets which lead)

One row per partner agent. A row only fires when `active` is TRUE **and** it has a partner email.
First matching row wins. Leave a row inactive until the broker-to-broker referral agreement with
that partner is signed.

| active | partner_name | partner_email | intent | area_keywords | partner_dropbox_email |
|---|---|---|---|---|---|
| TRUE/FALSE | who | where the intro email goes | Buying / Selling / Both / any | comma list matched against the lead's area + address, or `any` | optional: the partner's own BoldTrail Lead Dropbox address, so the contact is created in their CRM too |

Leads that match no active row go only to you.

## Changing the code later

After editing `Code.gs` in the script editor: **Deploy → Manage deployments → edit (pencil) → Version: New version → Deploy.**
The URL stays the same.

## Limits

Free Gmail accounts can send about 100 emails/day from Apps Script. Each lead uses 2–4. That is far more headroom than needed.
