"""Stamps the inner pages of felicianevin.com.

index.html is the single source for the header, footer and <head> links.
Each file in _build/pages/ is a page body with a small header block:

    path: /buy/
    title: ...
    description: ...
    ---
    <html body>

Run:  python _build/build.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index = (ROOT / "index.html").read_text(encoding="utf-8")

header = re.search(r'<a class="skip".*?</header>', index, re.S).group(0)
footer = re.search(r"<footer>.*?</footer>", index, re.S).group(0)
fonts = re.search(r'<link rel="icon".*?site\.css">', index, re.S).group(0)

# inner pages link back to the homepage form
header = header.replace('href="#start"', 'href="/#start"')

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://felicianevin.com{path}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://felicianevin.com{path}">
<meta property="og:image" content="https://felicianevin.com/assets/img/hero-folsom-rainbow-bridge.jpg">
<meta property="og:site_name" content="Felicia Nevin Real Estate">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#10241D">
{fonts}
</head>
<body>
{header}

<main id="main">
{body}
</main>

{footer}
{schema}
<script src="/assets/site.js" defer></script>
</body>
</html>
"""

def schema_for(meta, body):
    url = "https://felicianevin.com" + meta["path"]
    graph = [{
        "@type": "WebPage", "@id": url + "#page", "url": url, "name": meta["title"],
        "description": meta["description"], "inLanguage": "en-US",
        "isPartOf": {"@id": "https://felicianevin.com/#website"},
        "about": {"@id": "https://felicianevin.com/#agent"},
        "author": {"@id": "https://felicianevin.com/#agent"},
    }, {
        "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://felicianevin.com/"},
            {"@type": "ListItem", "position": 2, "name": meta["title"].split(" | ")[0], "item": url}]
    }]
    qa = re.findall(r'<details class="faq">\s*<summary>(.*?)</summary>\s*<div class="body"><p>(.*?)</p>', body, re.S)
    if qa:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
            for q, a in qa]})
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False) + "</script>"


urls = ["/"]
for src in sorted((ROOT / "_build" / "pages").glob("*.html")):
    meta_text, body = src.read_text(encoding="utf-8").split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in meta_text.strip().splitlines())
    nav = header.replace('href="%s"' % meta["path"], 'href="%s" aria-current="page"' % meta["path"])
    is_file = meta["path"].endswith(".html")
    out = ROOT / meta["path"].strip("/") if is_file else ROOT / meta["path"].strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.format(schema="" if is_file else schema_for(meta, body), fonts=fonts, header=nav, footer=footer, body=body.strip(), **meta), encoding="utf-8")
    if not is_file:
        urls.append(meta["path"])
    print("built", meta["path"])

# market updates are stamped by newsletter/build_issue.py --publish
if (ROOT / "market" / "index.html").exists():
    urls.append("/market/")
    urls += ["/market/%s/" % d.parent.name for d in sorted((ROOT / "market").glob("*/index.html"), reverse=True)]

sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sitemap += ["  <url><loc>https://felicianevin.com%s</loc></url>" % u for u in urls]
sitemap.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
(ROOT / "robots.txt").write_text("# AI assistants and search engines are welcome here.\nUser-agent: GPTBot\nUser-agent: OAI-SearchBot\nUser-agent: ChatGPT-User\nUser-agent: ClaudeBot\nUser-agent: Claude-SearchBot\nUser-agent: Claude-User\nUser-agent: PerplexityBot\nUser-agent: Google-Extended\nUser-agent: Applebot-Extended\nUser-agent: CCBot\nAllow: /\nDisallow: /hub/\nDisallow: /listing-checklist/\n\nUser-agent: *\nDisallow: /hub/\nDisallow: /listing-checklist/\nDisallow: /backend/\nDisallow: /_build/\n\nSitemap: https://felicianevin.com/sitemap.xml\n", encoding="utf-8")
print("built sitemap.xml + robots.txt")
