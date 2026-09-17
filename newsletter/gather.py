"""Saves a dated text snapshot of each source page so the draft can cite what it actually read.

    python newsletter/gather.py 2026-09-24

Writes newsletter/out/<date>/sources/<key>.txt (URL + fetch time on the first lines) and an
INDEX.txt that says which sources answered and which did not. One try per source, short
timeout, no retries, no loops. A source that fails is simply skipped: the rule is
"if you can't verify it, leave it out."
"""
import html
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

# key, who, url, what to look for
SOURCES = [
    ("freddiemac_pmms", "Freddie Mac Primary Mortgage Market Survey", "https://www.freddiemac.com/pmms", "30-yr and 15-yr average, survey date, week-ago and year-ago values. Posts Thursdays about 9am PT."),
    ("car_newsroom", "CALIFORNIA ASSOCIATION OF REALTORS® news releases", "https://www.car.org/aboutus/mediacenter/newsreleases", "Latest monthly home sales and price report (mid-month). Open the newest release; the county table has Sacramento, Placer, El Dorado."),
    ("nar_newsroom", "National Association of REALTORS® newsroom", "https://www.nar.realtor/newsroom", "Existing-home sales, pending home sales, Economists' Outlook."),
    ("fed_press", "Federal Reserve press releases", "https://www.federalreserve.gov/newsevents/pressreleases.htm", "Only in FOMC weeks. The decision sentence only."),
    ("census_newhomes", "U.S. Census Bureau new residential sales", "https://www.census.gov/construction/nrs/current/index.html", "Monthly new-home sales, median new-home price, months' supply."),
    ("mba_newsroom", "Mortgage Bankers Association newsroom", "https://www.mba.org/news-and-research/newsroom", "Weekly Applications Survey (Wednesdays). Often blocks scripts; skip if so."),
    ("fanniemae_research", "Fannie Mae Economic & Strategic Research", "https://www.fanniemae.com/research-and-insights", "Home Purchase Sentiment Index, monthly outlook. Often blocks scripts; skip if so. Their forecasts are THEIR forecasts: link, never restate as fact."),
    ("sar_stats", "Sacramento Association of REALTORS® statistics", "https://www.sacrealtor.org/consumers/housing-statistics", "Monthly county press release. Often blocks scripts; skip if so."),
    ("pcar", "Placer County Association of REALTORS®", "https://www.pcaor.com/", "Public monthly stats if posted."),
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def to_text(page):
    page = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", page)
    page = re.sub(r"(?i)<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", r"\2 [\1]", page, flags=re.S)
    page = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h\d)\b[^>]*>", "\n", page)
    page = html.unescape(re.sub(r"<[^>]+>", " ", page))
    page = re.sub(r"[ \t\r\f]+", " ", page)
    return re.sub(r"\n\s*\n+", "\n", page).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(3_000_000).decode("utf-8", "replace")


def main():
    day = sys.argv[1]
    extra = sys.argv[2:]  # optional: more URLs to snapshot (a specific release page)
    out = HERE / "out" / day / "sources"
    out.mkdir(parents=True, exist_ok=True)
    index = ["Sources gathered %s for issue %s" % (datetime.now().strftime("%Y-%m-%d %H:%M"), day), ""]
    jobs = SOURCES + [("extra_%d" % i, "extra", u, "") for i, u in enumerate(extra, 1)]
    for key, who, url, hint in jobs:
        try:
            text = to_text(fetch(url))
            (out / (key + ".txt")).write_text("SOURCE: %s\nURL: %s\nFETCHED: %s\nLOOK FOR: %s\n\n%s\n" % (who, url, datetime.now().isoformat(timespec="minutes"), hint, text[:60000]), encoding="utf-8")
            index.append("OK    %-20s %s" % (key, url))
        except Exception as e:  # one try only; a miss is recorded, never retried
            index.append("SKIP  %-20s %s  (%s)" % (key, url, str(e)[:80]))
    (out / "INDEX.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    print("\n".join(index))


if __name__ == "__main__":
    main()
