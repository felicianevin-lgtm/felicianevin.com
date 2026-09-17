# Weekly market email

Felicia's own newsletter, built the note-card way: one issue file in, five outputs out. **Nothing here sends, posts, or publishes by itself.**

| File | What it is |
|---|---|
| `template.html` | The email. Tables + inline CSS, 600px, Sierra brand. Footer carries name, both DRE numbers, broker address, EHO, the eXp "opinions" line and BoldTrail's `{unsubscribe_url}` tag. |
| `note-card.md` | The weekly inputs (MetroList TrendVision numbers + her take). |
| `issues/<date>.json` | One issue: her take, numbers, links with URL + publish date, tip, CTA. `status` is `draft` until she approves. |
| `gather.py` | Saves a dated text snapshot of each source page. One try each, no loops. |
| `build_issue.py` | Builds `out/<date>/`: `email.html`, `email.txt`, `blog-boldtrail.html`, `page-preview.html`, `social.md`, `CHECKS.txt`. `--publish` (approved issues only) writes `/market/<date>/`, the `/market/` index and the sitemap. |
| `guide/` | "How to read your market numbers" (her PDF cheat sheet, source HTML). |
| `ROUTINE.md` | The weekly routine (copy of the `felicia-newsletter` skill). |

`out/` is gitignored and `/newsletter/` is disallowed in robots.txt, so drafts never reach the live site.

```
python newsletter/gather.py 2026-09-24
python newsletter/build_issue.py 2026-09-24
python newsletter/build_issue.py 2026-09-24 --publish   # only after "status": "approved"
```
