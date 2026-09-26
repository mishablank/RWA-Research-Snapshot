# Data dictionary

Generated from [`data.schema.json`](data.schema.json) and the vocabularies in [`data.json`](data.json) by `tools/render.py` – edit those, not this file.

- **Schema version:** 2.0.0 (`schema_version` in data.json; a major bump means a breaking change)
- **Currency:** USD. Nominal USD as reported by each source; no inflation or FX adjustment.
- **Dates:** ISO 8601 – `YYYY-MM-DD`, or `YYYY-MM` when the source gives only a month; `a/b` is an interval.
- **Caveat:** Figures are reproduced as reported by each source on the date cited; scopes and definitions differ materially between studies and are not directly comparable.

## Files

| File | What it is |
|---|---|
| `data.json` | Canonical dataset. Everything else is generated from it. |
| `data.schema.json` | JSON Schema (draft 2020-12) for data.json, enforced in CI. |
| `data.csv` | One row per figure – 31 rows. |
| `positions.csv` | One row per filled matrix cell (desk × question). |
| `llms.txt` | Summary for LLM crawlers. |

## How to read the figures

1. **Filter on `metric`.** Only `market_size` figures are market sizes. Revenue, fund AUM, stablecoin supply and settlement volume are different units and never belong on one axis.
2. **Check `horizon`.** Forecasts are mostly 2030, not all – compare like with like.
3. **Check `scope`.** The scope bucket, `includes_stablecoins` and `includes_permissioned` explain most of the spread between desks. Within a bucket the 2030 forecasts land ≤1.7× apart; across buckets, 35×.
4. **Filter `status = current`** for the latest view; superseded figures stay for the revision history.

## `data.json` – top level

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `$schema` | string |  | URL of this schema |
| `schema_version` | string | ✓ | Semantic version of the data shape; a major bump is a breaking change |
| `meta` | `meta` | ✓ | Page and dataset metadata |
| `scopes` | array of `vocab` | ✓ | Scope buckets – what a figure counts |
| `metrics` | array of `metric` | ✓ | Units a figure can be measured in |
| `desk_groups` | array of `group` | ✓ | Desk categories, in page order |
| `desks` | array of `desk` | ✓ | Every desk in the source base, in page order |
| `sources` | array of `source` | ✓ | Reports that figures or positions are attributed to |
| `figures` | array of `figure` | ✓ | One record per sourced number |
| `questions` | array of `question` | ✓ | The matrix columns, with each stance question's value vocabulary |
| `positions` | array of `position` | ✓ | Filled matrix cells – one desk's answer to one question |
| `views` | `views` | ✓ | Which figures the chart plots, in order |
| `tables` | `tables` | ✓ | The page's study tables, citing figures by id |
| `staircase` | `staircase` | ✓ | The definitional staircase in section 05 |
| `revisions` | array of `revision` | ✓ | Dated changes to the numbers and to the page |
| `copy` | object | ✓ | Editorial strings the generator places on the page; may use {stat:NAME} / {fig:ID} placeholders and **bold** / *em* |

### `meta`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `title` | string | ✓ | Page title |
| `site` | string | ✓ | Canonical site URL, trailing slash |
| `author` | string | ✓ | Author |
| `author_url` | string |  | Author profile link |
| `window` | object | ✓ | Publication window of the source base |
| `reports_read` | integer | ✓ | Reports cross-read in the window |
| `archived_locally` | integer | ✓ | Of those, archived in the (non-public) research corpus |
| `published` | `isodate` | ✓ | First publication of the page |
| `updated` | `isodate` | ✓ | Last content update |
| `currency` | `USD` | ✓ | Currency of every *_usd field |
| `value_basis` | string | ✓ | How values are denominated |
| `disclaimer` | string | ✓ | Comparability caveat |
| `license` | string | ✓ | Dataset licence |
| `og_card` | object |  | What the static og-card.png says – checked against the data so the unfurl stays honest |

### `vocab`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `label` | string | ✓ | Display label |
| `description` | string | ✓ | What the value means |

### `metric`

A unit of measurement. Only market_size figures are comparable market sizes.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `label` | string | ✓ | What is measured |
| `short` | string | ✓ | Suffix shown in matrix cells (empty for market_size) |
| `unit_note` | string | ✓ | Tooltip explaining why the unit differs |

### `group`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `label` | string | ✓ | Display label |

### `desk`

A research desk or publisher. A desk with no positions is listed as 'in the source base, no position'.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `name` | string | ✓ | Canonical name – the same everywhere on the page |
| `short` | string |  | Short name for tight spaces |
| `group` | `id` | ✓ | desk_groups[].id |
| `note` | string |  | Sub-label under the name in the matrix |

### `source`

A report. Every figure cites exactly one.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `desk` | `id` | ✓ | desks[].id of the desk it belongs to |
| `publisher` | string | ✓ | Publisher credit as printed (may name co-authors) |
| `title` | string | ✓ | Report title |
| `published` | `isodate` | ✓ | Publication date or interval |
| `url` | string | ✓ | Publisher page or PDF; secondary coverage for client-only notes |
| `access` | `client-only` |  | Set when the report itself is not public |

### `figure`

One sourced number with every dimension needed to compare it honestly.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `desk` | `id` | ✓ | desks[].id |
| `source` | `id` | ✓ | sources[].id |
| `label` | string |  | Display label when not just the desk name (a scenario, a sub-scope, a data partner) |
| `kind` | `today` · `forecast` | ✓ | A measurement of the market now, or a projection |
| `metric` | `id` | ✓ | metrics[].id – what the number measures |
| `value_usd` | `usd` | ✓ | Headline value |
| `low_usd` | `usd` |  | Low end of a published scenario range |
| `high_usd` | `usd` |  | High end of a published scenario range |
| `approx` | boolean | ✓ | Source states the number as approximate (~) |
| `point_estimate` | boolean or null | ✓ | true = single number, no range published; false = a range exists; null = not recorded |
| `horizon` | integer or null | ✓ | Forecast horizon year; null for today figures or when the source states none |
| `as_of` | any | ✓ | Period measured, when the source states it separately from publication |
| `published` | `isodate` | ✓ | When this figure was published – must fall inside its source's date |
| `scenario` | `base` · `bull` · `bear` · `tail` · `null` | ✓ | Scenario label where the source gives one |
| `status` | `current` · `superseded` | ✓ | superseded = the desk later replaced it |
| `superseded_by` | `id` |  | figures[].id of the replacement; required when superseded |
| `reaffirmed_in` | array of `id` |  | Later sources that restated the figure |
| `scope` | any | ✓ | scopes[].id; null when no bucket fits or the metric is not a market size |
| `includes_stablecoins` | boolean or null | ✓ | Definition counts stablecoins (null = not stated) |
| `includes_permissioned` | boolean or null | ✓ | Definition counts permissioned networks (null = not stated) |
| `asset_class` | string or null | ✓ | Asset class the figure is limited to; null = all classes in scope |
| `definition` | string | ✓ | What the source counts, in one line |

### `question`

A matrix column. figure questions cite figures; stance questions pick from values.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `id` | `id` | ✓ |  |
| `label` | string | ✓ | Column header |
| `type` | `figure` · `stance` | ✓ | How cells answer it |
| `horizon` | integer |  | Horizon a figure question asks about; off-horizon cells are marked |
| `values` | array of `vocab` |  | Allowed answers for a stance question |

### `position`

One desk's answer to one question: figures for a figure question, a value for a stance question.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `desk` | `id` | ✓ | desks[].id |
| `question` | `id` | ✓ | questions[].id |
| `value` | `id` |  | questions[].values[].id (stance questions) |
| `qualifier` | string |  | Desk-specific nuance shown after the value |
| `figures` | array of `id` |  | figures[].id (figure questions); two = a low–high pair |
| `scope` | `id` |  | Colour override when the cited figures span buckets |

### `view_item`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `figure` | `id` | ✓ | figures[].id plotted as the mark |
| `alt` | `id` |  | Same desk's second figure under a wider scope – the hollow dot |
| `alt_label` | string |  | Label for the hollow dot |
| `label` | string |  | Row label override |
| `scope` | `id` |  | Colour override |
| `tooltip` | string |  | Tooltip text; defaults to the figure definition |

### `views`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `chart_forecast` | array of `view_item` | ✓ | 2030 forecast chart rows (also the 'by scope' view) |
| `chart_today` | array of `view_item` | ✓ | Market-today chart rows |

### `tables`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `forecast` | array of object | ✓ | Section 04 table |
| `today` | array of object | ✓ | Section 05 table |
| `lead_asset` | array of object | ✓ | Section 07 table |

### `staircase`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `kicker` | string | ✓ |  |
| `intro` | string | ✓ |  |
| `fork_note` | string | ✓ |  |
| `rungs` | array of object | ✓ | Values and multiples are computed from the cited figures |

### `revision`

A dated change – to a desk's numbers or to this page.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `date` | `isodate` | ✓ |  |
| `desk` | any | ✓ | desks[].id, or null for a change to this page |
| `change` | string | ✓ | What changed |
| `note` | string | ✓ | Context |
| `sources` | array of `id` | ✓ | sources[].id |
| `figures` | array of `id` |  | figures[].id the change introduced |
| `drift` | object |  | A desk revising itself: old and new figure ids |

## Vocabularies

### Scope buckets (`scopes`)

| id | Label | Meaning |
|---|---|---|
| `narrow` | Free-float / distributed only | Only distributed / free-float tokenized assets that trade on-chain; stablecoins excluded. |
| `public` | Public chains, all issued | Every tokenized asset issued on public blockchains, distributed or not; permissioned networks excluded. |
| `secur` | Securities & core asset classes | Tokenized securities and core asset classes (equities, Treasuries, commodities, ETFs). |
| `broad` | Broad – incl. funds / 12-class core | Broad definitions that add funds or a 12-class core asset list. |
| `all` | All-in – incl. stablecoins / settlement layer | Everything on-chain including stablecoins and settlement positions. |

### Metrics (`metrics`)

| id | Meaning |
|---|---|
| `market_size` | Tokenized asset market size (a stock of value) |
| `fund_aum` | Tokenized fund AUM only |
| `revenue` | Revenue pool |
| `am_opportunity` | Opportunity for asset managers |
| `stablecoin_supply` | Stablecoin adoption / supply |
| `settlement_volume` | On-chain settlement volume (monthly flow) |

### Desk groups (`desk_groups`)

| id | Label |
|---|---|
| `banks` | Banks |
| `managers` | Managers & issuers |
| `consultancies` | Consultancies |
| `crypto` | Crypto research & trackers |
| `official` | Official sector |

### Matrix questions and position values

- **`size_2030`** – 2030 size: a cell cites one or more `figures` (horizon 2030).
- **`size_today`** – Size today: a cell cites one or more `figures`.

**`stablecoins`** – Stablecoins

| value | Label | Meaning |
|---|---|---|
| `rail` | Rail | Stablecoins are the settlement rail and on-ramp for tokenized assets |
| `coexist` | Coexist | Stablecoins, tokenized bank deposits and central-bank money coexist, each for different uses |
| `flawed_money` | Flawed money | Stablecoins fail on singleness, elasticity and integrity; the future is tokenized central-bank and commercial-bank money |

**`lead_asset`** – Lead asset by 2030

| value | Label | Meaning |
|---|---|---|
| `treasuries` | Treasuries | Tokenized Treasuries stay the anchor asset |
| `treasuries_credit` | Tsy + credit | Treasuries and private credit – the strongest near-term product-market fit |
| `equities_treasuries` | Equities + Tsy | Listed equities and Treasuries, pulled on-chain by public-market infrastructure |
| `equities_credit` | Equities / credit | Equities by addressable market, private credit by current penetration |
| `funds` | Funds | Tokenized funds |

**`rails`** – Which rails

| value | Label | Meaning |
|---|---|---|
| `public` | Public | Public blockchains |
| `permissioned` | Permissioned | Permissioned networks (Canton, Kinexys and bank ledgers) |
| `unified_ledger` | Unified ledger | A unified ledger anchored in central-bank money (Project Agorá) |

**`constraint`** – Binding constraint

| value | Label | Meaning |
|---|---|---|
| `market_infra` | Market infra | Incumbent market infrastructure embedding tokenization (DTCC, NYSE, Nasdaq) |
| `data_interop` | Data & interop rails | Oracle and interoperability infrastructure decides who wins |
| `convergence` | Convergence | No single lever – regulation, custody, settlement, liquidity and distribution must reinforce each other |
| `monetary_architecture` | Monetary arch. | A unified ledger anchored in central-bank money is the prerequisite |
| `safety_first` | Safety first | Safe settlement assets, legal certainty and international coordination first |

## `data.csv` columns

| Column | Meaning |
|---|---|
| `figure_id` | Stable id of the figure (matches `figures[].id` in data.json) |
| `desk_id` | Stable id of the publishing desk |
| `desk` | Desk name |
| `desk_group` | Banks · Managers & issuers · Consultancies · Crypto research & trackers · Official sector |
| `label` | Display label used on the page (may name a scenario or sub-scope) |
| `kind` | `today` (a measurement) or `forecast` (a projection) |
| `metric` | What is measured – see the metric vocabulary; only `market_size` rows are comparable market sizes |
| `asset_class` | Asset class the figure is limited to; empty = all classes in scope |
| `value_usd` | Headline value, nominal USD |
| `low_usd` | Low end of a published scenario range, if any |
| `high_usd` | High end of a published scenario range, if any |
| `approx` | 1 if the source states the figure as approximate (~) |
| `point_estimate` | 1 = the source gives a single number with no range; 0 = a range exists; empty = not recorded |
| `horizon_year` | Forecast horizon year; empty for `today` figures and for forecasts with no stated horizon |
| `as_of` | Period the figure measures (ISO, month precision) when the source states it separately from publication |
| `published` | Publication date of the figure (ISO 8601; YYYY-MM when only the month is known) |
| `scenario` | `base`, `bull`, `bear` or `tail` where the source labels its scenarios |
| `status` | `current`, or `superseded` when the same desk later replaced it |
| `superseded_by` | figure_id of the replacement |
| `scope_id` | Scope bucket – what the figure counts; drives the chart colour |
| `scope_label` | Scope bucket label |
| `includes_stablecoins` | 1/0 if the definition is known to include/exclude stablecoins; empty = not stated |
| `includes_permissioned` | 1/0 if the definition is known to include/exclude permissioned networks; empty = not stated |
| `definition` | What the source counts, in one line |
| `in_chart` | `forecast` or `today` if the figure is plotted in that chart view (`-alt` = the hollow dot) |
| `source_id` | Source id (matches `sources[].id`) |
| `source_title` | Source report title |
| `source_url` | Link to the report |

## `positions.csv` columns

| Column | Meaning |
|---|---|
| `desk_id` | Stable id of the desk |
| `desk` | Desk name |
| `desk_group` | Desk group |
| `question_id` | Question id (`size_2030`, `size_today`, `stablecoins`, `lead_asset`, `rails`, `constraint`) |
| `question` | Question label as shown on the page |
| `position_id` | Value id from the question's vocabulary; empty for figure questions |
| `position` | Cell text as shown on the page |
| `position_description` | Long-form meaning of the position value |
| `qualifier` | Desk-specific nuance on top of the value (e.g. `USD only`) |
| `figure_ids` | Figures behind a size cell, ` \| `-separated |
| `different_unit` | 1 if the figure is not a market size (revenue, fund AUM, opportunity…) |
| `unit_note` | What the unit is instead |
| `source_ids` | Sources for this desk, ` \| `-separated |
| `source_urls` | Their URLs, ` \| `-separated |
