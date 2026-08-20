#!/usr/bin/env python3
"""Regenerate the generated regions of index.html plus data.csv, positions.csv,
llms.txt and SOURCES.md from data.json - the canonical dataset.

Usage:
    python3 tools/render.py           rewrite files in place
    python3 tools/render.py --check   exit 1 if any file is out of sync (CI)

Stdlib only; runs on Python 3.9+. No build step is needed to SERVE the page -
this script is maintenance tooling: edit data.json, run it, commit the result.
"""
import csv, io, json, math, os, re, sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fmt_usd(v):
    if v >= 1e12:
        t = v / 1e12
        s = ("%d" % t) if t >= 10 else ("%.2f" % t).rstrip("0").rstrip(".")
        return "$%sT" % s
    b = v / 1e9
    s = ("%d" % round(b)) if b >= 100 else ("%.1f" % b).rstrip("0").rstrip(".")
    return "$%sB" % s

# ---------- fragment builders ----------

def build_blob(d):
    blob = {"cats": d["cats"], "chart": d["chart"], "scope_view": d["scope_view"]}
    return ('<script id="rwa-data" type="application/json">'
            + json.dumps(blob, ensure_ascii=False, separators=(",", ":"))
            + "</script>")

def build_matrix(d):
    out = []
    for grp in d["matrix"]["groups"]:
        out.append('          <tr class="grp"><td colspan="7"><span>%s</span></td></tr>'
                   % escape(grp["g"]))
        for row in grp["rows"]:
            out.append("          <tr>")
            out.append('            <td class="desk">%s<small>%s</small></td>'
                       % (escape(row["desk"]), escape(row["sub"])))
            for c in row["cells"]:
                if c is None:
                    out.append('            <td class="c"><span class="cell n"></span></td>')
                else:
                    cls = "cell lbl" + (" out" if c.get("out") else "") + " " + c["cls"]
                    title = ' title="%s"' % escape(c["title"], quote=True) if c.get("title") else ""
                    out.append('            <td class="c"><span class="%s"%s>%s</span></td>'
                               % (cls, title, escape(c["t"])))
            out.append("          </tr>")
    return "\n".join(out)

def build_noposition(d):
    return ('<p class="disc" style="margin-top:20px">Also in the source base with no position '
            'extracted on these six questions: %s. The "regulatory clarity" bottleneck '
            '(GENIUS · CLARITY · MiCA) is stated collectively across bank research rather than '
            'by a named desk, so it is not attributed in the grid.</p>'
            % escape(d["matrix"]["no_position"]))

def build_forecast_table(d):
    out = []
    for r in d["forecast_table"]:
        out.append('          <tr><td class="pub">%s</td><td class="num"><span class="fig">%s</span>'
                   '<small>%s</small></td><td>%s</td><td>%s</td></tr>'
                   % (r["pub_html"], escape(r["fig"]), r["fignote_html"],
                      r["counted_html"], r["stance_html"]))
    return "\n".join(out)

def build_today_table(d):
    out = []
    for r in d["today_table"]:
        out.append('          <tr><td class="pub">%s</td><td class="num"><span class="fig">%s</span>'
                   '<small>%s</small></td><td>%s</td></tr>'
                   % (r["pub_html"], escape(r["fig"]), r["fignote_html"], r["def_html"]))
    return "\n".join(out)

def build_lead_table(d):
    out = []
    for r in d["lead_table"]:
        out.append('          <tr><td class="pub">%s</td><td>%s</td><td>%s</td></tr>'
                   % (r["pub_html"], r["lead_html"], r["why_html"]))
    return "\n".join(out)

def build_stairs(d):
    st = d["staircase"]
    lo, hi = math.log(st["lo"]), math.log(st["hi"])
    pos = lambda v: 100.0 * (math.log(v) - lo) / (hi - lo)
    out = ['<div class="stairs">',
           '      <div class="stairs-head"><span class="kicker">%s</span>'
           '<span class="stairs-note">%s</span></div>' % (escape(st["kicker"]), escape(st["intro"]))]
    cat_for = {"The tracker cluster": "sc-narrow", "BeInCrypto · core": "sc-broad",
               "21Shares": "sc-public", "Standard Chartered": "sc-all",
               "BeInCrypto · full layer": "sc-all"}
    for r in st["rungs"]:
        fork = ' fork' if r.get("fork") else ""
        fk = '<span class="fk">route %s</span>' % r["fork"] if r.get("fork") else ""
        cls = cat_for.get(r["label"], "sc-narrow")
        if "v_lo" in r:
            left, width = pos(r["v_lo"]), pos(r["v_hi"]) - pos(r["v_lo"])
        else:
            left, width = 0.0, pos(r["v"])
        val_at = left + width
        out.append('      <div class="rung%s %s">' % (fork, cls))
        out.append('        <div class="r-meta"><b>%s%s</b><small>%s</small></div>'
                   % (fk, escape(r["label"]), escape(r["who"])))
        out.append('        <div class="r-track"><div class="r-bar" style="left:%.1f%%;width:%.1f%%">'
                   '</div><span class="r-val" style="left:%.1f%%">%s<small>%s</small></span></div>'
                   % (left, max(width, 0.5), val_at, escape(r["display"]), escape(r["mult"])))
        out.append('        <div class="r-step">%s</div>' % escape(r["step"]))
        out.append('      </div>')
    out.append('      <p class="src-line">%s</p>' % escape(st["fork_note"]))
    out.append('    </div>')
    return "\n    ".join(out)

def build_revisions(d):
    out = ['<ol class="revlog">']
    for r in d["revisions"]:
        out.append('      <li><span class="rv-d">%s</span><div class="rv-b">'
                   '<span class="chg"><b>%s</b> – %s</span><small>%s</small>'
                   % (escape(r["d"]), escape(r["desk"]), escape(r["change"]), escape(r["note"])))
        if r.get("drift"):
            # Binance base-case walk-down: hollow dot = old base, solid dot = new base, log track $200B-$1.6T
            lo, hi = math.log(200e9), math.log(1600e9)
            p661 = 100.0 * (math.log(661e9) - lo) / (hi - lo)
            out.append('      <div class="drift"><span class="d-lab">$661B<small>30 Jul</small></span>'
                       '<div class="d-track"><div class="d-line" style="left:%.1f%%;right:0"></div>'
                       '<i class="d-dot" style="left:calc(%.1f%% - 5px)"></i>'
                       '<i class="d-dot was" style="right:0"></i></div>'
                       '<span class="d-lab">$1.6T<small>15 May</small></span>'
                       '<span class="d-tag">−59%% in ten weeks</span></div>' % (p661, p661))
        out.append('      </div></li>')
    out.append('    </ol>')
    return "\n    ".join(out)

def build_sources(d):
    groups, order = {}, []
    for s in d["sources"]:
        if s["group"] not in groups:
            groups[s["group"]] = []; order.append(s["group"])
        groups[s["group"]].append(s)
    out, n = ['<ol class="srcs">'], 0
    for g in order:
        out.append('      <li class="src-grp" role="presentation">%s</li>' % escape(g))
        for s in groups[g]:
            n += 1
            gate = " · %s" % s["gate"] if s.get("gate") else ""
            out.append('      <li><span class="sn">%02d</span><span class="st">%s · <em>%s</em> '
                       '<span class="sm">· %s%s</span></span>'
                       '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a></li>'
                       % (n, escape(s["pub"]), escape(s["title"]), escape(s["date"]),
                          escape(gate), escape(s["url"], quote=True), escape(s["label"])))
    out.append('    </ol>')
    return "\n    ".join(out)

# ---------- whole-file builders ----------

def render_index(d, src):
    frags = {
        "blob": build_blob(d),
        "matrix": build_matrix(d),
        "noposition": build_noposition(d),
        "forecast_table": build_forecast_table(d),
        "today_table": build_today_table(d),
        "lead_table": build_lead_table(d),
        "stairs": build_stairs(d),
        "revisions": build_revisions(d),
        "sources": build_sources(d),
        "srccount": str(len(d["sources"])),
    }
    for name, frag in frags.items():
        pat = re.compile(r"(<!-- gen:%s -->).*?(<!-- /gen:%s -->)" % (name, name), re.S)
        if not pat.search(src):
            sys.exit("marker missing in index.html: %s" % name)
        src = pat.sub(lambda m: m.group(1) + "\n" + frag + "\n" + m.group(2)
                      if name not in ("srccount",) else m.group(1) + frag + m.group(2), src)
    return src

def render_data_csv(d):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    srcmap = {s["id"]: s for s in d["sources"]}
    w.writerow(["series","desk","value_usd","low_usd","high_usd","alt_usd","alt_label",
                "category","category_label","scope","as_of","point_estimate",
                "pct_of_300t_tam","source_id","source_title","source_url"])
    for series in ("forecast", "today"):
        for it in d["chart"][series]["items"]:
            s = srcmap.get(it.get("ref"), {})
            w.writerow([series, it["n"], int(it["v"]),
                        int(it["lo"]) if it.get("lo") else "",
                        int(it["hi"]) if it.get("hi") else "",
                        int(it["alt"]) if it.get("alt") else "",
                        it.get("altLbl",""), it["cat"], d["cats"][it["cat"]],
                        it["scope"], it["src"], 1 if it.get("pt") else 0,
                        round(100.0*it["v"]/300e12, 4),
                        it.get("ref",""), s.get("title",""), s.get("url","")])
    return buf.getvalue()

def render_positions_csv(d):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    srcmap = {s["id"]: s for s in d["sources"]}
    w.writerow(["group","desk","desk_note","question","position","scope_class",
                "different_unit","unit_note","source_ids","source_urls"])
    qs = d["matrix"]["questions"]
    for grp in d["matrix"]["groups"]:
        for row in grp["rows"]:
            urls = " | ".join(srcmap[r]["url"] for r in row["refs"] if r in srcmap)
            for q, c in zip(qs, row["cells"]):
                if c is None: continue
                w.writerow([grp["g"], row["desk"], row["sub"], q, c["t"], c["cls"],
                            1 if c.get("out") else 0, c.get("title",""),
                            " | ".join(row["refs"]), urls])
    return buf.getvalue()

def render_llms(d):
    m = d["meta"]
    fc = d["chart"]["forecast"]["items"]; td = d["chart"]["today"]["items"]
    lines = [
        "# %s" % m["title"], "",
        "> A cross-read of %d RWA & tokenization research reports published %s. "
        "The desks converge on the direction of travel and disagree ~35x on 2030 market size "
        "(%s to %s) and ~36x on today's size (%s to %s). Most of the disagreement is "
        "definitional: what counts as an RWA, which chains are counted, and whether "
        "stablecoins are in." % (
            m["reports_read"], m["window"],
            fmt_usd(min(i["v"] for i in fc)), fmt_usd(max(i["v"] for i in fc)),
            fmt_usd(min(i["v"] for i in td)), fmt_usd(max(i["v"] for i in td))),
        "",
        "Consensus facts: ~0.01% penetration of a $300T+ addressable base; ~$15B tokenized "
        "U.S. Treasuries anchor the market; institutional issuers now lead growth; DTCC "
        "production launch October 2026 is the shared catalyst.",
        "",
        "## Data",
        "- [data.json](%sdata.json): canonical dataset - every figure, matrix position, "
        "revision and source; the page is generated from it" % m["site"],
        "- [data.csv](%sdata.csv): market-size figures, flat table "
        "(desk, value, scope category, date, source)" % m["site"],
        "- [positions.csv](%spositions.csv): 6-question desk-position matrix, flat table" % m["site"],
        "",
        "## Sources",
        "- [SOURCES.md](https://github.com/mishablank/RWA-Research-Snapshot/blob/main/SOURCES.md): "
        "the %d reports figures are attributed to, with links" % len(d["sources"]),
        "- Figures are reproduced as reported by each source on the date cited; scopes differ "
        "materially between studies and are not directly comparable - that incomparability "
        "is the subject of the page.",
        "",
        "Updated %s." % m["updated"],
    ]
    return "\n".join(lines) + "\n"

def render_sources_md(d):
    groups, order = {}, []
    for s in d["sources"]:
        if s["group"] not in groups:
            groups[s["group"]] = []; order.append(s["group"])
        groups[s["group"]].append(s)
    out = ["# Source register", "",
           "The reports this page attributes figures or positions to – %d of the %d cross-read "
           "in the window (%s). Links go to the publisher's own page or PDF; Standard Chartered's "
           "two research notes are institutional-client only and link to The Block's same-day "
           "coverage instead. %d of the %d reports are archived locally in the research corpus; "
           "the archive is not part of this repo." % (
               len(d["sources"]), d["meta"]["reports_read"], d["meta"]["window"],
               d["meta"]["archived_locally"], d["meta"]["reports_read"]),
           "",
           "Generated from [`data.json`](data.json) by `tools/render.py` – edit there, not here.", ""]
    n = 0
    for g in order:
        out.append("## %s" % g); out.append("")
        for s in groups[g]:
            n += 1
            gate = " · *%s, linked via The Block*" % s["gate"] if s.get("gate") else ""
            out.append("%d. %s – [*%s*](%s) – %s%s" % (n, s["pub"], s["title"], s["url"], s["date"], gate))
        out.append("")
    return "\n".join(out)

def main():
    check = "--check" in sys.argv
    with open(os.path.join(ROOT, "data.json")) as f:
        d = json.load(f)
    with open(os.path.join(ROOT, "index.html")) as f:
        idx = f.read()
    outputs = {
        "index.html": render_index(d, idx),
        "data.csv": render_data_csv(d),
        "positions.csv": render_positions_csv(d),
        "llms.txt": render_llms(d),
        "SOURCES.md": render_sources_md(d),
    }
    stale = []
    for name, content in outputs.items():
        path = os.path.join(ROOT, name)
        cur = open(path).read() if os.path.exists(path) else None
        if cur != content:
            stale.append(name)
            if not check:
                with open(path, "w") as f:
                    f.write(content)
    if check and stale:
        print("OUT OF SYNC with data.json: %s\nRun: python3 tools/render.py" % ", ".join(stale))
        sys.exit(1)
    print(("checked, all in sync" if check else "regenerated: %s" % (", ".join(stale) or "nothing changed")))

if __name__ == "__main__":
    main()
