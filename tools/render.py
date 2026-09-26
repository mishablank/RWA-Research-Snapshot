#!/usr/bin/env python3
"""Regenerate the generated regions of index.html plus data.csv, positions.csv,
llms.txt, SOURCES.md and DATA.md from data.json - the canonical dataset.

Usage:
    python3 tools/render.py           rewrite files in place
    python3 tools/render.py --check   exit 1 if any file is out of sync (CI)

Stdlib only; runs on Python 3.9+. No build step is needed to SERVE the page -
this script is maintenance tooling: edit data.json, run it, commit the result.
Run tools/validate.py first; this script assumes the data is well-formed.
"""
import csv, io, json, math, os, re, sys
from html import escape
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rwalib import (ROOT, DATA_PATH, SCHEMA_PATH, Data, load_json, fmt_usd, fmt_fig, month_label,
                    day_label, published_label, compute_stats, resolve, md_inline, words)

# Presentation lives here, not in data.json: which colour each position value gets.
# a green · b red · c brown · d plum · e ink · f blue (see .pos-* in index.html)
TONE = {
    ("stablecoins", "rail"): "b", ("stablecoins", "coexist"): "a", ("stablecoins", "flawed_money"): "e",
    ("lead_asset", "treasuries"): "a", ("lead_asset", "treasuries_credit"): "a",
    ("lead_asset", "equities_treasuries"): "b", ("lead_asset", "equities_credit"): "b",
    ("lead_asset", "funds"): "d",
    ("rails", "public"): "a", ("rails", "permissioned"): "d", ("rails", "unified_ledger"): "d",
    ("constraint", "market_infra"): "b", ("constraint", "data_interop"): "c",
    ("constraint", "convergence"): "f", ("constraint", "monetary_architecture"): "e",
    ("constraint", "safety_first"): "a",
}
NEUTRAL_CLS = "pos-c"   # figure cells with no scope bucket


def source_label(s):
    host = urlparse(s["url"]).netloc
    if host.endswith("theblock.co"):
        return "via The Block ↗"
    if urlparse(s["url"]).path.lower().endswith(".pdf"):
        return "PDF ↗"
    return "Report ↗"


def source_groups(D):
    groups, order = {}, []
    for s in D.d["sources"]:
        g = D.desk_group(s["desk"])
        if g not in groups:
            groups[g] = []; order.append(g)
        groups[g].append(s)
    return [(g, groups[g]) for g in order]


# ---------- position cells (matrix + positions.csv) ----------

def figure_cell(D, p):
    q = D.questions[p["question"]]
    figs = [D.figures[x] for x in p["figures"]]
    text = "–".join(fmt_usd(f["value_usd"]) for f in figs)
    h = q.get("horizon")
    if h and any(f["horizon"] and f["horizon"] != h for f in figs):
        text += " '%02d" % (figs[0]["horizon"] % 100)
    metric = D.metrics[figs[0]["metric"]]
    if metric["short"]:
        text += " " + metric["short"]
    scope = p.get("scope") or next((f["scope"] for f in figs if f["scope"]), None)
    out = any(f["metric"] != "market_size" for f in figs)
    return {"text": text, "cls": ("sc-" + scope) if scope else NEUTRAL_CLS, "out": out,
            "title": metric["unit_note"] if out else ""}


def stance_cell(D, p):
    v = D.value_label(p["question"], p["value"])
    text = v["label"] + (" · " + p["qualifier"] if p.get("qualifier") else "")
    return {"text": text, "cls": "pos-" + TONE[(p["question"], p["value"])], "out": False, "title": "",
            "description": v["description"]}


def cell(D, p):
    return figure_cell(D, p) if "figures" in p else stance_cell(D, p)


# ---------- fragment builders ----------

def build_blob(D, S):
    def items(view):
        out = []
        for e in D.d["views"][view]:
            f = D.figures[e["figure"]]
            it = {"n": escape(e.get("label") or D.label(f), quote=False), "v": f["value_usd"]}
            if f.get("low_usd") is not None:
                it["lo"], it["hi"] = f["low_usd"], f["high_usd"]
            it["cat"] = e.get("scope") or f["scope"]
            if f.get("point_estimate") is True:
                it["pt"] = 1
            if e.get("alt"):
                it["alt"] = D.figures[e["alt"]]["value_usd"]
                it["altLbl"] = escape(e["alt_label"], quote=False)
            it["scope"] = escape(resolve(e.get("tooltip") or f["definition"], D, S), quote=False)
            it["src"] = published_label(D, f)
            it["ref"] = f["source"]
            out.append(it)
        return out
    c = D.d["copy"]
    def chart(key, view):
        return {"ttl": resolve(c[key]["title"], D, S),
                "note": md_inline(resolve(c[key]["note_log"], D, S)),
                "noteLin": md_inline(resolve(c[key]["note_linear"], D, S)),
                "items": items(view)}
    blob = {"cats": {x["id"]: x["label"] for x in D.d["scopes"]},
            "chart": {"forecast": chart("chart_forecast", "chart_forecast"),
                      "today": chart("chart_today", "chart_today")},
            "scope_view": {"ttl": resolve(c["chart_byscope"]["title"], D, S),
                           "note": md_inline(resolve(c["chart_byscope"]["note"], D, S))}}
    js = json.dumps(blob, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return '<script id="rwa-data" type="application/json">' + js + "</script>"


def build_head(D, S):
    m, c = D.d["meta"], D.d["copy"]["share"]
    a = lambda s: escape(resolve(s, D, S), quote=True)
    t = escape(m["title"], quote=True)
    img = m["site"] + "og-card.png"
    lines = [
        '<meta name="description" content="%s">' % a(c["description"]),
        '<meta name="author" content="%s">' % escape(m["author"], quote=True),
        '<link rel="canonical" href="%s">' % m["site"],
        '<meta name="theme-color" content="#F2EBDD">',
        '<meta property="og:type" content="article">',
        '<meta property="og:url" content="%s">' % m["site"],
        '<meta property="og:site_name" content="RWA Research Snapshot">',
        '<meta property="og:title" content="%s">' % t,
        '<meta property="og:description" content="%s">' % a(c["social"]),
        '<meta property="og:image" content="%s">' % img,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="%s">' % a(c["image_alt"]),
        '<meta property="article:published_time" content="%s">' % m["published"],
        '<meta property="article:modified_time" content="%s">' % m["updated"],
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % t,
        '<meta name="twitter:description" content="%s">' % a(c["social"]),
        '<meta name="twitter:image" content="%s">' % img,
    ]
    return "\n".join(lines)


def build_jsonld(D, S):
    m = D.d["meta"]
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": m["title"],
          "description": resolve(D.d["copy"]["share"]["article"], D, S),
          "url": m["site"], "mainEntityOfPage": m["site"], "image": m["site"] + "og-card.png",
          "datePublished": m["published"], "dateModified": m["updated"],
          "author": {"@type": "Person", "name": m["author"], "url": m["author_url"]},
          "isBasedOn": {"@type": "Dataset", "name": m["title"] + " – dataset",
                        "url": m["site"] + "data.json", "license": "https://creativecommons.org/licenses/by/4.0/"}}
    return ('<script type="application/ld+json">\n'
            + json.dumps(ld, ensure_ascii=False, indent=2).replace("</", "<\\/") + "\n</script>")


def build_matrix(D, S):
    out = []
    qs = D.d["questions"]
    by = {(p["desk"], p["question"]): p for p in D.d["positions"]}
    held = D.matrix_desks()
    for g in D.d["desk_groups"]:
        rows = [x for x in held if D.desks[x]["group"] == g["id"]]
        if not rows:
            continue
        out.append('          <tr class="grp"><td colspan="%d"><span>%s</span></td></tr>'
                   % (len(qs) + 1, escape(g["label"])))
        for did in rows:
            dk = D.desks[did]
            out.append("          <tr>")
            out.append('            <td class="desk">%s<small>%s</small></td>'
                       % (escape(dk["name"]), escape(dk.get("note", ""))))
            for q in qs:
                p = by.get((did, q["id"]))
                if p is None:
                    out.append('            <td class="c"><span class="cell n" role="img" '
                               'aria-label="No public position in this window"></span></td>')
                    continue
                c = cell(D, p)
                cls = "cell lbl" + (" out" if c["out"] else "") + " " + c["cls"]
                title = c["title"] or c.get("description", "")
                title = ' title="%s"' % escape(title, quote=True) if title else ""
                out.append('            <td class="c"><span class="%s"%s>%s</span></td>'
                           % (cls, title, escape(c["text"])))
            out.append("          </tr>")
    return "\n".join(out)


def build_noposition(D, S):
    held = set(D.matrix_desks())
    names = [x["name"] for x in D.d["desks"] if x["id"] not in held]
    return ('<p class="disc" style="margin-top:20px">Also in the source base with no position '
            'extracted on these %s questions: %s. %s</p>'
            % (words(len(D.d["questions"])), escape(" · ".join(names)),
               escape(resolve(D.d["copy"]["no_position_note"], D, S))))


def build_forecast_table(D, S):
    out = []
    for r in D.d["tables"]["forecast"]:
        f = D.figures[r["figure"]]
        out.append('          <tr><td class="pub">%s<small>%s</small></td><td class="num"><span class="fig">%s</span>'
                   '<small>%s</small></td><td>%s</td><td>%s</td></tr>'
                   % (escape(r.get("label") or D.label(f)), escape(published_label(D, f, "table")),
                      escape(fmt_fig(f)), escape(resolve(r["note"], D, S)),
                      escape(resolve(r["counted"], D, S)), escape(resolve(r["stance"], D, S))))
    return "\n".join(out)


def build_today_table(D, S):
    out = []
    for r in D.d["tables"]["today"]:
        figs = [D.figures[x] for x in r["figures"]]
        out.append('          <tr><td class="pub">%s</td><td class="num"><span class="fig">%s</span>'
                   '<small>%s</small></td><td>%s</td></tr>'
                   % (escape(r.get("label") or D.label(figs[0])), escape(" → ".join(fmt_fig(f) for f in figs)),
                      escape(resolve(r["note"], D, S)), escape(resolve(r["definition"], D, S))))
    return "\n".join(out)


def build_lead_table(D, S):
    out = []
    for r in D.d["tables"]["lead_asset"]:
        out.append('          <tr><td class="pub">%s</td><td><b>%s</b></td><td>%s</td></tr>'
                   % (escape(r.get("label") or D.desks[r["desk"]]["name"]), escape(r["lead"]),
                      escape(resolve(r["why"], D, S))))
    return "\n".join(out)


def stair_rungs(D):
    """Rung values and multiples, computed from the figures they cite."""
    rungs = []
    for r in D.d["staircase"]["rungs"]:
        figs = [D.figures[x] for x in r["figures"]]
        vs = [f["value_usd"] for f in figs]
        rungs.append({"r": r, "figs": figs, "lo": min(vs), "hi": max(vs),
                      "scope": r.get("scope") or figs[0]["scope"]})
    base = rungs[0]["lo"]
    for i, x in enumerate(rungs):
        if len(x["figs"]) > 1:
            x["display"] = "$%d–%dB" % (round(x["lo"] / 1e9), round(x["hi"] / 1e9))
        else:
            x["display"] = fmt_fig(x["figs"][0])
        x["mult"] = "baseline" if i == 0 else "×%d" % round(x["hi"] / base) + (" the narrowest" if i == 1 else "")
    return rungs


def build_stairs(D, S):
    st = D.d["staircase"]
    rungs = stair_rungs(D)
    lo = math.floor(min(x["lo"] for x in rungs) * 0.8 / 5e9) * 5e9
    hi = math.ceil(max(x["hi"] for x in rungs) * 1.1 / 1e11) * 1e11
    llo, lhi = math.log(lo), math.log(hi)
    pos = lambda v: 100.0 * (math.log(v) - llo) / (lhi - llo)
    out = ['<div class="stairs">',
           '      <div class="stairs-head"><span class="kicker">%s</span>'
           '<span class="stairs-note">%s</span></div>' % (escape(st["kicker"]), escape(resolve(st["intro"], D, S)))]
    for x in rungs:
        r = x["r"]
        fork = ' fork' if r.get("fork") else ""
        fk = '<span class="fk">route %s</span>' % r["fork"] if r.get("fork") else ""
        who = r.get("who") or " · ".join(D.label(f) for f in x["figs"])
        if len(x["figs"]) > 1:
            left, width = pos(x["lo"]), pos(x["hi"]) - pos(x["lo"])
        else:
            left, width = 0.0, pos(x["hi"])
        out.append('      <div class="rung%s sc-%s">' % (fork, x["scope"]))
        out.append('        <div class="r-meta"><b>%s%s</b><small>%s</small></div>'
                   % (fk, escape(r["label"]), escape(who)))
        out.append('        <div class="r-track" aria-hidden="true"><div class="r-bar" style="left:%.1f%%;width:%.1f%%">'
                   '</div><span class="r-val" style="left:%.1f%%">%s<small>%s</small></span></div>'
                   % (left, max(width, 0.5), left + width, escape(x["display"]), escape(x["mult"])))
        out.append('        <div class="r-step">%s</div>' % escape(resolve(r["step"], D, S)))
        out.append('      </div>')
    out.append('      <p class="src-line">%s</p>' % escape(resolve(st["fork_note"], D, S)))
    out.append('    </div>')
    return "\n    ".join(out)


def build_revisions(D, S):
    out = ['<ol class="revlog">']
    for r in D.d["revisions"]:
        desk = D.desks[r["desk"]]["name"] if r.get("desk") else "This page"
        out.append('      <li><span class="rv-d">%s</span><div class="rv-b">'
                   '<span class="chg"><b>%s</b> – %s</span><small>%s</small>'
                   % (escape(day_label(r["date"])), escape(desk), escape(resolve(r["change"], D, S)),
                      escape(resolve(r["note"], D, S))))
        if r.get("drift"):
            # base-case walk-down: hollow dot = old base, solid dot = new base, on a log track
            a, b = D.figures[r["drift"]["from"]], D.figures[r["drift"]["to"]]
            hi = max(a["value_usd"], b["value_usd"]); lo = hi / 8
            p = 100.0 * (math.log(b["value_usd"]) - math.log(lo)) / (math.log(hi) - math.log(lo))
            dl = lambda f: "%d %s" % (int(f["published"][8:10]), month_label(f["published"]).split()[0])
            out.append('      <div class="drift"><span class="d-lab">%s<small>%s</small></span>'
                       '<div class="d-track" aria-hidden="true"><div class="d-line" style="left:%.1f%%;right:0"></div>'
                       '<i class="d-dot" style="left:calc(%.1f%% - 5px)"></i>'
                       '<i class="d-dot was" style="right:0"></i></div>'
                       '<span class="d-lab">%s<small>%s</small></span>'
                       '<span class="d-tag">−%s%% in %s weeks</span></div>'
                       % (fmt_usd(b["value_usd"]), dl(b), p, p, fmt_usd(a["value_usd"]), dl(a),
                          S["drift_pct"], S["drift_weeks_words"]))
        out.append('      </div></li>')
    out.append('    </ol>')
    return "\n    ".join(out)


def build_sources(D, S):
    out, n = ['<ol class="srcs">'], 0
    for g, items in source_groups(D):
        out.append('      <li class="src-grp" role="presentation">%s</li>' % escape(g))
        for s in items:
            n += 1
            gate = " · %s note" % s["access"] if s.get("access") else ""
            out.append('      <li><span class="sn">%02d</span><span class="st">%s · <em>%s</em> '
                       '<span class="sm">· %s%s</span></span>'
                       '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a></li>'
                       % (n, escape(s["publisher"]), escape(s["title"]), escape(month_label(s["published"])),
                          escape(gate), escape(s["url"], quote=True), escape(source_label(s))))
    out.append('    </ol>')
    return "\n    ".join(out)


# ---------- whole-file builders ----------

BLOCKS = {
    "head": build_head, "jsonld": build_jsonld, "blob": build_blob, "matrix": build_matrix,
    "noposition": build_noposition, "forecast_table": build_forecast_table,
    "today_table": build_today_table, "lead_table": build_lead_table, "stairs": build_stairs,
    "revisions": build_revisions, "sources": build_sources,
}
GEN_RE = re.compile(r"<!-- gen:(\w+) -->.*?<!-- /gen:\1 -->", re.S)


def render_index(D, S, src):
    for name in BLOCKS:
        if "<!-- gen:%s -->" % name not in src:
            sys.exit("marker missing in index.html: %s" % name)
    frags = {name: fn(D, S) for name, fn in BLOCKS.items()}

    def sub(m):
        name = m.group(1)
        if name.startswith("s_"):   # inline computed stat
            key = name[2:]
            if key not in S:
                sys.exit("index.html uses unknown stat marker gen:%s" % name)
            return "<!-- gen:%s -->%s<!-- /gen:%s -->" % (name, escape(S[key]), name)
        if name not in frags:
            sys.exit("index.html has unknown gen marker: %s" % name)
        return "<!-- gen:%s -->\n%s\n<!-- /gen:%s -->" % (name, frags[name], name)
    return GEN_RE.sub(sub, src)


def csv_text(columns, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([c for c, _ in columns])
    for r in rows:
        w.writerow(["" if r.get(c) is None else r.get(c) for c, _ in columns])
    return buf.getvalue()


def b01(x):
    return "" if x is None else (1 if x else 0)


DATA_CSV_COLUMNS = [
    ("figure_id", "Stable id of the figure (matches `figures[].id` in data.json)"),
    ("desk_id", "Stable id of the publishing desk"),
    ("desk", "Desk name"),
    ("desk_group", "Banks · Managers & issuers · Consultancies · Crypto research & trackers · Official sector"),
    ("label", "Display label used on the page (may name a scenario or sub-scope)"),
    ("kind", "`today` (a measurement) or `forecast` (a projection)"),
    ("metric", "What is measured – see the metric vocabulary; only `market_size` rows are comparable market sizes"),
    ("asset_class", "Asset class the figure is limited to; empty = all classes in scope"),
    ("value_usd", "Headline value, nominal USD"),
    ("low_usd", "Low end of a published scenario range, if any"),
    ("high_usd", "High end of a published scenario range, if any"),
    ("approx", "1 if the source states the figure as approximate (~)"),
    ("point_estimate", "1 = the source gives a single number with no range; 0 = a range exists; empty = not recorded"),
    ("horizon_year", "Forecast horizon year; empty for `today` figures and for forecasts with no stated horizon"),
    ("as_of", "Period the figure measures (ISO, month precision) when the source states it separately from publication"),
    ("published", "Publication date of the figure (ISO 8601; YYYY-MM when only the month is known)"),
    ("scenario", "`base`, `bull`, `bear` or `tail` where the source labels its scenarios"),
    ("status", "`current`, or `superseded` when the same desk later replaced it"),
    ("superseded_by", "figure_id of the replacement"),
    ("scope_id", "Scope bucket – what the figure counts; drives the chart colour"),
    ("scope_label", "Scope bucket label"),
    ("includes_stablecoins", "1/0 if the definition is known to include/exclude stablecoins; empty = not stated"),
    ("includes_permissioned", "1/0 if the definition is known to include/exclude permissioned networks; empty = not stated"),
    ("definition", "What the source counts, in one line"),
    ("in_chart", "`forecast` or `today` if the figure is plotted in that chart view (`-alt` = the hollow dot)"),
    ("source_id", "Source id (matches `sources[].id`)"),
    ("source_title", "Source report title"),
    ("source_url", "Link to the report"),
]

POSITIONS_CSV_COLUMNS = [
    ("desk_id", "Stable id of the desk"),
    ("desk", "Desk name"),
    ("desk_group", "Desk group"),
    ("question_id", "Question id (`size_2030`, `size_today`, `stablecoins`, `lead_asset`, `rails`, `constraint`)"),
    ("question", "Question label as shown on the page"),
    ("position_id", "Value id from the question's vocabulary; empty for figure questions"),
    ("position", "Cell text as shown on the page"),
    ("position_description", "Long-form meaning of the position value"),
    ("qualifier", "Desk-specific nuance on top of the value (e.g. `USD only`)"),
    ("figure_ids", "Figures behind a size cell, ` | `-separated"),
    ("different_unit", "1 if the figure is not a market size (revenue, fund AUM, opportunity…)"),
    ("unit_note", "What the unit is instead"),
    ("source_ids", "Sources for this desk, ` | `-separated"),
    ("source_urls", "Their URLs, ` | `-separated"),
]


def render_data_csv(D, S):
    in_chart = {}
    for view, tag in (("chart_forecast", "forecast"), ("chart_today", "today")):
        for e in D.d["views"][view]:
            in_chart[e["figure"]] = tag
            if e.get("alt"):
                in_chart[e["alt"]] = tag + "-alt"
    rows = []
    for f in D.d["figures"]:
        s, dk = D.sources[f["source"]], D.desks[f["desk"]]
        rows.append({
            "figure_id": f["id"], "desk_id": f["desk"], "desk": dk["name"], "desk_group": D.desk_group(f["desk"]),
            "label": D.label(f), "kind": f["kind"], "metric": f["metric"], "asset_class": f.get("asset_class"),
            "value_usd": f["value_usd"], "low_usd": f.get("low_usd"), "high_usd": f.get("high_usd"),
            "approx": b01(f.get("approx")), "point_estimate": b01(f.get("point_estimate")),
            "horizon_year": f.get("horizon"), "as_of": f.get("as_of"), "published": f["published"],
            "scenario": f.get("scenario"), "status": f["status"], "superseded_by": f.get("superseded_by"),
            "scope_id": f.get("scope"), "scope_label": D.scopes[f["scope"]]["label"] if f.get("scope") else None,
            "includes_stablecoins": b01(f.get("includes_stablecoins")),
            "includes_permissioned": b01(f.get("includes_permissioned")),
            "definition": f["definition"], "in_chart": in_chart.get(f["id"]),
            "source_id": f["source"], "source_title": s["title"], "source_url": s["url"],
        })
    return csv_text(DATA_CSV_COLUMNS, rows)


def render_positions_csv(D, S):
    rows = []
    by = {(p["desk"], p["question"]): p for p in D.d["positions"]}
    for did in D.matrix_desks():
        srcs = D.desk_sources(did)
        for q in D.d["questions"]:
            p = by.get((did, q["id"]))
            if p is None:
                continue
            c = cell(D, p)
            rows.append({
                "desk_id": did, "desk": D.desks[did]["name"], "desk_group": D.desk_group(did),
                "question_id": q["id"], "question": q["label"], "position_id": p.get("value"),
                "position": c["text"], "position_description": c.get("description"),
                "qualifier": p.get("qualifier"), "figure_ids": " | ".join(p.get("figures", [])) or None,
                "different_unit": 1 if c["out"] else 0, "unit_note": c["title"] or None,
                "source_ids": " | ".join(s["id"] for s in srcs), "source_urls": " | ".join(s["url"] for s in srcs),
            })
    return csv_text(POSITIONS_CSV_COLUMNS, rows)


def render_llms(D, S):
    m = D.d["meta"]
    site = m["site"]
    lines = [
        "# %s" % m["title"], "",
        "> A cross-read of %s RWA & tokenization research reports published %s. "
        "The desks converge on the direction of travel and disagree ~%sx on 2030 market size "
        "(%s to %s) and ~%sx on today's size (%s to %s). Most of the disagreement is "
        "definitional: what counts as an RWA, which chains are counted, and whether "
        "stablecoins are in." % (S["reports_read"], S["window"], S["fc_spread"], S["fc_lo"], S["fc_hi"],
                                 S["td_spread"], S["td_lo"], S["td_hi"]),
        "",
        "Consensus facts: ~0.01% penetration of a $300T+ addressable base; ~$15B tokenized "
        "U.S. Treasuries anchor the market; institutional issuers now lead growth; DTCC "
        "production launch October 2026 is the shared catalyst.",
        "",
        "## Data",
        "- [data.json](%sdata.json): canonical dataset (schema v%s) - one record per figure with "
        "horizon, as-of date, unit and scope; desk positions with defined vocabularies; "
        "revisions; sources. The page is generated from it" % (site, D.d["schema_version"]),
        "- [data.schema.json](%sdata.schema.json): JSON Schema for data.json" % site,
        "- [data.csv](%sdata.csv): every figure, one row each (%d rows)" % (site, len(D.d["figures"])),
        "- [positions.csv](%spositions.csv): the %s-desk x %s-question position matrix, one row per cell"
        % (site, S["matrix_desks"], S["questions"]),
        "- [DATA.md](https://github.com/mishablank/RWA-Research-Snapshot/blob/main/DATA.md): "
        "data dictionary - every field, column and vocabulary",
        "",
        "## Reading the numbers",
        "- Only rows with metric=market_size are market sizes; revenue, fund AUM and stablecoin figures are different units.",
        "- Check horizon_year before comparing forecasts: most are 2030, but not all (Standard Chartered's $4T is 2028).",
        "- status=superseded rows are kept for the revision history; filter to status=current for the latest view.",
        "",
        "## Sources",
        "- [SOURCES.md](https://github.com/mishablank/RWA-Research-Snapshot/blob/main/SOURCES.md): "
        "the %s reports figures are attributed to, with links" % S["sources_n"],
        "- %s" % m["disclaimer"],
        "",
        "Updated %s." % m["updated"],
    ]
    return "\n".join(lines) + "\n"


def render_sources_md(D, S):
    m = D.d["meta"]
    out = ["# Source register", "",
           "The reports this page attributes figures or positions to – %s of the %s cross-read "
           "in the window (%s). Links go to the publisher's own page or PDF; Standard Chartered's "
           "two research notes are institutional-client only and link to The Block's same-day "
           "coverage instead. %s of the %s reports are archived locally in the research corpus; "
           "the archive is not part of this repo." % (
               S["sources_n"], S["reports_read"], S["window"], S["archived_locally"], S["reports_read"]),
           "",
           "Generated from [`data.json`](data.json) by `tools/render.py` – edit there, not here.", ""]
    n = 0
    for g, items in source_groups(D):
        out.append("## %s" % g); out.append("")
        for s in items:
            n += 1
            gate = " · *%s note, linked via The Block*" % s["access"] if s.get("access") else ""
            out.append("%d. %s – [*%s*](%s) – %s%s" % (n, s["publisher"], s["title"], s["url"],
                                                    month_label(s["published"]), gate))
        out.append("")
    return "\n".join(out)


# ---------- DATA.md: the data dictionary, generated from the schema + vocabularies ----------

def schema_type(p, defs):
    if "$ref" in p:
        return "`%s`" % p["$ref"].split("/")[-1]
    if "enum" in p:
        return " · ".join("`%s`" % ("null" if e is None else e) for e in p["enum"])
    t = p.get("type", "any")
    t = " or ".join(t) if isinstance(t, list) else t
    if t == "array" and "items" in p:
        return "array of " + schema_type(p["items"], defs)
    if p.get("pattern") == "^\\d{4}(-\\d{2}(-\\d{2})?)?(/\\d{4}(-\\d{2}(-\\d{2})?)?)?$":
        t += " (ISO date)"
    return t


def field_table(obj, defs):
    req = set(obj.get("required", []))
    rows = ["| Field | Type | Req. | Meaning |", "|---|---|---|---|"]
    for k, p in obj.get("properties", {}).items():
        rows.append("| `%s` | %s | %s | %s |" % (k, schema_type(p, defs), "✓" if k in req else "",
                                                 p.get("description", "").replace("|", "\\|")))
    return rows


def render_data_md(D, S):
    sch = load_json(SCHEMA_PATH)
    defs = sch.get("$defs", {})
    out = ["# Data dictionary", "",
           "Generated from [`data.schema.json`](data.schema.json) and the vocabularies in "
           "[`data.json`](data.json) by `tools/render.py` – edit those, not this file.", "",
           "- **Schema version:** %s (`schema_version` in data.json; a major bump means a breaking change)"
           % D.d["schema_version"],
           "- **Currency:** %s. %s" % (D.d["meta"]["currency"], D.d["meta"]["value_basis"]),
           "- **Dates:** ISO 8601 – `YYYY-MM-DD`, or `YYYY-MM` when the source gives only a month; "
           "`a/b` is an interval.",
           "- **Caveat:** %s" % D.d["meta"]["disclaimer"], "",
           "## Files", "",
           "| File | What it is |", "|---|---|",
           "| `data.json` | Canonical dataset. Everything else is generated from it. |",
           "| `data.schema.json` | JSON Schema (draft 2020-12) for data.json, enforced in CI. |",
           "| `data.csv` | One row per figure – %d rows. |" % len(D.d["figures"]),
           "| `positions.csv` | One row per filled matrix cell (desk × question). |",
           "| `llms.txt` | Summary for LLM crawlers. |", "",
           "## How to read the figures", "",
           "1. **Filter on `metric`.** Only `market_size` figures are market sizes. Revenue, fund AUM, "
           "stablecoin supply and settlement volume are different units and never belong on one axis.",
           "2. **Check `horizon`.** Forecasts are mostly 2030, not all – compare like with like.",
           "3. **Check `scope`.** The scope bucket, `includes_stablecoins` and `includes_permissioned` "
           "explain most of the spread between desks. Within a bucket the 2030 forecasts land ≤%s× apart; "
           "across buckets, %s×." % (S["scope_max_spread"], S["fc_spread"]),
           "4. **Filter `status = current`** for the latest view; superseded figures stay for the revision history.",
           ""]
    out += ["## `data.json` – top level", ""] + field_table(sch, defs) + [""]
    for name, obj in defs.items():
        if obj.get("type") != "object":
            continue
        out += ["### `%s`" % name, ""]
        if obj.get("description"):
            out += [obj["description"], ""]
        out += field_table(obj, defs) + [""]

    out += ["## Vocabularies", "", "### Scope buckets (`scopes`)", "",
            "| id | Label | Meaning |", "|---|---|---|"]
    out += ["| `%s` | %s | %s |" % (s["id"], s["label"], s["description"]) for s in D.d["scopes"]]
    out += ["", "### Metrics (`metrics`)", "", "| id | Meaning |", "|---|---|"]
    out += ["| `%s` | %s |" % (m["id"], m["label"]) for m in D.d["metrics"]]
    out += ["", "### Desk groups (`desk_groups`)", "", "| id | Label |", "|---|---|"]
    out += ["| `%s` | %s |" % (g["id"], g["label"]) for g in D.d["desk_groups"]]
    out += ["", "### Matrix questions and position values", ""]
    for q in D.d["questions"]:
        if q["type"] == "figure":
            out += ["- **`%s`** – %s: a cell cites one or more `figures`%s." % (
                q["id"], q["label"], (" (horizon %d)" % q["horizon"]) if q.get("horizon") else "")]
    out += [""]
    for q in D.d["questions"]:
        if q["type"] != "stance":
            continue
        out += ["**`%s`** – %s" % (q["id"], q["label"]), "", "| value | Label | Meaning |", "|---|---|---|"]
        out += ["| `%s` | %s | %s |" % (v["id"], v["label"], v["description"]) for v in q["values"]]
        out += [""]
    for title, cols in (("`data.csv` columns", DATA_CSV_COLUMNS), ("`positions.csv` columns", POSITIONS_CSV_COLUMNS)):
        out += ["## %s" % title, "", "| Column | Meaning |", "|---|---|"]
        out += ["| `%s` | %s |" % (c, desc.replace("|", "\\|")) for c, desc in cols]
        out += [""]
    return "\n".join(out)


def main():
    check = "--check" in sys.argv
    D = Data(load_json(DATA_PATH))
    S = compute_stats(D)
    with open(os.path.join(ROOT, "public", "index.html"), encoding="utf-8") as f:
        idx = f.read()
    with open(DATA_PATH, encoding="utf-8") as f:
        raw_data = f.read()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        raw_schema = f.read()
    outputs = {
        "public/index.html": render_index(D, S, idx),
        "public/data.json": raw_data,          # served copies of the canonical root files
        "public/data.schema.json": raw_schema,
        "public/data.csv": render_data_csv(D, S),
        "public/positions.csv": render_positions_csv(D, S),
        "public/llms.txt": render_llms(D, S),
        "SOURCES.md": render_sources_md(D, S),
        "DATA.md": render_data_md(D, S),
    }
    stale = []
    for name, content in outputs.items():
        path = os.path.join(ROOT, name)
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if cur != content:
            stale.append(name)
            if not check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
    if check and stale:
        print("OUT OF SYNC with data.json: %s\nRun: python3 tools/render.py" % ", ".join(stale))
        sys.exit(1)
    print(("checked, all in sync" if check else "regenerated: %s" % (", ".join(stale) or "nothing changed")))


if __name__ == "__main__":
    main()
