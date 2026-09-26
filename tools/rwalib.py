"""Shared helpers for render.py and validate.py: loading data.json, lookups,
number/date formatting, template placeholders and the computed headline stats.

Stdlib only; Python 3.9+.
"""
import datetime, json, math, os, re
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.json")
SCHEMA_PATH = os.path.join(ROOT, "data.schema.json")

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Data:
    """data.json plus id lookups."""

    def __init__(self, d):
        self.d = d
        self.desks = {x["id"]: x for x in d.get("desks", [])}
        self.groups = {x["id"]: x for x in d.get("desk_groups", [])}
        self.sources = {x["id"]: x for x in d.get("sources", [])}
        self.figures = {x["id"]: x for x in d.get("figures", [])}
        self.scopes = {x["id"]: x for x in d.get("scopes", [])}
        self.metrics = {x["id"]: x for x in d.get("metrics", [])}
        self.questions = {x["id"]: x for x in d.get("questions", [])}

    def label(self, fig):
        return fig.get("label") or self.desks[fig["desk"]]["name"]

    def desk_group(self, desk_id):
        return self.groups[self.desks[desk_id]["group"]]["label"]

    def value_label(self, qid, vid):
        return next(v for v in self.questions[qid]["values"] if v["id"] == vid)

    def matrix_desks(self):
        """Desk ids that hold at least one position, in desks[] order."""
        held = {p["desk"] for p in self.d["positions"]}
        return [x["id"] for x in self.d["desks"] if x["id"] in held]

    def desk_sources(self, desk_id):
        return [s for s in self.d["sources"] if s["desk"] == desk_id]


# ---------- numbers ----------

def fmt_usd(v):
    """Mirrors fmt() in the page's chart script so tables and chart agree."""
    if v >= 1e12:
        t = v / 1e12
        s = ("%d" % round(t)) if t >= 10 else ("%.2f" % t).rstrip("0").rstrip(".")
        return "$%sT" % s
    if v >= 1e9:
        b = v / 1e9
        s = ("%d" % round(b)) if b >= 100 else ("%.1f" % b).rstrip("0").rstrip(".")
        return "$%sB" % s
    return "$%dM" % round(v / 1e6)


def fmt_fig(fig, tilde=True):
    return ("~" if tilde and fig.get("approx") else "") + fmt_usd(fig["value_usd"])


def fmt_ratio(x, nd=1):
    s = ("%." + str(nd) + "f") % x
    return s.rstrip("0").rstrip(".") if "." in s else s


def words(n):
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


# ---------- dates ----------

DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$")


def parse_date(s):
    """ISO 8601 date at year, month or day precision, or an interval a/b.
    Returns (first_day, last_day) as datetime.date."""
    if "/" in s:
        a, b = s.split("/", 1)
        return parse_date(a)[0], parse_date(b)[1]
    m = DATE_RE.match(s)
    if not m:
        raise ValueError("not an ISO date: %r" % s)
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    if d:
        x = datetime.date(y, int(mo), int(d))
        return x, x
    if mo:
        mo = int(mo)
        first = datetime.date(y, mo, 1)
        nxt = datetime.date(y + (mo == 12), mo % 12 + 1, 1)
        return first, nxt - datetime.timedelta(days=1)
    return datetime.date(y, 1, 1), datetime.date(y, 12, 31)


def month_label(s):
    """'2026-05-15' / '2026-05' -> 'May 2026'; '2026-04/2026-06' -> 'Apr–Jun 2026'."""
    if "/" in s:
        a, b = (parse_date(x)[0] for x in s.split("/", 1))
        if a.year == b.year:
            return "%s–%s %d" % (MONTHS[a.month - 1], MONTHS[b.month - 1], b.year)
        return "%s %d – %s %d" % (MONTHS[a.month - 1], a.year, MONTHS[b.month - 1], b.year)
    a = parse_date(s)[0]
    return "%s %d" % (MONTHS[a.month - 1], a.year)


def day_label(s):
    a = parse_date(s)[0]
    return "%d %s %d" % (a.day, MONTHS[a.month - 1], a.year)


def window_label(w):
    a, b = parse_date(w["start"])[0], parse_date(w["end"])[0]
    ya = "" if a.year == b.year else " %d" % a.year
    return "%d %s%s – %d %s %d" % (a.day, MONTHS[a.month - 1], ya, b.day, MONTHS[b.month - 1], b.year)


def published_label(D, fig, style="chart"):
    """'May 2026', plus the months a figure was reaffirmed in later sources.
    chart style: 'May · Aug 2026'; table style: 'May 2026 · reaff. Aug'."""
    base = parse_date(fig["published"])[0]
    later = [parse_date(D.sources[r]["published"])[0] for r in fig.get("reaffirmed_in", [])]
    if not later:
        return month_label(fig["published"])
    if style == "table":
        return "%s · reaff. %s" % (month_label(fig["published"]),
                                   " · ".join(MONTHS[x.month - 1] for x in later))
    ms = [MONTHS[base.month - 1]] + [MONTHS[x.month - 1] for x in later]
    return "%s %d" % (" · ".join(ms), later[-1].year)


# ---------- computed stats ----------

def view_figs(D, view):
    return [D.figures[e["figure"]] for e in D.d["views"][view]]


def compute_stats(D):
    """Every number the prose quotes about the dataset itself. Anything here can be
    used as {stat:NAME} in data.json copy or <!-- gen:s_NAME --> in index.html."""
    d, m = D.d, D.d["meta"]
    s = {}
    fc = view_figs(D, "chart_forecast")
    td_entries = d["views"]["chart_today"]
    td = view_figs(D, "chart_today")
    td_all = td + [D.figures[e["alt"]] for e in td_entries if e.get("alt")]

    s["reports_read"] = str(m["reports_read"])
    s["archived_locally"] = str(m["archived_locally"])
    s["sources_n"] = str(len(d["sources"]))
    s["window"] = window_label(m["window"])
    s["updated"] = day_label(m["updated"])
    s["updated_short"] = s["updated"].rsplit(" ", 1)[0]
    s["updated_month"] = month_label(m["updated"])

    lo, hi = min(f["value_usd"] for f in fc), max(f["value_usd"] for f in fc)
    s["fc_lo"], s["fc_hi"] = fmt_usd(lo), fmt_usd(hi)
    s["fc_spread"] = "%d" % round(hi / lo)
    s["fc_n"] = str(len(fc))
    fc_desks = len({f["desk"] for f in fc})
    s["fc_desks"] = str(fc_desks)
    horizon = next(q["horizon"] for q in d["questions"] if q["id"] == "size_2030")
    off = [f for f in fc if f["horizon"] != horizon]
    off_short = ", ".join("%s: %d" % (D.desks[f["desk"]].get("short") or D.desks[f["desk"]]["name"], f["horizon"])
                          for f in off)
    off_long = " and ".join("%s’s, which runs to %d" % (D.desks[f["desk"]]["name"], f["horizon"]) for f in off)
    s["fc_sub"] = "%d forecasts · %d desks · %d horizon%s" % (
        len(fc), fc_desks, horizon, (" (%s)" % off_short) if off else "")
    s["fc_dek_lead"] = "%s forecasts from %s desks, all for %d%s" % (
        words(len(fc)).capitalize(), words(fc_desks), horizon, (" bar " + off_long) if off else "")

    tlo, thi = min(f["value_usd"] for f in td), max(f["value_usd"] for f in td)
    s["td_lo"], s["td_hi"] = fmt_usd(tlo), fmt_usd(thi)
    s["td_spread"] = "%d" % round(thi / tlo)
    s["td_desks"] = str(len({f["desk"] for f in td}))
    s["td_numbers"] = str(len(td_all))

    s["matrix_desks"] = str(len(D.matrix_desks()))
    s["questions"] = str(len(d["questions"]))

    # widest within-bucket spread of the 2030 forecasts – the "by scope" thesis
    spreads = []
    for sc in d["scopes"]:
        vs = [f["value_usd"] for f in fc if f["scope"] == sc["id"]]
        if len(vs) > 1:
            spreads.append(max(vs) / min(vs))
    s["scope_max_spread"] = fmt_ratio(max(spreads)) if spreads else "1"

    forks = {r["fork"]: max(D.figures[x]["value_usd"] for x in r["figures"])
             for r in d["staircase"]["rungs"] if r.get("fork")}
    if len(forks) == 2:
        a, b = forks.values()
        s["fork_gap_pct"] = "%d" % round(abs(a - b) / min(a, b) * 100)

    perm = [D.figures[e["alt"]]["value_usd"] / D.figures[e["figure"]]["value_usd"]
            for e in td_entries if e.get("alt") and D.figures[e["alt"]].get("includes_permissioned")]
    if perm:
        s["permissioned_x"] = "%d" % round(max(perm))

    drift = [r for r in d["revisions"] if r.get("drift")]
    if drift:
        r = drift[-1]["drift"]
        a, b = D.figures[r["from"]], D.figures[r["to"]]
        days = (parse_date(b["published"])[0] - parse_date(a["published"])[0]).days
        s["drift_from"], s["drift_to"] = fmt_usd(a["value_usd"]), fmt_usd(b["value_usd"])
        s["drift_x"] = fmt_ratio(a["value_usd"] / b["value_usd"])
        s["drift_pct"] = "%d" % round((1 - b["value_usd"] / a["value_usd"]) * 100)
        s["drift_weeks"] = "%d" % round(days / 7)
        s["drift_desk"] = D.desks[a["desk"]].get("short") or D.desks[a["desk"]]["name"]

    tails = [f for f in fc if f.get("scenario") == "tail"]
    if tails:
        t = tails[0]
        base = next((f for f in td if f["desk"] == t["desk"]), None)
        if base:
            s["tail_x"] = "%d" % round(t["value_usd"] / base["value_usd"])

    s["constraint_desks"] = str(sum(1 for p in d["positions"] if p["question"] == "constraint"))

    for k in list(s):
        if s[k].isdigit():
            s[k + "_words"] = words(int(s[k]))
            s[k + "_Words"] = words(int(s[k])).capitalize()
    return s


# ---------- templates ----------

PH_RE = re.compile(r"\{(stat|fig):([\w\-]+)\}")


def resolve(text, D, stats):
    def sub(m):
        kind, key = m.groups()
        if kind == "stat":
            if key not in stats:
                raise KeyError("unknown {stat:%s}" % key)
            return stats[key]
        if key not in D.figures:
            raise KeyError("unknown {fig:%s}" % key)
        return fmt_fig(D.figures[key])
    return PH_RE.sub(sub, text)


def md_inline(text):
    """Escape, then **bold** -> <b>, *em* -> <em>. The only markup data.json copy may carry."""
    h = escape(text, quote=False)
    h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", h)


def iter_copy_strings(d):
    """(path, text) for every editorial string in data.json that reaches a reader."""
    def walk(x, path):
        if isinstance(x, str):
            yield path, x
        elif isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, path + "." + k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from walk(v, "%s[%d]" % (path, i))
    for key in ("views", "tables", "staircase", "revisions", "copy"):
        yield from walk(d.get(key), key)
    for f in d.get("figures", []):
        yield "figures[%s].definition" % f["id"], f.get("definition", "")
