---
name: felicia-newsletter
description: Draft Felicia Nevin's OWN weekly market email (felicianevin.com) - gather cited sources, read her note card, write the issue in her voice, build email + site page + BoldTrail blog + social cuts, save to Drive for her Thursday review. DRAFT ONLY - never sends, posts, publishes, commits, or pushes.
---

# Felicia's weekly market email - draft routine

**The weekly clock (Pacific time):** Wed 6:00pm draft run (this skill) -> Thu ~9:00am Freddie Mac posts the new rate -> Thu 9:30am rate refresh + QA re-run -> Felicia reads + approves Thursday -> she schedules it in BoldTrail (Marketing -> Scheduled Mass Emails) for **FRIDAY 9:30am Pacific / 12:30pm Eastern** -> site page + BoldTrail blog + social cuts Friday. Why Friday: BoldTrail's scheduler needs about 24 hours of lead time, so a same-day Thursday send cannot carry Thursday's rate. SHE picks the recipient hashtag and clicks Schedule herself, always (the hashtag dropdown mis-selects under automation); Claude may load the HTML into the message box (tinymce setContent) and reads back the '# of Contacts' number.

**What this is:** Alex Dyer's note-card method, for Felicia's own business. Note card + reliable sources in, one issue out in five shapes (HTML email, plain text, site page, BoldTrail blog body, social cuts).

**HARD STOPS (read first):**
- DRAFT ONLY. Never send an email, never post to social, never publish to the site, never `git commit` / `git push`, never change a BoldTrail setting. Felicia approves every issue (her standing rule + DRE's 3/17/2026 AI advisory).
- ONE pass. No loops, no retries beyond one, nothing left running in the background. If a step fails twice, write what failed into `RUN-LOG.txt` and stop.
- Done = the files are in Drive and `READY FOR REVIEW.txt` is written. Then STOP.
- Unattended (scheduled) runs: use **PowerShell and Read only** (scheduled runs start in default permission mode and stall on any other tool). Write files with PowerShell/python, fetch the web with `python newsletter/gather.py`. No browser, no MCP tools, no Write/Edit/WebFetch.
- Never type a password. Never contact eXp compliance, CARLO, or broker support.
- Never invent a number. A number with no source page in `sources/` does not go in.

**Paths**
- Repo: `C:\Users\felic\Desktop\Felicia\felicianevin-site` (work in place; do not switch branches; do not touch `assets/site.js`, `backend/`, `CNAME`)
- Drive: `G:\My Drive\REAL ESTATE SYSTEMS\Felicia Nevin - Own Business\Newsletter\`
- Note card she fills in: `<Drive>\NOTE CARD - fill this in.txt` (template: `newsletter/note-card.md`)
- Issue date = the coming Thursday (`YYYY-MM-DD`).

## Steps

1. **Gather.** `python newsletter/gather.py <date>` -> snapshots in `newsletter/out/<date>/sources/` + `INDEX.txt`. Read `INDEX.txt`. For each index page that answered, Read the snapshot, find THIS WEEK's release link (C.A.R. monthly report, NAR release, Fed statement in FOMC weeks, Census new-home sales, MBA weekly survey), then run gather once more with those exact URLs as extra arguments so the release pages themselves are snapshotted. If run on Wednesday night, the Freddie Mac number is LAST Thursday's: write it in, and put `"rates_stale": true` so the Thursday check replaces it.
2. **Read the note card.** Numbers are `this month | last month | same month last year`. Blank = leave `"value": null`. If the whole card is blank, fall back to the C.A.R. county table (median price, median days, unsold inventory index only) and use the C.A.R. attribution line. MLS numbers need the MetroList line from `note-card.md` with the real date range and pull date.
3. **Pick 2 to 3 links** from what was gathered. Only items published in the last ~10 days (monthly reports: the newest one). Every link needs `url`, `published`, `verified_on`, and a 2-sentence `take`.
4. **Write `newsletter/issues/<date>.json`** - copy the shape of the newest file in `newsletter/issues/`. `"status": "draft"` always. You never set "approved".
5. **Build.** `python newsletter/build_issue.py <date> --copy-to "G:\My Drive\REAL ESTATE SYSTEMS\Felicia Nevin - Own Business\Newsletter"`. Read `CHECKS.txt`. Fix every MUST FIX and every wording flag that is a real problem, rebuild ONCE.
5b. **QA.** `python newsletter/gather.py <date> <each release URL used>` (so every cited page is saved), then `python newsletter/qa_issue.py <date>`. Every number must be found on its own source page and every compliance line must PASS. The only allowed FAIL in a draft is "a licensed human approved" (that is Felicia's job). Fix anything else and re-run ONCE. Copy `QA-REPORT.txt` + `QA-REPORT.html` to the Drive folder.
6. **Hand off.** Write `<Drive>\<date>\READY FOR REVIEW.txt`: what's in the issue, every source with URL + publish date, anything skipped and why, anything she must check by eye (rate number if stale, any big or surprising figure), and her Thursday steps (below). Then stop. Do NOT run `--publish`.

## Writing rules (all of them, every issue)

- **Her voice, high-school reading level.** Short sentences. Everyday words. One idea at a time. If she would have to reread it, rewrite it. No em dashes. No exclamation points except a real thank-you. "I", not "we". Never "my team".
- **Teach, don't sell.** The reader should finish knowing something new. ONE call to action in the whole email (reply / ask a question). No "send this to a friend", no "call me today".
- **She is the middleman.** Summarize in our own words and point to the source. Never copy a paragraph. At most ONE direct quote per issue, under 15 words, in the `quote` field.
- **Look back, never forward.** No predictions, no "will", no "expected to", no "great time to buy". Someone else's forecast can be linked as THEIR forecast, never restated as fact.
- **No rate advice.** She is not a lender. Report the Freddie Mac average, show the math on a sample payment, say "ask a licensed loan officer". Never "lock", "wait", "refinance now".
- **Fair Housing filter (absolute).** Describe the market and homes. Never people, never neighborhood character: no "safe", "family-friendly", "good schools", "up-and-coming", "improving/declining area". Read the finished draft once as a Fair Housing reviewer.
- **▲▼ are neutral.** Up is not "good". Say who it helps: "good news if you're selling, harder if you're buying".
- **Small numbers jump.** If a county's median moved more than ~5% in a month, say that one month can swing a small county and point to the year-over-year number.
- **Interpret every number** in one plain line (what it means for a buyer or seller). See the guide PDF in Drive for the wording patterns.
- Footer, DRE lines, address, EHO, unsubscribe tag and the eXp "opinions are my own" line live in `template.html`. Never edit them in an issue.
- REALTOR® appears only inside an association's name.

## Felicia's Thursday (what READY FOR REVIEW tells her)

1. Open `email.html` from the Drive folder in Chrome. Read it top to bottom. Open `CHECKS.txt`.
2. After ~9am PT, check the Freddie Mac number at freddiemac.com/pmms. Tell Claude "update the rate" if it changed.
3. Tell Claude what to change, or say "approved". Only then: Claude sets `"status": "approved"`, runs `--publish`, shows her the site page, and she OKs the commit + push.
4. BoldTrail -> Marketing -> Scheduled Mass Emails -> + Schedule Email -> SHE picks hashtag `#newsletter` and checks the chip -> date = Friday, time = 12:30 pm (ET) -> ask Claude to "load this week's email" into the message box (never copy from the Chrome view of the file; that loses all formatting) -> SHE clicks Schedule -> check '# of Contacts'.
5. BoldTrail blog: new post, paste `blog-boldtrail.html` in source view.
6. Post the cuts in `social.md` (Facebook, Instagram, LinkedIn, Google Business Profile) after the site page is live.
7. New subscribers: Leads sheet rows with `newsletter` = yes -> add to BoldTrail with hashtag `#newsletter`.

**Do not bulk-send from a gmail.com address.** First real send waits for felicia@felicianevin.com on Google Workspace with SPF `v=spf1 include:_spf.google.com include:sendgrid.net ip4:198.202.27.0/24 ~all` + DKIM + DMARC.

Log minutes to `C:\Users\felic\.claude\time-ledger\YYYY-MM.csv` (agent `Felicia`, category `content`).
