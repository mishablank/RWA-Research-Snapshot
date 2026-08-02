# The State of RWAs — Where the Research Disagrees

**Everyone agrees RWAs are coming. Nobody agrees how big.**

A single-page editorial synthesis that cross-reads **61 research reports** on real-world assets and tokenization — global banks, asset managers, the Big Four, crypto-native desks and the official sector — all published between **29 Mar and 27 Jun 2026**. The finding: the desks converge almost completely on the *direction of travel* and contradict each other on nearly everything you can put a number on.

The headline tension: **$400B → $14T** for the same 2030 horizon. A 35× spread. And an even wider ~36× spread on what the market is worth *today*.

No build step, no dependencies, no framework. One file — [`index.html`](index.html).

---

## The argument in three lines

1. **The facts of today are settled.** ~0.01% penetration of a $300T+ addressable base, ~$15B of tokenized Treasuries anchoring the market, institutional issuers now leading growth. Nobody disputes this.
2. **Every forward number is contested.** 35× on 2030 size, 36× on today's size, and a straight split on whether stablecoins are the settlement rail (crypto desks) or a flawed form of money to be superseded (BIS).
3. **Most of the disagreement is definitional, not factual.** Three choices explain the bulk of it — what counts as an RWA (free-float vs. represented vs. full settlement layer), which chains you count (public-only undercounts ~10×), and whether stablecoins are in.

---

## What's on the page

| # | Section | What it does |
|---|---------|--------------|
| 01 | Hero | The $400B → $14T tension, the source base by category |
| 02 | Consensus | The five numbers every desk signs up to |
| 03 | The matrix | 18 desks × 6 questions on one grid |
| 04 | Discrepancy 01 — the 2030 number | Interactive forecast chart + study table |
| 05 | Discrepancy 02 — the denominator | Why "today's" market size ranges $19.3B → $695B |
| 06 | Discrepancy 03 — stablecoins | Rail, coexistence layer, or flawed money |
| 07 | Discrepancy 04 — the lead asset | Treasuries lead now; after that, pick a fight |
| 08 | Discrepancy 05 — whose chain | Public trackers vs. the permissioned layer nobody sees |
| 09 | Discrepancy 06 — the constraint | Six desks, six different bottlenecks |
| 10 | Takeaway | How to read any RWA report without being fooled by scope |

~12 minute read.

### The chart (section 04)

Two toggles — **2030 forecast / market today** and **linear / log** — over the same six-to-seven study dataset. The encoding is deliberate and switches with the scale:

- **Linear** → marks are **bars**. Length encodes magnitude from a real zero.
- **Log** → marks are **dots**. There is no zero on a log axis, so bar length would be meaningless; only position is read.
- **Colour** encodes the *definition* used (free-float · public-chain · securities · broad · all-in incl. stablecoins), not the desk.
- **Hollow dot** = the same desk's second sourced figure under a wider scope (21Shares $31B → $350B; Standard Chartered $4T '28 → $2.7T DeFi-active '30).
- **Band** = a published scenario range (Binance $320B–$4.8T around a $1.6T base).
- **`pt. est.`** = the source publishes a point estimate with no range.
- On linear with two figures, the solid bar stops at the **lower** number and extends in a tint — the solid block never overstates the most conservative sourced figure.

Log tick density adapts to plot width (narrow viewports drop to one tick per decade so labels don't overprint), so the chart re-renders on resize.

### The matrix (section 03)

18 desks down, six questions across, grouped by desk type. Read down a column to see whether a question is settled or split; read across a row for one desk's whole position. Empty rings are desks in the source base that took **no public position** on that question — and most cells are empty, which is itself the finding: 61 reports, few desks answering more than two of these six questions.

---

## Source base

61 reports cross-read, 29 Mar – 27 Jun 2026 (49 archived locally — **the source documents are not in this repo**; the page reproduces figures as reported, with dates).

- **Banks** — Citi · J.P. Morgan · Morgan Stanley · Standard Chartered · Deutsche Bank · HSBC · Barclays · Nomura
- **Managers & issuers** — BlackRock · Franklin Templeton · Securitize · Grayscale · 21Shares · Bitwise
- **Consultancies** — BCG · McKinsey · PwC · Oliver Wyman · Deloitte · KPMG
- **Crypto research** — Binance · Pantera · Messari · Galaxy · DefiLlama · CoinGecko · BeInCrypto · RWA.xyz · Keyrock
- **Official sector** — BIS · IMF · GFMA · OMFIF

---

## Repo layout

```
index.html       the entire site — markup, design tokens, CSS, chart data, chart engine
wrangler.jsonc   Cloudflare static-assets config (worker name: rwa-snapshot)
.gitignore       wrangler local state + env files
README.md        this file
```

## Run it locally

Any static server works — there's nothing to build.

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

Git-integration deploys from `main` work equally well — there is no build command and no output directory to configure.

Two things worth knowing before you touch that config: serving `.` publishes every file in the root, including this README and `wrangler.jsonc`; and the `nodejs_compat` flag is inert here, since there is no worker script to run.

---

## Editing the content

**Chart data lives in the inline `<script>`** — the `DS` object at [index.html:841](index.html#L841), split into `forecast` and `today` arrays. One entry per study:

```js
{n:'Citi', v:5500e9, cat:'secur', pt:1,
 scope:'Tokenized securities — equities + Treasuries led', src:'Jun 2026'}
```

- `v` — headline figure in dollars · `lo`/`hi` — published scenario band · `alt`/`altLbl` — same desk, wider scope (renders as the hollow dot)
- `cat` — the scope bucket, keyed to `CATS` at [index.html:867](index.html#L867); it drives both the colour and the legend, which is generated from whichever categories are actually present
- `pt: 1` — flags a point estimate · `scope` and `src` — the hover/tap tooltip

**The prose tables under each chart are hand-written HTML, not generated from `DS`.** Adding or revising a study means editing both, or the chart and the table beneath it will disagree — which would be an unfortunate way for this particular page to fail.

**Design tokens** are CSS custom properties in `:root` at [index.html:12](index.html#L12) — paper `#F2EBDD`, ink `#1A1816`, accent `#C44A36`, highlight `#F5E69A`, plus Fraunces (display) and Inter (text) from Google Fonts. Scope colours used by the chart and the matrix pills come from the same set, so the two sections stay legible against each other.

---

## Caveats

Figures are reproduced as reported by each source on the date cited. **Scopes and definitions differ materially between studies and are not directly comparable** — that incomparability is the subject of the brief, not a defect in it. Not investment advice.

---

Prepared by [Mike Blank](https://pl.linkedin.com/in/mishablank) · June 2026. Design after trancheprotocol.com.
