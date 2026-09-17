"""Builds one issue of Felicia's weekly market email from newsletter/issues/<date>.json.

    python newsletter/build_issue.py 2026-09-17              draft: everything goes to newsletter/out/<date>/
    python newsletter/build_issue.py 2026-09-17 --copy-to "G:\\My Drive\\...\\Newsletter"
    python newsletter/build_issue.py 2026-09-17 --publish    only after Felicia approves (status: "approved")

Draft output (newsletter/out/ is gitignored, so drafts never reach the live site):
    email.html            paste into BoldTrail mass email (HTML view)
    email.txt             plain-text twin
    blog-boldtrail.html   body-only HTML for the BoldTrail blog editor
    page-preview.html     what /market/<date>/ will look like
    social.md             Facebook, Instagram, LinkedIn, Google Business Profile cuts
    CHECKS.txt            what the build flagged; read this first

--publish writes /market/<date>/index.html + the /market/ index and re-runs _build/build.py for
the sitemap. It refuses unless status is "approved", nothing is a placeholder, and the wording
checks are clean. This script never sends, posts, commits, or pushes anything.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = "https://felicianevin.com"
ID_LINE = "Felicia Nevin | CA DRE #01961050 | eXp Realty of California, Inc. | CA DRE #01878277"

# key, label, kind (how the value and its change are written)
METRICS = [
    ("median_price", "Median sold price", "money"),
    ("new_listings", "New listings", "count"),
    ("pendings", "Homes that went pending", "count"),
    ("days_on_market", "Days on market", "days"),
    ("months_inventory", "Months of homes for sale", "months"),
    ("sale_to_list", "Sold price vs. asking price", "pct"),
]

# Wording the drafter must not use. Left side is a regex, right side is why.
LINT = [
    (r"\bwill (rise|fall|drop|climb|go up|go down|crash|increase|decrease)\b", "prediction"),
    (r"\b(is|are) going to (rise|fall|drop|climb|crash)\b", "prediction"),
    (r"\b(expect|expected|forecast|predict)\w*\b", "prediction or forecast talk; link to the source's own forecast instead"),
    (r"\bguarantee", "guarantee"),
    (r"\b(best|great|perfect|right) time to (buy|sell)\b", "advice/prediction"),
    (r"\bnow is the time\b", "advice/prediction"),
    (r"\b(lock in|lock your rate|you should refinance|refinance now|wait for rates)\b", "rate advice; she is not a lender"),
    (r"\b(safe|family[- ]friendly|good schools?|bad schools?|up[- ]and[- ]coming|desirable|exclusive|nice area|good neighborhood|bad neighborhood)\b", "Fair Housing: describe homes and the market, never people or neighborhood character"),
    (r"\b(trending up|trending down|improving|declining|sliding)\b", "Fair Housing flag from 2026: never about a neighborhood; fine only for a number, so re-read"),
    (r"\b(top agent|#1|number one|best agent)\b", "unverified claim"),
    (r"\bmy team\b", "no registered team name"),
    (r"\bREALTOR\b", "trademark: site uses 'California real estate agent' (OK only inside an association's name)"),
    (r"—", "em dash; her copy uses periods and commas"),
]


def esc(s):
    return html.escape(str(s), quote=True)


def md_inline(s):
    """Escape, then allow **bold** only."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))


def render(tpl, ctx):
    def block(m):
        val = ctx.get(m.group(1))
        if not val:
            return ""
        items = val if isinstance(val, list) else [val]
        return "".join(render(m.group(2), {**ctx, **it}) for it in items)
    tpl = re.sub(r"<!--\[(\w+)\]-->(.*?)<!--\[/\1\]-->", block, tpl, flags=re.S)
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(ctx.get(m.group(1), "")), tpl)


# ---------- numbers ----------
def fmt_value(kind, v):
    if kind == "money":
        return "${:,.0f}".format(v)
    if kind == "count":
        return "{:,.0f}".format(v)
    if kind == "days":
        return "{:g} days".format(v)
    if kind == "months":
        return "{:g} months".format(v)
    return "{:g}%".format(v)


def fmt_delta(kind, now, prev, versus):
    if prev is None:
        return ""
    diff = now - prev
    if kind in ("money", "count"):
        amt = abs(diff) / prev * 100 if prev else 0
        text = "{:.1f}%".format(amt)
        flat = amt < 0.05
    else:
        unit = {"days": " days", "months": " mo", "pct": " pts"}[kind]
        text = "{:g}{}".format(round(abs(diff), 1), unit)
        flat = abs(diff) < 0.05
    if flat:
        return "● no change vs. " + versus
    return ("▲ up " if diff > 0 else "▼ down ") + text + " vs. " + versus


def default_meaning(key, m):
    v = m["value"]
    if key == "median_price":
        return "Half of the homes sold for more than this. Half sold for less."
    if key == "new_listings":
        return "How many homes came on the market. More listings means more choices for buyers."
    if key == "pendings":
        return "Homes that got an accepted offer. It's the freshest sign of how busy buyers are."
    if key == "days_on_market":
        return "A typical home sold in about {:g} days.".format(v)
    if key == "months_inventory":
        return "If no new homes were listed, it would take about {:g} months to sell what's for sale now.".format(v)
    return "On average, sellers got about {:g}% of their asking price.".format(v)


def build_counties(local, final):
    out = []
    for c in local["counties"]:
        tiles, missing = [], []
        for key, label, kind in METRICS:
            m = c["metrics"].get(key) or {}
            if m.get("value") is None:
                missing.append(label)
                continue
            tiles.append({"label": esc(label), "value": fmt_value(kind, m["value"]),
                          "delta_mom": fmt_delta(kind, m["value"], m.get("prev_month"), "last month"),
                          "delta_yoy": fmt_delta(kind, m["value"], m.get("prev_year"), "last year"),
                          "meaning": md_inline(m.get("meaning") or default_meaning(key, m))})
        rows = []
        for i in range(0, len(tiles), 2):
            pair = tiles[i:i + 2]
            for j, t in enumerate(pair):
                t["cellw"] = "50%" if len(pair) == 2 else "100%"
                t["cellpad"] = "0 5px 10px 0" if j == 0 and len(pair) == 2 else ("0 0 10px 5px" if j == 1 else "0 0 10px 0")
            rows.append({"tiles": pair})
        # drafts say plainly what is still needed; a published issue just leaves those tiles out
        note = None if final or not missing else {"missing_list": esc(", ".join(missing))}
        moi = (c["metrics"].get("months_inventory") or {}).get("value")
        meter = None
        if moi is not None:
            meter = {"moi": "{:g}".format(moi), "pct": max(0, round(min(moi, 8) / 8 * 100 - 1.5, 1)), "pct_site": round(min(moi, 8) / 8 * 100, 1)}
        out.append({"name": c["name"], "takeaway": c.get("takeaway", ""), "rows": rows, "tiles_flat": tiles, "meter": meter, "missing_note": note})
    return out


# ---------- checks ----------
def check(issue):
    problems, warnings = [], []
    for f in ("date", "headline", "intro", "rates", "local", "links", "tip", "cta", "subject", "preheader"):
        if not issue.get(f):
            problems.append("missing field: " + f)
    if problems:
        return problems, warnings
    if len(issue["intro"]) != 3:
        warnings.append("intro should be exactly 3 sentences (design), found %d" % len(issue["intro"]))
    if not 2 <= len(issue["links"]) <= 3:
        warnings.append("design calls for 2 to 3 curated links, found %d" % len(issue["links"]))
    for i, l in enumerate(issue["links"], 1):
        for f in ("source", "title", "url", "published", "take", "verified_on"):
            if not l.get(f):
                problems.append("link %d has no '%s' (every claim needs a URL, a publish date, and the day it was checked)" % (i, f))
        if l.get("quote") and len(l["quote"].split()) > 14:
            problems.append("link %d quote is over 14 words" % i)
    quotes = sum(1 for l in issue["links"] if l.get("quote"))
    if quotes > 1:
        problems.append("more than one direct quote in the issue (limit is one short quote)")
    r = issue["rates"]
    for f in ("survey_date", "rate30", "rate15", "source_url", "meaning"):
        if r.get(f) is None:
            problems.append("rates." + f + " missing")
    if r.get("rates_stale") or issue.get("rates_stale"):
        problems.append("mortgage rate is last week's number (drafted before Thursday's Freddie Mac release). Update it, then remove rates_stale.")
    loc = issue["local"]
    if loc.get("placeholder"):
        problems.append("local numbers are marked PLACEHOLDER (sample data). Cannot publish.")
    if not loc.get("attribution") or not loc.get("period"):
        problems.append("local numbers need an attribution line and a date range")
    missing = [c["name"] + ": " + k for c in loc["counties"] for k, _, _ in METRICS if (c["metrics"].get(k) or {}).get("value") is None]
    if missing:
        warnings.append("no number yet for: " + "; ".join(missing) + " (shown as 'Needs MetroList' in the draft, dropped on publish)")

    def walk(o, path=""):
        if isinstance(o, str):
            yield path, o
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("url", "source_url", "attribution", "source", "title"):
                    yield from walk(v, path + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from walk(v, "%s[%d]" % (path, i))
    for path, text in walk(issue):
        for pat, why in LINT:
            for m in re.finditer(pat, text, re.I):
                warnings.append("wording %s: \"%s\" -> %s" % (path, m.group(0), why))
    return problems, warnings


# ---------- outputs ----------
def long_date(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")


def rate_lines(r, key):
    now = r[key]
    def d(prev, versus):
        if prev is None:
            return ""
        diff = round(now - prev, 2)
        if diff == 0:
            return "● no change vs. " + versus
        return ("▲ up " if diff > 0 else "▼ down ") + "{:.2f} pts vs. ".format(abs(diff)) + versus
    return d(r.get(key + "_prev"), "last week"), d(r.get(key + "_year"), "a year ago")


def context(issue, final):
    r = issue["rates"]
    w30, y30 = rate_lines(r, "rate30")
    w15, y15 = rate_lines(r, "rate15")
    loc = issue["local"]
    banner = ""
    if loc.get("placeholder"):
        banner = ('<div style="margin-top:12px;background:#10241D;color:#EDE6D6;border-radius:10px;padding:10px 14px;font-family:Arial,Helvetica,sans-serif;'
                  'font-size:13px;line-height:19px;"><strong style="color:#D98B4A;">SAMPLE NUMBERS.</strong> These are placeholders, not real market data. Do not send.</div>')
    return {
        "subject": esc(issue["subject"]), "preheader": esc(issue["preheader"]),
        "newsletter_name": esc(issue.get("newsletter_name", "Weekly market email")),
        "date_long": long_date(issue["date"]), "headline": esc(issue["headline"]),
        "intro": " ".join(md_inline(s) for s in issue["intro"]),
        "rate30": "{:.2f}%".format(r["rate30"]), "rate15": "{:.2f}%".format(r["rate15"]),
        "rate30_wk": w30, "rate30_yr": y30, "rate15_wk": w15, "rate15_yr": y15,
        "rate_meaning": md_inline(r["meaning"]), "rate_url": esc(r["source_url"]), "rate_date": long_date(r["survey_date"]),
        "local_period": esc(loc["period"]), "placeholder_banner": banner,
        "attribution": md_inline(loc["attribution"]),
        "counties": [{**c, "name": esc(c["name"]), "takeaway": md_inline(c["takeaway"])} for c in build_counties(loc, final)],
        "links": [{"source": esc(l["source"]), "published": "published " + long_date(l["published"]), "title": esc(l["title"]),
                   "take": md_inline(l["take"]) + ((' <em>&ldquo;%s&rdquo;</em>' % esc(l["quote"])) if l.get("quote") else ""), "url": esc(l["url"])} for l in issue["links"]],
        "tip_title": esc(issue["tip"]["title"]), "tip_text": md_inline(issue["tip"]["text"]),
        "tip_url": esc(abs_url(issue["tip"]["url"])), "tip_link_text": esc(issue["tip"].get("link_text", "Read the plain-language guide")) + " →",
        "cta_text": md_inline(issue["cta"]["text"]), "cta_button": esc(issue["cta"]["button"]), "cta_url": esc(abs_url(issue["cta"]["url"])),
        "page_url": "%s/market/%s/" % (SITE, issue["date"]),
    }


def abs_url(u):
    return SITE + u if u.startswith("/") else u


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def plain_text(issue, ctx):
    L = [ctx["newsletter_name"].upper() + " | " + ctx["date_long"], "Felicia Nevin, California real estate", "", strip_tags(ctx["headline"]).upper(), "",
         strip_tags(ctx["intro"]), "", "MORTGAGE RATES (U.S. weekly average)",
         "30-year fixed: %s  (%s; %s)" % (ctx["rate30"], ctx["rate30_wk"], ctx["rate30_yr"]),
         "15-year fixed: %s  (%s; %s)" % (ctx["rate15"], ctx["rate15_wk"], ctx["rate15_yr"]),
         "What this means: " + strip_tags(ctx["rate_meaning"]),
         "Source: Freddie Mac Primary Mortgage Market Survey, week of %s: %s" % (ctx["rate_date"], issue["rates"]["source_url"]),
         "A national average, not a rate quote. I'm not a lender.", "", "LOCAL NUMBERS | " + issue["local"]["period"]]
    if issue["local"].get("placeholder"):
        L.append("*** SAMPLE NUMBERS. PLACEHOLDERS. DO NOT SEND. ***")
    for c in ctx["counties"]:
        L += ["", strip_tags(c["name"]).upper(), strip_tags(c["takeaway"])]
        for t in c["tiles_flat"]:
            L.append("- %s: %s" % (strip_tags(t["label"]), strip_tags(t["value"])))
            L.append("    %s | %s" % (strip_tags(t["delta_mom"]), strip_tags(t["delta_yoy"])))
            L.append("    " + strip_tags(t["meaning"]))
        if c["missing_note"]:
            L.append("  [DRAFT NOTE: still needed from MetroList: %s]" % strip_tags(c["missing_note"]["missing_list"]))
    L += ["", strip_tags(ctx["attribution"]), "", "WORTH YOUR TIME"]
    for l in ctx["links"]:
        L += ["", "%s (%s, %s)" % (strip_tags(l["title"]), strip_tags(l["source"]), l["published"]), strip_tags(l["take"]), html.unescape(l["url"])]
    L += ["", "GOOD TO KNOW: " + strip_tags(ctx["tip_title"]), strip_tags(ctx["tip_text"]), html.unescape(ctx["tip_url"]), "",
          strip_tags(ctx["cta_text"]), html.unescape(ctx["cta_url"]), "", "--",
          "Felicia Nevin · California Real Estate Salesperson · CA DRE #01961050", "eXp Realty of California, Inc. · CA DRE #01878277",
          "2603 Camino Ramon, Suite 200, San Ramon, CA 94583", "Equal Housing Opportunity", "",
          "Opinions are my own and not the views of eXp Realty. General information, not legal, tax, lending, or financial advice. "
          "Market numbers look back at what already happened. They are not a prediction. Data is deemed reliable but not guaranteed.", "",
          "You signed up at felicianevin.com. Unsubscribe: {unsubscribe_url}"]
    return "\n".join(L) + "\n"


def article_html(issue, ctx, for_site):
    """Shared body for the site page and the BoldTrail blog (plain tags + the site's classes)."""
    h = []
    h.append('<p class="lede">%s</p>' % ctx["intro"])
    h.append('<h2>Mortgage rates this week</h2>')
    h.append('<div class="ratecard"><div><span class="big">%s</span><span class="lbl">30-year fixed</span><span class="chg">%s<br>%s</span></div>'
             '<div><span class="mid">%s</span><span class="lbl">15-year fixed</span><span class="chg">%s<br>%s</span></div></div>'
             % (ctx["rate30"], ctx["rate30_wk"], ctx["rate30_yr"], ctx["rate15"], ctx["rate15_wk"], ctx["rate15_yr"]))
    h.append('<p><strong>What this means:</strong> %s</p>' % ctx["rate_meaning"])
    h.append('<p class="src">Source: <a href="%s" rel="noopener">Freddie Mac Primary Mortgage Market Survey</a>, week of %s. A national average, not a rate quote. I\'m not a lender. Ask a licensed loan officer about your own rate.</p>' % (ctx["rate_url"], ctx["rate_date"]))
    h.append('<h2>Local numbers: %s</h2>' % ctx["local_period"])
    h.append('<p>▲ means the number went up. ▼ means it went down. Neither one is "good" or "bad" by itself. It depends on whether you\'re buying or selling.</p>')
    if issue["local"].get("placeholder"):
        h.append('<p class="note"><strong>SAMPLE NUMBERS.</strong> Placeholders, not real market data.</p>')
    for c in ctx["counties"]:
        h.append('<h3>%s</h3><p>%s</p><div class="stats">' % (c["name"], c["takeaway"]))
        for t in c["tiles_flat"]:
            h.append('<div class="stat"><span class="lbl">%s</span><span class="val">%s</span><span class="chg">%s<br>%s</span><span class="mean">%s</span></div>'
                     % (t["label"], t["value"], t["delta_mom"], t["delta_yoy"], t["meaning"]))
        h.append('</div>')
        if c["missing_note"]:
            h.append('<p class="draftnote"><strong>Draft note (not shown once published):</strong> still needed from MetroList: %s. No number was made up.</p>' % c["missing_note"]["missing_list"])
        if c["meter"]:
            h.append('<div class="meter" role="img" aria-label="%s months of homes for sale. Under 3 favors sellers, 3 to 6 is balanced, over 6 favors buyers.">'
                     '<span class="cap">Who has the edge? Months of homes for sale: <strong>%s</strong></span>'
                     '<span class="mark" style="left:%s%%">▼</span><div class="zones"><span>Sellers\' edge · under 3</span><span>Balanced · 3 to 6</span><span>Buyers\' edge · 6+</span></div></div>'
                     % (c["meter"]["moi"], c["meter"]["moi"], c["meter"]["pct_site"]))
    h.append('<p class="src">%s The "edge" scale is a common rule of thumb, not a hard line.</p>' % ctx["attribution"])
    if issue["local"].get("trendvision_embed"):
        h.append('<h3>Five-year trend</h3>' + issue["local"]["trendvision_embed"])
    h.append('<h2>Worth your time</h2>')
    for l in ctx["links"]:
        h.append('<div class="note"><span class="src">%s · %s</span><h3>%s</h3><p>%s</p><p><a href="%s" rel="noopener">Read it at the source →</a></p></div>' % (l["source"], l["published"], l["title"], l["take"], l["url"]))
    h.append('<h2>Good to know: %s</h2><p>%s <a href="%s">%s</a></p>' % (ctx["tip_title"], ctx["tip_text"], issue["tip"]["url"] if for_site else ctx["tip_url"], ctx["tip_link_text"]))
    h.append('<p>%s</p><p><a class="btn pri" href="%s">%s</a></p>' % (md_inline(issue["cta"].get("text_web") or issue["cta"]["text"]), issue["cta"]["url"] if for_site else ctx["cta_url"], ctx["cta_button"]))
    return "\n".join(h)


def site_shell():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    header = re.search(r'<a class="skip".*?</header>', index, re.S).group(0).replace('href="#start"', 'href="/#start"')
    header = header.replace('href="/market/"', 'href="/market/" aria-current="page"')
    footer = re.search(r"<footer>.*?</footer>", index, re.S).group(0)
    fonts = re.search(r'<link rel="icon".*?site\.css">', index, re.S).group(0)
    return header, footer, fonts


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{robots}<link rel="canonical" href="{url}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://felicianevin.com/assets/img/hero-folsom-rainbow-bridge.jpg">
<meta property="og:site_name" content="Felicia Nevin Real Estate">
{article_meta}<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#10241D">
{fonts}
</head>
<body>
{header}

<main id="main">
{body}
</main>

{footer}
<script type="application/ld+json">{schema}</script>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""

SIGNUP = """<section class="dark" id="newsletter">
  <div class="wrap why">
    <div>
      <span class="eyebrow">Weekly market email</span>
      <h2>Get this in your inbox once a week.</h2>
      <p style="color:var(--cream)">Local numbers, mortgage rates, and the few stories worth your time. Plain language. Unsubscribe with one click.</p>
    </div>
    <div class="card">
      <form class="lead-form" data-form="newsletter-market" novalidate>
        <input type="hidden" name="intent" value="Newsletter">
        <input type="hidden" name="newsletter" value="yes">
        <div class="two">
          <input class="fld" type="text" name="name" placeholder="First name" aria-label="First name" autocomplete="given-name" required>
          <input class="fld" type="email" name="email" placeholder="Email" aria-label="Email" autocomplete="email" required>
        </div>
        <input class="fld" type="text" name="area" placeholder="City or area you care about (optional)" aria-label="City or area, optional">
        <div class="hp" aria-hidden="true"><label>Leave this empty <input type="text" name="company" tabindex="-1" autocomplete="off"></label></div>
        <button class="btn pri go" type="submit">Sign me up</button>
        <div class="form-msg" role="status" aria-live="polite"></div>
        <p class="fine">Email only. I don't sell your information. See the <a href="/privacy/">privacy policy</a>.</p>
        <p class="idline">Felicia Nevin · CA DRE #01961050 · eXp Realty of California, Inc. · CA DRE #01878277</p>
      </form>
    </div>
  </div>
</section>"""


def site_page(issue, ctx, preview):
    header, footer, fonts = site_shell()
    url = "%s/market/%s/" % (SITE, issue["date"])
    title = "%s | Sacramento Region Market Update, %s" % (issue["headline"], long_date(issue["date"]))
    body = ('<section class="page-head"><div class="wrap"><span class="eyebrow">Market update · %s</span><h1>%s</h1>'
            '<p>By Felicia Nevin, California real estate agent. Sacramento, Placer, and El Dorado counties.</p></div></section>\n'
            '<section><div class="wrap"><article class="prose market">\n%s\n</article></div></section>\n%s'
            % (ctx["date_long"], ctx["headline"], article_html(issue, ctx, True), SIGNUP))
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "BlogPosting", "@id": url + "#post", "mainEntityOfPage": url, "url": url, "headline": issue["headline"][:110],
         "description": issue["preheader"], "datePublished": issue["date"], "dateModified": issue["date"], "inLanguage": "en-US",
         "image": SITE + "/assets/img/hero-folsom-rainbow-bridge.jpg", "author": {"@id": SITE + "/#agent"}, "publisher": {"@id": SITE + "/#agent"},
         "isPartOf": {"@id": SITE + "/#website"}, "about": ["Sacramento County housing market", "Placer County housing market", "El Dorado County housing market", "Mortgage rates"],
         "citation": [issue["rates"]["source_url"]] + [l["url"] for l in issue["links"]] + ([issue["local"]["source_url"]] if issue["local"].get("source_url") else [])},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Market updates", "item": SITE + "/market/"},
            {"@type": "ListItem", "position": 3, "name": issue["headline"], "item": url}]}]}
    return PAGE.format(title=esc(title), description=esc(issue["preheader"]), url=url, ogtype="article", fonts=fonts, header=header, footer=footer, body=body,
                       robots='<meta name="robots" content="noindex">\n' if preview else "",
                       article_meta='<meta property="article:published_time" content="%s">\n<meta property="article:author" content="Felicia Nevin">\n' % issue["date"],
                       schema=json.dumps(schema, ensure_ascii=False))


def market_index():
    header, footer, fonts = site_shell()
    posts = []
    for d in sorted((ROOT / "market").glob("*/index.html"), reverse=True):
        src = HERE / "issues" / (d.parent.name + ".json")
        if src.exists():
            posts.append(json.loads(src.read_text(encoding="utf-8")))
    if posts:
        items = "\n".join('<a class="tile" href="/market/%s/"><span class="eyebrow">%s</span><h3>%s</h3><p>%s</p><span class="more">Read the update</span></a>'
                          % (p["date"], long_date(p["date"]), esc(p["headline"]), esc(p["preheader"])) for p in posts)
        listing = '<div class="grid2">%s</div>' % items
    else:
        listing = '<p class="sec-head center" style="margin-top:0">The first update is on its way. Sign up below and it will land in your inbox.</p>'
    url = SITE + "/market/"
    desc = "Weekly Sacramento-region housing market updates in plain language: local home prices, days on market, homes for sale, and mortgage rates, with links to the original sources."
    body = ('<section class="page-head"><div class="wrap"><span class="eyebrow">Market updates</span><h1>The Sacramento-region market, in plain language.</h1>'
            '<p>Once a week: what homes are doing in Sacramento, Placer, and El Dorado counties, where mortgage rates are, and what it means. Every number links back to where it came from.</p></div></section>\n'
            '<section class="band"><div class="wrap">%s</div></section>\n%s' % (listing, SIGNUP))
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "Blog", "@id": url + "#blog", "url": url, "name": "Sacramento Region Market Updates", "description": desc, "inLanguage": "en-US",
         "author": {"@id": SITE + "/#agent"}, "isPartOf": {"@id": SITE + "/#website"},
         "blogPost": [{"@type": "BlogPosting", "headline": p["headline"], "url": "%s/market/%s/" % (SITE, p["date"]), "datePublished": p["date"]} for p in posts]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Market updates", "item": url}]}]}
    out = ROOT / "market" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.format(title="Sacramento Region Housing Market Updates | Felicia Nevin", description=esc(desc), url=url, ogtype="website", fonts=fonts,
                               header=header, footer=footer, body=body, robots="", article_meta="", schema=json.dumps(schema, ensure_ascii=False)), encoding="utf-8")


def headline_numbers(issue):
    lines = []
    for c in issue["local"]["counties"]:
        p = (c["metrics"].get("median_price") or {})
        d = (c["metrics"].get("days_on_market") or {})
        if p.get("value") is not None:
            s = "%s: median sold price %s" % (c["name"], fmt_value("money", p["value"]))
            if d.get("value") is not None:
                s += ", about %g days to sell" % d["value"]
            lines.append(s)
    return lines


def social(issue, ctx):
    s = issue.get("social", {})
    url = ctx["page_url"]
    intro = " ".join(issue["intro"][:2])  # the third sentence points "below", which only makes sense in the email
    nums = headline_numbers(issue)
    mean2 = " ".join(re.split(r"(?<=[.!?])\s+", issue["rates"]["meaning"])[:2])
    rate = "30-year fixed mortgage average: %s (Freddie Mac, week of %s)" % (ctx["rate30"], ctx["rate_date"])
    attrib = strip_tags(ctx["attribution"])
    fb = s.get("facebook") or "%s\n\n%s\n%s\n\nWhat each number means, in plain language, plus this week's reads: %s\n\n%s\n%s" % (intro, "\n".join("• " + n for n in nums), "• " + rate, url, attrib, ID_LINE)
    slides = s.get("instagram_slides") or ([issue["headline"]] + nums + [rate, "What it means: " + mean2, "Full update + sources at felicianevin.com/market"])
    ig = s.get("instagram") or "%s\n\nFull update with sources: felicianevin.com/market (link in bio)\n\n%s\n%s\n\n#sacramentorealestate #placercounty #eldoradocounty #rosevilleca #folsomca #housingmarket #mortgagerates" % (intro, attrib, ID_LINE)
    li = s.get("linkedin") or "%s\n\nThe numbers I'm watching (%s):\n%s\n%s\n\nI wrote up what each one means in plain language, with links to every source: %s\n\n%s\n%s" % (intro, issue["local"]["period"], "\n".join("• " + n for n in nums), "• " + rate, url, attrib, ID_LINE)
    gbp = s.get("gbp") or "%s\n\n%s\n%s\n\n%s\n%s" % (intro, "\n".join("• " + n for n in nums), "• " + rate, attrib, ID_LINE)
    warn = ""
    if len(gbp) > 1500:
        warn = "\n> ⚠ Google Business Profile post is %d characters. Limit is 1,500. Trim it.\n" % len(gbp)
    return """# Social cuts for {date}  (DRAFTS. Felicia posts these herself after she approves the issue.)

Post AFTER the site page is live so the link works: {url}
Every post keeps the name + DRE + broker line (first-point-of-contact rule). Photos: real local photos only, no AI scenery.
{warn}
---
## Facebook (Page post, link to the site page)

{fb}

---
## Instagram (carousel text, one line per slide, then the caption)

{slides}

**Caption:**

{ig}

---
## LinkedIn

{li}

---
## Google Business Profile update  (button: "Learn more" -> {url})

{gbp}
""".format(date=issue["date"], url=url, warn=warn, fb=fb, slides="\n".join("%d. %s" % (i, t) for i, t in enumerate(slides, 1)), ig=ig, li=li, gbp=gbp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?")
    ap.add_argument("--index", action="store_true", help="only rebuild the /market/ index page")
    ap.add_argument("--publish", action="store_true", help="write /market/<date>/ (needs status approved + clean checks)")
    ap.add_argument("--copy-to", help="also copy the draft folder here (e.g. the Drive newsletter folder)")
    a = ap.parse_args()
    if a.index or not a.date:
        market_index()
        print("built /market/ index")
        return

    issue = json.loads((HERE / "issues" / (a.date + ".json")).read_text(encoding="utf-8"))
    problems, warnings = check(issue)
    if any(p.startswith("missing field") for p in problems):
        sys.exit("Cannot build:\n  " + "\n  ".join(problems))

    out = HERE / "out" / a.date
    out.mkdir(parents=True, exist_ok=True)
    ctx = context(issue, final=a.publish)
    (out / "email.html").write_text(render((HERE / "template.html").read_text(encoding="utf-8"), ctx), encoding="utf-8")
    (out / "email.txt").write_text(plain_text(issue, ctx), encoding="utf-8")
    (out / "blog-boldtrail.html").write_text(
        "<!-- Paste into the BoldTrail blog editor (HTML/source view). Title: %s -->\n<p><em>First published at <a href=\"%s\">felicianevin.com/market</a>.</em></p>\n%s\n<p><small>%s</small></p>\n"
        % (esc(issue["headline"]), ctx["page_url"], article_html(issue, ctx, False), ID_LINE.replace("|", "·")), encoding="utf-8")
    (out / "page-preview.html").write_text(site_page(issue, ctx, preview=True), encoding="utf-8")
    (out / "social.md").write_text(social(issue, ctx), encoding="utf-8")
    (out / "social.txt").write_text(social(issue, ctx), encoding="utf-8")  # same thing; opens in Notepad
    size_kb = (out / "email.html").stat().st_size / 1024
    if size_kb > 95:
        warnings.append("email.html is %.0f KB. Gmail clips emails over about 102 KB." % size_kb)
    report = ["Issue %s | status: %s | email.html %.0f KB" % (a.date, issue.get("status", "draft"), size_kb), "",
              "MUST FIX BEFORE PUBLISH (%d):" % len(problems)] + ["  - " + p for p in problems] + ["", "READ AND DECIDE (%d):" % len(warnings)] + ["  - " + w for w in warnings] + [
              "", "Nothing was sent, posted, committed, or pushed. Felicia approves every issue."]
    (out / "CHECKS.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

    if a.copy_to:
        dest = Path(a.copy_to) / a.date
        dest.mkdir(parents=True, exist_ok=True)
        for f in out.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
        shutil.copy2(HERE / "issues" / (a.date + ".json"), dest / "issue.json")
        print("copied draft to", dest)

    if a.publish:
        if issue.get("status") != "approved":
            sys.exit('\nNOT published: status is "%s". Felicia sets "status": "approved" in the issue file after she reads it.' % issue.get("status", "draft"))
        if problems:
            sys.exit("\nNOT published: fix the items above first.")
        page = ROOT / "market" / a.date / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(site_page(issue, ctx, preview=False), encoding="utf-8")
        market_index()
        subprocess.run([sys.executable, str(ROOT / "_build" / "build.py")], check=True)
        print("published /market/%s/ locally. Review, then commit and push by hand." % a.date)


if __name__ == "__main__":
    main()
