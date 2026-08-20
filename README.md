# The State of RWAs – Where the Research Disagrees

**Everyone agrees RWAs are coming. Nobody agrees how big.**

A single-page editorial synthesis that cross-reads **63 research reports** on real-world assets and tokenization – global banks, asset managers, the Big Four, crypto-native desks and the official sector – published between **29 Mar and 10 Aug 2026**. The finding: the desks converge almost completely on the *direction of travel* and contradict each other on nearly everything you can put a number on.

> **Updated 20 Aug 2026** – the dataset behind the page is now published (`data.json` · `data.csv` · `positions.csv` · `llms.txt`), the page is generated from it (`tools/render.py`, CI-enforced), and three things were added: a **By scope** chart view (within a scope bucket the desks land ≤1.7× apart – the 35× spread is definitional), a **definitional staircase** ($19B → $695B in four widening steps, with the 21Shares/SC fork), and a **revision log** appendix. Grayscale's ~$30B "today" figure and permissioned-rails lean were extracted from *Investing in the Tokenization Megatrend* (Apr 2026) – the matrix gains a 19th desk.

> **Updated 13 Aug 2026** – adds Binance Research's *Half-Year 2026: On-Chain Markets* (30 Jul) and Standard Chartered's *Chainlink: Owning the rails* (10 Aug, institutional-client note, cited via The Block's same-day coverage). Two consequential changes: Binance **cut its 2030 base case from $1.6T to $661B** (the old base is now its bull case), and SC published its first sourced "today" figure – **~$340B incl. stablecoins**, landing within 3% of 21Shares' $350B by a completely different route (stablecoins in vs. permissioned networks in).

The headline tension: **$400B → $14T** for the same 2030 horizon. A 35× spread. And an even wider ~36× spread on what the market is worth *today*.

No build step to serve, no dependencies, no framework. One page – [`index.html`](index.html) – whose data-bearing blocks (chart, tables, matrix, staircase, revision log, source register) are generated from one canonical dataset, [`data.json`](data.json).

---

## The argument in three lines

1. **The facts of today are settled.** ~0.01% penetration of a $300T+ addressable base, ~$15B of tokenized Treasuries anchoring the market, institutional issuers now leading growth. Nobody disputes this.
2. **Every forward number is contested.** 35× on 2030 size, 36× on today's size, and a straight split on whether stablecoins are the settlement rail (crypto desks) or a flawed form of money to be superseded (BIS).
3. **Most of the disagreement is definitional, not factual.** Three choices explain the bulk of it – what counts as an RWA (free-float vs. represented vs. full settlement layer), which chains you count (public-only undercounts ~10×), and whether stablecoins are in.

---

## What's on the page

| # | Section | What it does |
|---|---------|--------------|
| 01 | Hero | The $400B → $14T tension, the source base by category |
| 02 | Consensus | The five numbers every desk signs up to |
| 03 | The matrix | 18 desks × 6 questions on one grid |
| 04 | Discrepancy 01 – the 2030 number | Interactive forecast chart + study table |
| 05 | Discrepancy 02 – the denominator | Why "today's" market size ranges $19.3B → $695B |
| 06 | Discrepancy 03 – stablecoins | Rail, coexistence layer, or flawed money |
| 07 | Discrepancy 04 – the lead asset | Treasuries lead now; after that, pick a fight |
| 08 | Discrepancy 05 – whose chain | Public trackers vs. the permissioned layer nobody sees |
| 09 | Discrepancy 06 – the constraint | Six desks, six different bottlenecks |
| 10 | Takeaway | How to read any RWA report without being fooled by scope |
| R | Revision log | Dated changes to the numbers – and the Binance $1.6T → $661B drift |
| A | Sources | The register – the 22 reports figures are attributed to, linked to the publisher (see also [`SOURCES.md`](SOURCES.md)) |

~12 minute read.

### The chart (section 04)

Three dataset toggles – **2030 forecast / market today / by scope** – and **linear / log**, over the same study dataset. **By scope** regroups the six 2030 forecasts by what they count: within a bucket the desks land ≤1.7× apart, across buckets 35× – the page's thesis, shown rather than asserted. The encoding is deliberate and switches with the scale:

- **Linear** → marks are **bars**. Length encodes magnitude from a real zero.
- **Log** → marks are **dots**. There is no zero on a log axis, so bar length would be meaningless; only position is read.
- **Colour** encodes the *definition* used (free-float · public-chain · securities · broad · all-in incl. stablecoins), not the desk.
- **Hollow dot** = the same desk's second sourced figure under a wider scope (21Shares $31B → $350B; Standard Chartered $4T '28 → $2.7T DeFi-active '30).
- **Band** = a published scenario range (Binance $203B–$1.6T around a $661B base – the Jul 2026 framework that cut the May base case of $1.6T).
- **`pt. est.`** = the source publishes a point estimate with no range.
- On linear with two figures, the solid bar stops at the **lower** number and extends in a tint – the solid block never overstates the most conservative sourced figure.

Log tick density adapts to plot width (narrow viewports drop to one tick per decade so labels don't overprint), so the chart re-renders on resize.

### The matrix (section 03)

18 desks down, six questions across, grouped by desk type. Read down a column to see whether a question is settled or split; read across a row for one desk's whole position. Empty rings are desks in the source base that took **no public position** on that question – and most cells are empty, which is itself the finding: 63 reports, few desks answering more than two of these six questions.

---

## Source base

63 reports cross-read, 29 Mar – 10 Aug 2026 (50 archived locally – **the source documents are not in this repo**; the page reproduces figures as reported, with dates). The two August additions: Binance Research *Half-Year 2026: On-Chain Markets* (official PDF) and Standard Chartered *Chainlink: Owning the rails* (client-only; via The Block's coverage).

- **Banks** – Citi · J.P. Morgan · Morgan Stanley · Standard Chartered · Deutsche Bank · HSBC · Barclays · Nomura
- **Managers & issuers** – BlackRock · Franklin Templeton · Securitize · Grayscale · 21Shares · Bitwise
- **Consultancies** – BCG · McKinsey · PwC · Oliver Wyman · Deloitte · KPMG
- **Crypto research** – Binance · Pantera · Messari · Galaxy · DefiLlama · CoinGecko · BeInCrypto · RWA.xyz · Keyrock
- **Official sector** – BIS · IMF · GFMA · OMFIF

The 22 reports the page attributes figures to are linked – publisher page or PDF where public, The Block's same-day coverage for the two client-only Standard Chartered notes – in the page's Sources appendix and in [`SOURCES.md`](SOURCES.md).

---

## Repo layout

```
index.html            the site – markup, design tokens, CSS, chart engine; data blocks generated
data.json             the canonical dataset – figures, matrix positions, revisions, sources
data.csv              market-size figures, flat table (generated)
positions.csv         the 6-question desk matrix, flat table (generated)
llms.txt              machine-readable page summary + data pointers (generated)
SOURCES.md            the source register in markdown – same 22 entries as the page (generated)
tools/render.py       the generator: data.json → index.html regions + derived files
.github/workflows/    data-check.yml – CI fails if index.html is out of sync with data.json
og-card.png           1200×630 share card (Open Graph / Twitter image)
apple-touch-icon.png  180×180 home-screen icon (iOS ignores SVG favicons)
wrangler.jsonc        Cloudflare static-assets config (worker name: rwa-snapshot)
.gitignore            wrangler local state + env files
README.md             this file
```

## Run it locally

Any static server works – there's nothing to build.

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`. Or with Wrangler, matching the deploy target:

```bash
npx wrangler dev
```

Opening `index.html` directly off the filesystem also works; only the Google Fonts request needs network.

## Deploy

The page ships as static assets on Cloudflare. `wrangler.jsonc` serves the repo root (`assets.directory: "."`) under the worker name `rwa-snapshot`:

```bash
npx wrangler deploy
```

Git-integration deploys from `main` work equally well – there is no build command and no output directory to configure.

Two things worth knowing before you touch that config: serving `.` publishes every file in the root, including this README and `wrangler.jsonc`; and the `nodejs_compat` flag is inert here, since there is no worker script to run.

---

## Editing the content

**[`data.json`](data.json) is the single source of truth.** The chart, the desk matrix, the three study tables, the definitional staircase, the revision log, the source register, both CSVs, `llms.txt` and `SOURCES.md` are all generated from it:

```bash
python3 tools/render.py          # regenerate everything from data.json
python3 tools/render.py --check  # exit 1 if anything is out of sync (CI runs this)
```

The generator (stdlib-only, Python 3.9+) rewrites the regions of `index.html` between `<!-- gen:NAME -->` markers and the derived files. A GitHub Action (`.github/workflows/data-check.yml`) fails any push where `index.html` and `data.json` disagree – the failure mode where the chart and the table under it contradict each other is now structurally impossible.

To add or revise a study: edit `data.json` (a chart item, its table row, its matrix cells, a `revisions` entry, and – if it's a new report – a `sources` entry), run the generator, commit both. Chart item fields: `v` headline figure in dollars · `lo`/`hi` published scenario band · `alt`/`altLbl` same desk, wider scope (the hollow dot) · `cat` scope bucket keyed to `cats` (drives colour + legend) · `pt: 1` point estimate · `scope`/`src` the tooltip · `ref` the source id.

**Editorial prose stays hand-written** in `index.html` – deks, callouts, section copy. Only the data-bearing blocks are generated.

**Sections are deep-linkable** – every section has an id (`#consensus`, `#map`, `#forecast`, `#denominator`, `#stablecoins`, `#lead-asset`, `#rails`, `#constraint`, `#takeaway`, `#sources`), each `h2` grows a `#` anchor on hover, and a fixed progress rail (`.rail`, shown ≥1280px) tracks the active section via IntersectionObserver.

**Share metadata** lives in the `<head>`: description, canonical, Open Graph + Twitter cards pointing at `og-card.png` (1200×630, same design tokens), and JSON-LD `Article` markup. If the headline numbers change, re-render the card to keep the unfurl honest.

**Design tokens** are CSS custom properties in `:root` at [index.html:12](index.html#L12) – paper `#F2EBDD`, ink `#1A1816`, accent `#C44A36`, highlight `#F5E69A`, plus Fraunces (display) and Inter (text) from Google Fonts. Scope colours used by the chart and the matrix pills come from the same set, so the two sections stay legible against each other.

---

## Caveats

Figures are reproduced as reported by each source on the date cited. **Scopes and definitions differ materially between studies and are not directly comparable** – that incomparability is the subject of the brief, not a defect in it. Not investment advice.

---

Prepared by [Mike Blank](https://pl.linkedin.com/in/mishablank) · June 2026 · updated 13 Aug 2026. Design after trancheprotocol.com.
