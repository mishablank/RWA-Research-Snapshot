#!/usr/bin/env python3
"""Check that data.json is internally consistent and that the page says only what
the data supports. CI runs this before `render.py --check`.

Usage:
    python3 tools/validate.py           schema, integrity, derived-claim and prose checks
    python3 tools/validate.py --links   also fetch every source URL (weekly CI job)

Exit 1 on any error; warnings are printed but do not fail the run.
Stdlib only; Python 3.9+.
"""
import os, re, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rwalib import (ROOT, DATA_PATH, SCHEMA_PATH, Data, load_json, parse_date, compute_stats,
                    iter_copy_strings, PH_RE, fmt_usd)

# Dollar amounts the prose quotes that are not yet figure records. Each is a
# consensus number with no source attached – tracked in GitHub issue #3
# (per-figure provenance). Remove an entry once it becomes a sourced figure.
KNOWN_UNSOURCED_USD = {
    300e12: "addressable base ($300T+)",
    250e9: "stablecoin supply ($250B+)",
    200e9: "Treasuries held in stablecoin reserves ($200B+)",
    300e6: "tokenized equities at the start of the period (sub-$300M)",
}
# Multiples quoted as reported by a source rather than computed from the data.
KNOWN_REPORTED_RATIOS = {
    "5–6×": "distributed-RWA growth since early 2025 – consensus, unsourced (#3)",
    "6×": "DefiLlama-reported growth in 14 months",
}

errors, warnings = [], []
def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)


# ---------- a small JSON Schema subset (the keywords data.schema.json uses) ----------

TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
         "array": list, "object": dict, "null": type(None)}

def type_ok(x, t):
    if t in ("integer", "number") and isinstance(x, bool):
        return False
    return isinstance(x, TYPES[t])

def check_schema(x, s, root, path):
    if "$ref" in s:
        node = root
        for part in s["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return check_schema(x, node, root, path)
    if "anyOf" in s:
        if not any(not check_schema_collect(x, sub, root) for sub in s["anyOf"]):
            err("%s: matches none of the allowed shapes" % path)
        return
    if "enum" in s and x not in s["enum"]:
        err("%s: %r not one of %r" % (path, x, s["enum"])); return
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(type_ok(x, t) for t in ts):
            err("%s: expected %s, got %s" % (path, "/".join(ts), type(x).__name__)); return
    if isinstance(x, str) and "pattern" in s and not re.search(s["pattern"], x):
        err("%s: %r does not match %s" % (path, x, s["pattern"]))
    if isinstance(x, (int, float)) and not isinstance(x, bool) and "minimum" in s and x < s["minimum"]:
        err("%s: %r below minimum %r" % (path, x, s["minimum"]))
    if isinstance(x, list):
        if len(x) < s.get("minItems", 0):
            err("%s: needs at least %d items" % (path, s["minItems"]))
        if "items" in s:
            for i, v in enumerate(x):
                check_schema(v, s["items"], root, "%s[%d]" % (path, i))
    if isinstance(x, dict):
        for k in s.get("required", []):
            if k not in x:
                err("%s: missing required field %r" % (path, k))
        props = s.get("properties", {})
        for k, v in x.items():
            if k in props:
                check_schema(v, props[k], root, "%s.%s" % (path, k))
            elif s.get("additionalProperties") is False:
                err("%s: unexpected field %r" % (path, k))

def check_schema_collect(x, s, root):
    """Run check_schema in isolation; return its errors instead of recording them."""
    global errors
    saved, errors = errors, []
    check_schema(x, s, root, "")
    found, errors = errors, saved
    return found


# ---------- integrity ----------

def label_for(d, i):
    return "%s[%s]" % (d, i)

def check_integrity(D):
    d = D.d
    for coll in ("desks", "sources", "figures", "scopes", "metrics", "desk_groups", "questions"):
        seen = set()
        for x in d[coll]:
            if x["id"] in seen:
                err("%s: duplicate id %r" % (coll, x["id"]))
            seen.add(x["id"])

    def ref(kind, key, where):
        if key not in getattr(D, kind):
            err("%s: unknown %s id %r" % (where, kind.rstrip("s"), key))
            return False
        return True

    for x in d["desks"]:
        ref("groups", x["group"], label_for("desks", x["id"]))
    w0, w1 = parse_date(d["meta"]["window"]["start"])[0], parse_date(d["meta"]["window"]["end"])[1]
    for s in d["sources"]:
        where = label_for("sources", s["id"])
        ref("desks", s["desk"], where)
        a, b = parse_date(s["published"])
        if b < w0.replace(day=1) or a > w1:
            err("%s: published %s falls outside the window %s – %s" % (where, s["published"], w0, w1))
        if s.get("access") == "client-only" and "theblock.co" not in s["url"]:
            warn("%s: client-only source links somewhere other than The Block – check the credit line" % where)

    for f in d["figures"]:
        where = label_for("figures", f["id"])
        ok = ref("desks", f["desk"], where) & ref("sources", f["source"], where) & ref("metrics", f["metric"], where)
        if f.get("scope") is not None:
            ref("scopes", f["scope"], where)
        if ok and D.sources[f["source"]]["desk"] != f["desk"]:
            err("%s: desk %r but its source belongs to %r" % (where, f["desk"], D.sources[f["source"]]["desk"]))
        lo, hi, v = f.get("low_usd"), f.get("high_usd"), f["value_usd"]
        if (lo is None) != (hi is None):
            err("%s: low_usd and high_usd must be given together" % where)
        if lo is not None and not (lo <= v <= hi):
            err("%s: value %s outside its range %s–%s" % (where, fmt_usd(v), fmt_usd(lo), fmt_usd(hi)))
        if lo is not None and f.get("point_estimate") is True:
            err("%s: point_estimate is true but a range is given" % where)
        if v <= 0:
            err("%s: value must be positive" % where)
        if f["kind"] == "today" and f["horizon"] is not None:
            err("%s: a 'today' figure cannot have a horizon" % where)
        if f["kind"] == "forecast" and f["horizon"] is None and f["metric"] == "market_size":
            err("%s: a market-size forecast needs a horizon year" % where)
        try:
            pub = parse_date(f["published"])
        except ValueError as e:
            err("%s: %s" % (where, e)); continue
        if ok:
            sa, sb = parse_date(D.sources[f["source"]]["published"])
            if pub[0] < sa or pub[1] > sb:
                err("%s: published %s is outside its source's date %s"
                    % (where, f["published"], D.sources[f["source"]]["published"]))
        if f["horizon"] is not None and f["horizon"] < pub[0].year:
            err("%s: horizon %d is before publication" % (where, f["horizon"]))
        if f.get("as_of") and parse_date(f["as_of"])[0] > pub[1]:
            err("%s: as_of %s is after publication %s" % (where, f["as_of"], f["published"]))
        if f["status"] == "superseded":
            if not f.get("superseded_by"):
                err("%s: superseded but no superseded_by" % where)
            elif ref("figures", f["superseded_by"], where):
                nf = D.figures[f["superseded_by"]]
                if nf["desk"] != f["desk"]:
                    err("%s: superseded by another desk's figure" % where)
                if parse_date(nf["published"])[0] < pub[0]:
                    err("%s: superseded by an older figure" % where)
        elif f.get("superseded_by"):
            err("%s: superseded_by set on a current figure" % where)
        for r in f.get("reaffirmed_in", []):
            if ref("sources", r, where) and D.sources[r]["desk"] != f["desk"]:
                err("%s: reaffirmed in another desk's source %r" % (where, r))
        if f["metric"] != "market_size" and f.get("scope") and f["metric"] != "stablecoin_supply":
            warn("%s: %s figure carries a scope bucket – buckets describe market sizes" % (where, f["metric"]))

    # views: what the chart plots must be current, comparable and honestly labelled
    horizon = next((q.get("horizon") for q in d["questions"] if q["id"] == "size_2030"), None)
    for view, kind in (("chart_forecast", "forecast"), ("chart_today", "today")):
        for i, e in enumerate(d["views"][view]):
            where = "views.%s[%d]" % (view, i)
            for key in ("figure", "alt"):
                if key not in e or not ref("figures", e[key], where):
                    continue
                f = D.figures[e[key]]
                if f["kind"] != kind:
                    err("%s: %s is a %r figure in the %s chart" % (where, f["id"], f["kind"], kind))
                if f["metric"] != "market_size":
                    err("%s: %s is %s, not a market size – it cannot share this axis" % (where, f["id"], f["metric"]))
                if f["status"] != "current":
                    err("%s: %s is superseded" % (where, f["id"]))
                if key == "alt" and f["desk"] != D.figures[e["figure"]]["desk"]:
                    err("%s: the hollow dot must be the same desk's figure" % where)
            if e.get("alt") and not e.get("alt_label"):
                err("%s: alt without alt_label" % where)
            if e.get("scope"):
                ref("scopes", e["scope"], where)
            f = D.figures.get(e.get("figure"))
            if f and kind == "forecast" and horizon and f["horizon"] != horizon:
                lbl = e.get("label") or D.label(f)
                yy = "%02d" % (f["horizon"] % 100)
                if yy not in lbl and str(f["horizon"]) not in lbl:
                    err("%s: %s is a %d figure on the %d chart – its label must say so (e.g. ’%s)"
                        % (where, f["id"], f["horizon"], horizon, yy))
            if f and not (e.get("scope") or f["scope"]):
                err("%s: plotted figure has no scope bucket to colour it" % where)

    for i, r in enumerate(d["tables"]["forecast"]):
        where = "tables.forecast[%d]" % i
        if ref("figures", r["figure"], where):
            f = D.figures[r["figure"]]
            if f["kind"] != "forecast":
                err("%s: not a forecast" % where)
            if horizon and f["horizon"] != horizon and str(f["horizon"]) not in r["note"]:
                err("%s: %d figure in the 2030 table – say so in its note" % (where, f["horizon"]))
    for i, r in enumerate(d["tables"]["today"]):
        where = "tables.today[%d]" % i
        for x in r["figures"]:
            if ref("figures", x, where) and D.figures[x]["kind"] != "today":
                err("%s: %s is not a 'today' figure" % (where, x))
        if len({D.figures[x]["desk"] for x in r["figures"] if x in D.figures}) > 1:
            err("%s: one table row mixes desks" % where)
    for i, r in enumerate(d["tables"]["lead_asset"]):
        ref("desks", r["desk"], "tables.lead_asset[%d]" % i)

    # matrix positions
    seen = set()
    for i, p in enumerate(d["positions"]):
        where = "positions[%d] (%s × %s)" % (i, p.get("desk"), p.get("question"))
        if not (ref("desks", p["desk"], where) and ref("questions", p["question"], where)):
            continue
        key = (p["desk"], p["question"])
        if key in seen:
            err("%s: duplicate cell" % where)
        seen.add(key)
        q = D.questions[p["question"]]
        if q["type"] == "figure":
            if "figures" not in p or "value" in p:
                err("%s: a figure question cites figures, not a value" % where); continue
            for x in p["figures"]:
                if ref("figures", x, where):
                    f = D.figures[x]
                    if f["desk"] != p["desk"]:
                        err("%s: cites another desk's figure %s" % (where, x))
                    if f["status"] != "current":
                        err("%s: cites superseded figure %s" % (where, x))
                    want = "today" if p["question"] == "size_today" else "forecast"
                    if f["kind"] != want:
                        err("%s: %s is a %r figure" % (where, x, f["kind"]))
        else:
            if "value" not in p or "figures" in p:
                err("%s: a stance question takes a value, not figures" % where); continue
            if p["value"] not in {v["id"] for v in q["values"]}:
                err("%s: %r is not in the %s vocabulary" % (where, p["value"], q["id"]))
        if p.get("scope"):
            ref("scopes", p["scope"], where)
    for x in D.matrix_desks():
        if not D.desk_sources(x):
            err("desks[%s]: holds positions but has no source" % x)

    # staircase + revisions
    for i, r in enumerate(d["staircase"]["rungs"]):
        where = "staircase.rungs[%d]" % i
        for x in r["figures"]:
            if ref("figures", x, where) and D.figures[x]["kind"] != "today":
                    err("%s: %s is not a 'today' figure" % (where, x))
        if r.get("scope"):
            ref("scopes", r["scope"], where)
        elif r["figures"] and r["figures"][0] in D.figures and not D.figures[r["figures"][0]]["scope"]:
            err("%s: figure has no scope bucket – set the rung's scope" % where)
    vals = [max(D.figures[x]["value_usd"] for x in r["figures"] if x in D.figures)
            for r in d["staircase"]["rungs"]]
    forks = [i for i, r in enumerate(d["staircase"]["rungs"]) if r.get("fork")]
    for i in range(1, len(vals)):
        # fork routes are alternatives to each other, not successive steps
        prev = max(vals[j] for j in range(i) if not (j in forks and i in forks))
        if vals[i] < prev * 0.95:
            err("staircase.rungs[%d]: a step down (%s after %s) – each rung should widen the count"
                % (i, fmt_usd(vals[i]), fmt_usd(prev)))
    dates = []
    for i, r in enumerate(d["revisions"]):
        where = "revisions[%d]" % i
        dates.append(parse_date(r["date"])[0])
        if r["desk"] is not None:
            ref("desks", r["desk"], where)
        for s in r["sources"]:
            ref("sources", s, where)
        for x in r.get("figures", []):
            ref("figures", x, where)
        if r.get("drift"):
            a, b = r["drift"]["from"], r["drift"]["to"]
            if ref("figures", a, where) and ref("figures", b, where):
                if D.figures[a].get("superseded_by") != b:
                    err("%s: drift from %s should be superseded_by %s" % (where, a, b))
    if dates != sorted(dates):
        err("revisions: not in date order")
    if dates and max(dates) > parse_date(d["meta"]["updated"])[1]:
        err("revisions: an entry is dated after meta.updated (%s)" % d["meta"]["updated"])
    if dates and parse_date(d["meta"]["updated"])[0] not in dates:
        warn("meta.updated (%s) has no matching revision-log entry" % d["meta"]["updated"])



# ---------- claims: placeholders, prose figures, ratios, counts ----------

USD_RE = re.compile(r"\$(\d+(?:\.\d+)?)\s?(T|B|M|trillion|billion|million)(?![a-z])")
RATIO_RE = re.compile(r"(?<![\w×])~?(\d+(?:\.\d+)?(?:–\d+(?:\.\d+)?)?)×")
SCALE = {"T": 1e12, "trillion": 1e12, "B": 1e9, "billion": 1e9, "M": 1e6, "million": 1e6}
GEN_RE = re.compile(r"<!-- gen:(\w+) -->.*?<!-- /gen:\1 -->", re.S)

def known_values(D):
    vs = set()
    for f in D.d["figures"]:
        for k in ("value_usd", "low_usd", "high_usd"):
            if f.get(k) is not None:
                vs.add(f[k])
    return vs

def usd_ok(v, known):
    return any(abs(v - k) <= 0.03 * k for k in known) or any(abs(v - k) <= 0.03 * k for k in KNOWN_UNSOURCED_USD)

def lint_text(text, where, known):
    for m in USD_RE.finditer(text):
        v = float(m.group(1)) * SCALE[m.group(2)]
        if not usd_ok(v, known):
            err("%s: %s is not a figure in data.json – add it as a figure record, or fix the number"
                % (where, m.group(0)))
    for m in RATIO_RE.finditer(text):
        if m.group(1) + "×" not in KNOWN_REPORTED_RATIOS:
            err("%s: hand-typed multiple %s – use a {stat:…} placeholder / gen:s_ marker so it is computed"
                % (where, m.group(0)))

def page_prose(src):
    """index.html with generated regions, <style> and <script> removed; tags stripped."""
    body = GEN_RE.sub(" ", src)
    body = re.sub(r"<style.*?</style>|<script.*?</script>", " ", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", body)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def check_claims(D, S):
    known = known_values(D)
    for path, text in iter_copy_strings(D.d):
        for m in PH_RE.finditer(text):
            kind, key = m.groups()
            if kind == "stat" and key not in S:
                err("%s: unknown placeholder {stat:%s}" % (path, key))
            if kind == "fig" and key not in D.figures:
                err("%s: unknown placeholder {fig:%s}" % (path, key))
        lint_text(PH_RE.sub("", text), path, known)

    with open(os.path.join(ROOT, "public", "index.html"), encoding="utf-8") as f:
        src = f.read()
    for m in re.finditer(r"<!-- gen:s_(\w+) -->", src):
        if m.group(1) not in S:
            err("index.html: unknown stat marker gen:s_%s" % m.group(1))
    for line in page_prose(src).splitlines():
        lint_text(line, "index.html prose", known)

    # README counts that aren't generated
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    for m in re.finditer(r"(\d+) desks (?:×|down)", readme):
        if m.group(1) != S["matrix_desks"]:
            err("README.md: says %s desks, the matrix has %s" % (m.group(1), S["matrix_desks"]))
    for m in re.finditer(r"(\d+) research reports", readme):
        if m.group(1) != S["reports_read"]:
            err("README.md: says %s research reports, meta says %s" % (m.group(1), S["reports_read"]))

    # the static share card
    og = D.d["meta"].get("og_card")
    if og:
        want = {"reports_read": int(S["reports_read"]), "fc_spread": int(S["fc_spread"])}
        for k, v in want.items():
            if og.get(k) != v:
                err("og-card.png says %s = %s, the data says %s – re-render the card" % (k, og.get(k), v))
        if fmt_usd(og["fc_lo_usd"]) != S["fc_lo"] or fmt_usd(og["fc_hi_usd"]) != S["fc_hi"]:
            err("og-card.png headline range is stale – re-render the card")
        if og.get("updated") and og["updated"][:7] != D.d["meta"]["updated"][:7]:
            warn("og-card.png says 'Updated %s', the page was updated %s – re-render when convenient"
                 % (og["updated"], D.d["meta"]["updated"]))


# ---------- links (weekly) ----------

def check_links(D):
    ua = "Mozilla/5.0 (compatible; rwaresearch-linkcheck/1.0; +https://rwaresearch.info/)"
    for s in D.d["sources"]:
        req = urllib.request.Request(s["url"], headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            err("sources[%s]: %s unreachable (%s)" % (s["id"], s["url"], getattr(e, "reason", e))); continue
        if code in (401, 403, 429):
            warn("sources[%s]: HTTP %d (bot-blocked?) %s – check by hand" % (s["id"], code, s["url"]))
        elif code >= 400:
            err("sources[%s]: HTTP %d %s" % (s["id"], code, s["url"]))


def main():
    d = load_json(DATA_PATH)
    schema = load_json(SCHEMA_PATH)
    check_schema(d, schema, schema, "data")
    if errors:   # structural problems make the deeper checks meaningless
        report(); return
    D = Data(d)
    check_integrity(D)
    if not errors:
        try:
            S = compute_stats(D)
        except Exception as e:
            err("computing stats failed: %r" % e); report(); return
        check_claims(D, S)
    if "--links" in sys.argv:
        check_links(D)
    report()


def report():
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print("\n%d error(s)" % len(errors))
        sys.exit(1)
    print("data.json valid (%d warning%s)" % (len(warnings), "" if len(warnings) == 1 else "s"))


if __name__ == "__main__":
    main()
