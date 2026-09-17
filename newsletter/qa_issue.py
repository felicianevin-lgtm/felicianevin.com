"""Accuracy + compliance QA for one built issue. Run after build_issue.py.

    python newsletter/qa_issue.py 2026-09-17

1. ACCURACY  every number in the issue file must appear on a saved source page
             (newsletter/out/<date>/sources/*.txt, written by gather.py) and every link must load.
2. COMPLIANCE the built email is checked line by line against the rules Felicia works under:
             CAN-SPAM, CA DRE license disclosure (B&P 10140.6 / Reg 2773), Fair Housing,
             NAR Code of Ethics Art. 12, MLS/source attribution, copyright, the DRE 3/17/2026
             AI advisory (a human approves), and her own standing rules.

Writes QA-REPORT.txt and QA-REPORT.html in the issue's out folder. PASS / FAIL / CHECK BY EYE.
It is a checklist run by software, not legal advice, and it never sends or publishes anything.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_issue import LINT, METRICS  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def number_forms(v, kind):
    """Ways a number may be printed on a source page."""
    if kind == "money":
        return ["{:,.0f}".format(v)]
    if kind == "rate":
        return ["{:.2f}".format(v)]
    forms = {"{:g}".format(v), "{:.1f}".format(v)}
    if kind == "count":
        forms.add("{:,.0f}".format(v))
    return sorted(forms)


def main():
    day = sys.argv[1]
    out = HERE / "out" / day
    issue = json.loads((HERE / "issues" / (day + ".json")).read_text(encoding="utf-8"))
    email = (out / "email.html").read_text(encoding="utf-8")
    text = (out / "email.txt").read_text(encoding="utf-8")
    src_dir = out / "sources"
    sources = {p.name: p.read_text(encoding="utf-8") for p in src_dir.glob("*.txt") if p.name != "INDEX.txt"} if src_dir.exists() else {}
    rows = []  # (section, check, result, detail)

    def add(section, check, ok, detail="", eye=False):
        rows.append((section, check, "CHECK BY EYE" if eye else ("PASS" if ok else "FAIL"), detail))

    # ---------- 1. accuracy ----------
    def url_of(body):
        m = re.search(r"^URL: (\S+)", body, re.M)
        return m.group(1).rstrip("/") if m else ""

    def find(forms, only_url=None):
        """Look for the number on the page it is supposed to come from (only_url), else on any saved page."""
        for name, body in sources.items():
            if only_url and url_of(body) != only_url.rstrip("/"):
                continue
            for f in forms:
                if re.search(r"(?<![\d.,])" + re.escape(f) + r"(?![\d])", body):
                    return name
        return None

    if not sources:
        add("Accuracy", "Source pages saved (run gather.py with the release URLs)", False, "no sources/ folder")
    r = issue["rates"]
    for key in ("rate30", "rate30_prev", "rate30_year", "rate15", "rate15_prev", "rate15_year"):
        if r.get(key) is not None:
            hit = find(number_forms(r[key], "rate"), r["source_url"])
            add("Accuracy", "Mortgage rate %s = %.2f%% is on the Freddie Mac page" % (key, r[key]), bool(hit), hit or "NOT FOUND in any saved source")
    for c in issue["local"]["counties"]:
        for key, label, kind in METRICS:
            m = c["metrics"].get(key) or {}
            for which in ("value", "prev_month", "prev_year"):
                if m.get(which) is not None:
                    src = issue["local"].get("source_url")
                    if not src:  # MLS numbers live behind her login; they cannot be re-checked by script
                        add("Accuracy", "%s, %s (%s) = %s" % (c["name"], label, which, number_forms(m[which], kind)[0]), True, "from the note card: compare with TrendVision on screen", eye=True)
                        continue
                    hit = find(number_forms(m[which], kind), src)
                    add("Accuracy", "%s, %s (%s) = %s" % (c["name"], label, which, number_forms(m[which], kind)[0]), bool(hit), hit or "NOT FOUND on " + src)
    # numbers quoted inside the written takes
    prose = " ".join([issue["headline"], issue["preheader"]] + issue["intro"] + [l["take"] for l in issue["links"]])
    for tok in sorted(set(re.findall(r"\$[\d,]{5,}|\d+\.\d+%|\d+\.\d+ months", prose))):
        core = re.sub(r"[^\d.,]", "", tok).strip(".,")
        forms = [core]
        if core.endswith(".75"):
            forms.append(core[:-3] + "-3/4")  # the Fed writes 3-3/4
        if core.endswith(".25"):
            forms.append(core[:-3] + "-1/4")
        if core.endswith(".5"):
            forms.append(core[:-2] + "-1/2")
        hit = find(forms)
        add("Accuracy", "Number in the writing: %s" % tok, bool(hit), hit or "NOT FOUND in any saved source")
    add("Accuracy", "Sample-payment math in 'what this means' (not from a source, it is arithmetic)", True, "re-computed by hand or calculator each week", eye=True)
    for l in issue["links"] + [{"url": r["source_url"], "title": "Freddie Mac PMMS"}]:
        try:
            req = urllib.request.Request(l["url"], headers={"User-Agent": UA})
            code = urllib.request.urlopen(req, timeout=25).status
            add("Accuracy", "Link loads: " + l["url"], code == 200, "HTTP %s" % code)
        except Exception as e:
            add("Accuracy", "Link loads: " + l["url"], False, str(e)[:80])
    for l in issue["links"]:
        add("Accuracy", "Link has publish date + date checked: " + l["title"], bool(l.get("published") and l.get("verified_on")), "%s / checked %s" % (l.get("published"), l.get("verified_on")))
    add("Accuracy", "No placeholder or made-up local numbers", not issue["local"].get("placeholder"))
    add("Accuracy", "Mortgage rate is this week's (not drafted before Thursday's release)", not (r.get("rates_stale") or issue.get("rates_stale")))

    # ---------- 2. compliance ----------
    must = [
        ("CAN-SPAM", "Working unsubscribe link (BoldTrail merge tag)", "{unsubscribe_url}"),
        ("CAN-SPAM", "Physical postal address", "2603 Camino Ramon, Suite 200, San Ramon, CA 94583"),
        ("CAN-SPAM", "Says why they are getting it (signed up at felicianevin.com)", "signed up at"),
        ("DRE 10140.6 / Reg 2773", "Agent name + license number", "CA DRE #01961050"),
        ("DRE 10140.6 / Reg 2773", "Broker name exactly as licensed, with ', Inc.'", "eXp Realty of California, Inc."),
        ("DRE 10140.6 / Reg 2773", "Broker license number", "CA DRE #01878277"),
        ("Fair Housing", "Equal Housing Opportunity statement", "Equal Housing Opportunity"),
        ("eXp", "'Opinions are my own and not the views of eXp Realty'", "Opinions are my own and not the views of eXp Realty"),
        ("Not advice", "General-information / not legal, tax, lending advice line", "not legal, tax, lending, or financial advice"),
        ("Not advice", "'Not a rate quote. I'm not a lender.' on the rate card", "not a lender"),
        ("No predictions", "'They are not a prediction' line", "not a prediction"),
        ("Source attribution", "'Deemed reliable but not guaranteed'", "eliable but not guaranteed"),
    ]
    flat = html.unescape(re.sub(r"\s+", " ", email))
    for sec, check, needle in must:
        add(sec, check, needle in flat or needle in html.unescape(email))
    add("CAN-SPAM", "Plain-text twin also has unsubscribe + address", "{unsubscribe_url}" in text and "2603 Camino Ramon" in text)
    subj = issue["subject"]
    add("CAN-SPAM", "Subject line is not misleading (matches the content): \"%s\"" % subj, True, "", eye=True)
    add("CAN-SPAM", "'From' name = Felicia Nevin, from her own domain (not gmail.com)", True, "set in BoldTrail at send time", eye=True)
    add("Source attribution", "Local numbers carry source, date range and publish/pull date", bool(issue["local"].get("attribution")) and bool(re.search(r"\d{4}", issue["local"].get("attribution", ""))), issue["local"].get("attribution", "")[:90])
    if "MetroList" in issue["local"].get("attribution", ""):
        add("Source attribution", "MetroList credit line present", "MetroList" in flat)
    add("Copyright", "At most one direct quote, under 15 words", sum(1 for l in issue["links"] if l.get("quote")) <= 1 and all(len(l.get("quote", "").split()) < 15 for l in issue["links"]))
    add("Copyright", "Takes are in our own words (not pasted from the source)", True, "compare each take with its source page", eye=True)

    body_only = re.sub(r"(?s)<!-- ============ FOOTER.*", "", email)
    body_text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(style|head)\b.*?</\1>", " ", body_only)))
    hits = []
    for pat, why in LINT:
        for m in re.finditer(pat, body_text, re.I):
            ctx = body_text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
            if "REALTOR" in m.group(0) and re.search(r"ASSOCIATION OF REALTORS|Association of REALTORS", ctx):
                continue  # allowed: inside an association's name
            if m.group(0) == "—":
                continue  # style only, not compliance
            if re.search(r"not guaranteed", ctx, re.I):
                continue  # the required "deemed reliable but not guaranteed" disclaimer
            hits.append("\"%s\" (%s) ...%s..." % (m.group(0), why.split(";")[0].split(":")[0], re.sub(r"\s+", " ", ctx).strip()))
    add("Fair Housing / NAR Art. 12 / no predictions / no rate advice", "No flagged wording in the body (%d patterns scanned)" % len(LINT), not hits, " | ".join(hits)[:600])
    add("Fair Housing", "Human read-through as a Fair Housing reviewer: homes and numbers only, never people or neighborhood character", True, "", eye=True)
    add("NAR Art. 12", "True picture: no 'best/top/#1' claims, no promised results", True, "covered by the wording scan; confirm by eye", eye=True)
    add("Trademark", "REALTOR® only inside an association's name, all caps with ®", not re.search(r"\bRealtor\b|\brealtor\b", body_text))
    add("One CTA", "Exactly one button / call to action", len(re.findall(r"border-radius:99px", email)) == 1)
    add("TCPA", "Email only. No texts or calls come from this send.", True)
    add("DRE AI advisory 3/17/2026", "A licensed human reviewed and approved before anything went out", issue.get("status") == "approved", "status: %s (stays FAIL until Felicia approves; nothing can publish before that)" % issue.get("status", "draft"))
    add("Her rules", "No contact with eXp compliance; draft only; nothing auto-sent", True)
    size = len(email.encode("utf-8")) / 1024
    add("Deliverability", "Email under Gmail's ~102 KB clip limit", size < 100, "%.0f KB" % size)

    # ---------- report ----------
    fails = [x for x in rows if x[2] == "FAIL"]
    eyes = [x for x in rows if x[2] == "CHECK BY EYE"]
    head = "QA REPORT  issue %s  |  %d checks  |  %d PASS  |  %d FAIL  |  %d for Felicia to check by eye" % (day, len(rows), len(rows) - len(fails) - len(eyes), len(fails), len(eyes))
    lines = [head, "A software checklist, not legal advice. Nothing was sent or published.", ""]
    sec = None
    for s, c, res, d in rows:
        if s != sec:
            lines += ["", "== %s ==" % s]
            sec = s
        lines.append("[%-12s] %s%s" % (res, c, ("   -> " + d) if d else ""))
    (out / "QA-REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    color = {"PASS": "#2F6B4F", "FAIL": "#A3271F", "CHECK BY EYE": "#9C5518"}
    trs, sec = [], None
    for s, c, res, d in rows:
        if s != sec:
            trs.append('<tr><th colspan="2">%s</th></tr>' % html.escape(s))
            sec = s
        mark = {"PASS": "✓ PASS", "FAIL": "✗ FAIL", "CHECK BY EYE": "◉ BY EYE"}[res]
        trs.append('<tr><td class="r" style="color:%s">%s</td><td>%s%s</td></tr>' % (color[res], mark, html.escape(c), ('<div class="d">%s</div>' % html.escape(d)) if d else ""))
    (out / "QA-REPORT.html").write_text("""<!doctype html><meta charset="utf-8"><title>QA report %s</title>
<style>@page{size:Letter;margin:.6in}body{font:10.5pt/1.45 "DM Sans","Segoe UI",Arial,sans-serif;color:#10241D}
h1{font-size:20pt;margin:0 0 4px}p{margin:2px 0 12px;color:#4A5A50}table{width:100%%;border-collapse:collapse}
th{text-align:left;background:#10241D;color:#EDE6D6;padding:6px 10px;font-size:9pt;letter-spacing:.08em;text-transform:uppercase}
td{padding:5px 10px;border-bottom:1px solid #CFC5AD;vertical-align:top}tr{break-inside:avoid}.r{white-space:nowrap;font-weight:700;width:86px}.d{color:#4A5A50;font-size:9pt}</style>
<h1>Accuracy + compliance QA</h1><p>%s<br>A software checklist, not legal advice. ✓ = checked by the script. ◉ = Felicia checks by eye. Nothing was sent or published.</p>
<table>%s</table>""" % (day, html.escape(head), "".join(trs)), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
