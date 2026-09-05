# Markeitech V2 Options-Flow Specialist Report

- **Research date:** 2026-08-17
- **Primary evidence:** `data/OptionsFlow.csv`, a manually downloaded BlackBoxStocks options-flow export
- **Scope:** data-product audit, options-market interpretation, V2 ingestion boundary, deterministic metrics/state/events, evidence joins, delivery gates, and risk review
- **Status:** specialist recommendation; not implementation approval and not a trading model

## Executive recommendation

The CSV is a useful **vendor-curated activity feed**, not a consolidated options tape and not an
execution-quality option-chain source. Markeitech can use it to observe selected large block/sweep
activity, repeated contract/strike/expiration concentration, vendor open-interest threshold states,
and time-aligned contextual evidence. It cannot honestly determine the initiator, opening versus
closing intent, complete multi-leg strategy, full market volume, executable price, liquidity,
dealer positioning, or bullish/bearish intent from this file alone.

The measured file makes the limitation unusually clear:

- all 20,226 nonblank `Side` values are `A` or `AA`; there are no bid-side (`B`/`BB`) or
  between-market regular prints;
- every row is a vendor-classified `SWEEP` or `BLOCK`; there are no `ML/` multi-leg rows;
- BlackBox documents that its default view includes only blocks/sweeps and defaults to at-or-above
  ask activity, so the export is consistent with a default-filtered view rather than full flow
  ([BlackBox Options Flow Filters](https://docs.blackboxstocks.com/en/options-platform/options-flow-filters/));
- the file begins at 09:30 and contains no SPXW Global Trading Hours evidence;
- there is no exchange, OPRA sequence, trade identifier, condition code, bid/ask, quote timestamp,
  multiplier, deliverable, or correction reference;
- every SPXW and SPX row has `Spot = 0` and `ImpliedVolatility = 0`, preventing trustworthy
  moneyness and volatility interpretation from the export itself; and
- same-day expiration must be derived from `CreatedDate == ExpirationDate`; `Dte == 1` is not a
  0DTE test in this dataset.

The recommended product stance is therefore:

1. Preserve the original manual export as an immutable, access-controlled source artifact if and
   only if the applicable subscription and market-data terms permit retention and automated use.
2. Normalize each row without upgrading vendor classifications into exchange facts. Retain the
   vendor row and a separate Markeitech interpretation/fidelity block.
3. Publish normalized observations through a replaceable options-flow source boundary; do not
   make a manual file look live, and do not make BlackBox-specific fields part of the provider-
   neutral analytical contract.
4. Use PostgreSQL for file/batch lifecycle, quality summaries, approved rolling-state checkpoints,
   semantic events, and decision lineage—not for all 20,271 raw rows.
5. Keep gross call/put, ask/above-ask, sweep/block, late/cancel, 0DTE/non-0DTE, contract, surface,
   and cross-underlying dimensions separate. Do not publish a single “bullish flow” score.
6. Join fresh option NBBO, canonical contract definitions, chain/Greeks/OI, and the named
   underlying reference before options flow can affect expression quality or moneyness claims.
7. Do not interrupt Stage 9B final live acceptance. Implement the first isolated parser/contract
   slice only after 9B is accepted; integrate actionable flow state no earlier than the bounded
   options/richer-options stages.

## Evidence labels used in this report

| Label | Meaning |
|---|---|
| **Measured** | Reproduced directly from the supplied CSV bytes. |
| **Vendor-verified** | Described by current or linked official BlackBoxStocks materials. |
| **Market-verified** | Supported by OCC/OIC, Cboe, or OPRA primary material. |
| **Inferred** | Best interpretation of measured patterns, explicitly not source truth. |
| **Unknown** | The field or behavior is not documented sufficiently to assign semantics safely. |
| **Recommendation** | Proposed Markeitech behavior; not a claim about the file or market. |

## 1. Dataset audit

### 1.1 File integrity and parseability

| Property | Measured result |
|---|---|
| Path | `data/OptionsFlow.csv` |
| Size | 2,837,331 bytes (about 2.7 MiB) |
| SHA-256 | `bde0f66d937967386038589455a84331d098f95c13461909839b7dad15c7dd4e` |
| Filesystem creation/mtime | 2026-08-17 16:13:54 +0300; this is workstation metadata, not an export timestamp |
| Encoding | 7-bit ASCII; no BOM, NUL bytes, or non-ASCII bytes |
| Line endings | 20,272 CRLF records: one header plus 20,271 data rows |
| CSV width | Exactly 22 fields on every data row; no malformed-width records |
| Parse errors | None for the stated date, time, integer, decimal, and categorical domains |
| Git state during audit | The source CSV was untracked; it must not be committed without a separate licensing/retention decision |

The file is structurally clean. Its main risks are semantic completeness, missing metadata, sentinel
zeros, vendor-derived labels, and floating-point serialization artifacts—not broken CSV syntax.

### 1.2 Coverage, order, and apparent export filter

| Dimension | Measured result |
|---|---|
| Total rows | 20,271 |
| Displayed dates | 2026-08-13: 10,589 rows (52.237%); 2026-08-14: 9,682 rows (47.763%) |
| Displayed time coverage | 2026-08-13 09:30:00–16:17:49; 2026-08-14 09:30:00–16:14:19 |
| Rows after 16:00:00 | 47; they include regular vendor colors as well as 3 orange rows, so “after 16:00” is not itself a correction flag |
| Sort order | Strictly non-increasing by combined displayed date/time; zero forward inversions |
| Timestamp resolution | One second; 5,543 adjacent row pairs share the same displayed second |
| Timezone | Not encoded. Eastern Time is a strong inference because BlackBox documents its options flow as starting at 09:30 EDT and the dates are U.S. option sessions, but the CSV does not verify this. |
| Session coverage | Regular-hours-shaped export plus late/closing reports; no premarket or SPXW GTH rows |

The `Created*` naming should not be silently rewritten as exchange execution time. BlackBox's
operator material says the UI `TIME` is the time the trade was executed
([BlackBox orientation handout](https://blackboxstocks.com/orientation-class-handouts/)), but this
CSV omits timezone, source timestamp precision, report timestamp, and exchange sequence. The honest
normalized form is therefore `source_displayed_at_local` with `source_timezone_status = unknown`
until Markeitect captures or BlackBox confirms the export timezone. A configured
`America/New_York` interpretation may then produce a **derived** UTC timestamp with its mapping
version and DST rule; it must not overwrite the source text.

The side/type distribution is consistent with BlackBox's documented defaults: at/above-ask only,
blocks and sweeps only, ETF explicitly enabled, and multi-leg off. The file does not retain the
filter settings, so this remains an evidence-backed inference rather than proven export provenance.

### 1.3 Schema profile

The following table reports physical representation, actual missingness, distinct count, and
representative range. Literal zero and `None` values are not CSV nulls; they are discussed as
semantic sentinels.

| Column | Parsed representation | Empty | Distinct | Measured domain/range |
|---|---:|---:|---:|---|
| `CreatedDate` | date | 0 | 2 | 2026-08-13 to 2026-08-14 |
| `CreatedTime` | local time to seconds | 0 | 12,107 | 09:30:00 to 16:17:49 |
| `Symbol` | string | 0 | 919 | `TSLA` most frequent; adjusted-looking `BYND1`, `SA1` present |
| `Type` | enum-like string | 0 | 2 | `SWEEP`, `BLOCK` |
| `Volume` | integer contracts | 0 | 1,651 | 75 to 53,000 |
| `Price` | decimal text parsed as decimal/float | 0 | 5,137 | $0.01 to $860.71; 1–3 displayed decimals |
| `Side` | enum-like string | 45 | 3 including empty | `A`, `AA`, empty; no `B`, `BB`, or ordinary mid-market code |
| `CallPut` | enum | 0 | 2 | `CALL`, `PUT` |
| `Strike` | decimal | 0 | 792 | 0.50 to 37,000; mostly integer or one decimal |
| `Spot` | decimal | 0 physical / 371 zero | 15,213 | 0 to 1,868.8164; 4,704 values have more than 4 decimal places |
| `Premium` | integer dollars | 0 | 14,108 | $84 to $122,220,820 |
| `ExpirationDate` | date | 0 | 46 | 2026-08-13 to 2028-12-15 |
| `Color` | enum-like string | 0 | 5 | `WHITE`, `MAGENTA`, `YELLOW`, `ORANGE`, `#FF0000` |
| `ImpliedVolatility` | decimal fraction, inferred scale | 0 physical / 680 zero | 258 | 0 to 5.95; likely 0.41 = 41% |
| `Dte` | integer | 0 | 73 | 1 to 855; no zero |
| `ER` | boolean code | 0 | 2 | `T`, `F` |
| `StockEtf` | vendor class | 0 | 2 | `STOCK`, `ETF` |
| `Sector` | vendor category string | 0 | 12 | 11 named sectors plus literal `None` |
| `Uoa` | boolean code | 0 | 2 | `T`, `F` |
| `Weekly` | boolean code | 0 | 2 | `T`, `F`; empirical meaning differs from canonical “weekly series” |
| `MktCap` | integer-like vendor value | 0 physical / 1,035 zero | 1,165 | 0 to $5.422978 trillion |
| `OI` | integer contracts | 0 physical / 153 zero | 5,156 | 0 to 598,129 |

### 1.4 Missingness and sentinel values

Only `Side` has actual empty cells. Zero is nevertheless an important missing/unsupported sentinel:

| Condition | Rows | Share | Consequence |
|---|---:|---:|---|
| Blank `Side` | 45 | 0.222% | 41 orange late/out-of-sequence rows and 4 of 5 red-hex cancellation rows; side cannot be used |
| `Spot == 0` | 371 | 1.830% | Moneyness and underlying-at-print unavailable; includes all 288 SPXW and all 38 SPX rows |
| `ImpliedVolatility == 0` | 680 | 3.355% | Treat as unavailable unless zero IV is independently valid; includes all SPXW and SPX rows |
| `MktCap == 0` | 1,035 | 5.106% | Vendor filter/reference unavailable or inapplicable; includes index roots and many ETFs |
| `OI == 0` | 153 | 0.755% | Ratio undefined/ambiguous; may be genuinely zero, stale, new series, or unavailable |

`Sector == "None"` occurs 3,404 times and is a literal category, not a null. It is expected for
most ETF/index-class rows but also appears on 93 vendor-`STOCK` rows. `StockEtf` must not become
Markeitech canonical asset class: SPX, SPXW, XSP, NDX, and VIX are labeled `ETF`, while NDXP is
labeled `STOCK`. Resolve canonical product identity from approved instrument definitions.

`Spot` contains ordinary binary floating-point artifacts such as
`401.23900000000003` and `98.21000000000001`. Parse price-like fields as decimal values and retain
the original source string. Do not hash platform-native binary floats as canonical identity.

### 1.5 Representative distributions

#### Categorical

| Dimension | Count and share |
|---|---|
| Type | `SWEEP` 11,763 (58.029%); `BLOCK` 8,508 (41.971%) |
| Side | `A` 16,874 (83.242%); `AA` 3,352 (16.536%); blank 45 (0.222%) |
| Right | calls 13,365 (65.932%); puts 6,906 (34.068%) |
| Color | white 9,190 (45.336%); magenta 7,294 (35.982%); yellow 3,741 (18.455%); orange 41 (0.202%); `#FF0000` 5 (0.025%) |
| Vendor security class | stock 16,933 (83.533%); ETF 3,338 (16.467%) |
| `ER` | true 485 (2.393%) |
| `Uoa` | true 239 (1.179%) |
| `Weekly` | true 8,358 (41.231%) |

Calls being 65.9% of this file is not evidence of bullishness: regular rows are ask-side only,
puts bought at the ask may be bearish or protective, calls may close shorts or belong to spreads,
and the export excludes an unknown amount of market activity.

#### Numeric

| Metric | p1 | p5 | p25 | median | p75 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Contracts (`Volume`) | 80 | 100 | 150 | 210 | 428 | 1,299.5 | 3,734.4 | 53,000 |
| Option price | $0.10 | $0.28 | $0.92 | $1.964 | $5.20 | $26.50 | $80.21 | $860.71 |
| Premium | $3,867 | $10,856 | $20,928 | $46,946 | $140,000 | $841,763 | $2,604,920 | $122,220,820 |
| IV fraction | 0 | 0.06 | 0.26 | 0.41 | 0.69 | 1.10 | 1.61 | 5.95 |
| DTE | 1 | 1 | 1 | 7 | 35 | 155 | 525 | 855 |
| OI | 2 | 41 | 645 | 2,746 | 9,355 | 40,280.5 | 65,376 | 598,129 |

The observed minimum `Volume` of 75 is consistent with a curated feed, not proof of one universal
75-contract threshold. BlackBox says rows must meet minimum contract-size **or** notional criteria,
but does not document the active thresholds in the export
([BlackBox Flow Tab](https://intercom.help/blackboxstocks/en/articles/4296095-flow-tab)).

### 1.6 Symbols, expirations, and the target universe

There are 919 displayed symbols; 314 appear once. The twelve largest row counts are TSLA 3,178,
QQQ 1,234, NVDA 1,210, MU 909, SPY 742, SPCX 606, AAPL 571, AMD 417, INTC 396,
SMCI 330, SNDK 299, and SPXW 288. This broad cross-section can provide context, but its unknown
filter/threshold selection prevents comparisons from being interpreted as market-wide participation.

| Symbol | Rows | Share | Sweeps / blocks | Calls / puts | Zero spot | Zero IV | Total displayed contracts | Total vendor premium |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SPX | 38 | 0.187% | 0 / 38 | 31 / 7 | 38 | 38 | 32,882 | $348,571,385 |
| SPXW | 288 | 1.421% | 6 / 282 | 164 / 124 | 288 | 288 | 72,007 | $119,404,866 |
| SPY | 742 | 3.660% | 533 / 209 | 276 / 466 | 0 | 6 | 542,635 | $157,477,115 |
| QQQ | 1,234 | 6.088% | 885 / 349 | 266 / 968 | 0 | 7 | 476,555 | $263,256,173 |

SPX and SPXW are not interchangeable roots. Cboe identifies SPX as the standard AM-settled root and
SPXW as the PM-settled weekly/end-of-month root; both are cash-settled, European-style index
options, while SPY is physically settled and American-style
([Cboe SPX Weeklys specifications](https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/)).
Canonical identity and session/settlement rules must remain product-specific.

### 1.7 0DTE audit

The exact same-day-expiration cohort contains 4,889 rows (24.118%). Every one has `Dte = 1` and
`Weekly = T`, but `Dte = 1` contains 3,469 additional rows traded on 2026-08-13 for 2026-08-14
expiration. Across all 20,271 rows, the measured relationship is:

```text
Dte = max(1, ExpirationDate - CreatedDate in calendar days)
Weekly = T if and only if Dte = 1
```

That is an empirical invariant of this file, not verified BlackBox schema documentation. It means:

- `Dte` is floored at one and cannot identify same-day expiry;
- `Weekly` behaves like a current-week/near-expiry flag in this sample, not a canonical indication
  that the OCC series is a weekly contract; and
- Markeitech must calculate `calendar_dte`, `trading_dte`, and `is_same_trade_date_expiry`
  separately from authoritative calendar/contract data.

Target 0DTE rows:

| Trade date | SPXW | SPY | QQQ |
|---|---:|---:|---:|
| 2026-08-13 | 168 | 203 | 694 |
| 2026-08-14 | 41 | 21 | 18 |
| Total | 209 | 224 | 712 |

The aggregate same-day target cohort is 1,145 rows. It is heavily put-shaped for SPY (199 puts of
224) and QQQ (687 of 712), while SPXW has 119 puts and 90 calls. This is a descriptive property of
the filtered export, not “bearish smart money.” No SPX row is same-day expiration in the file.

### 1.8 Duplicate, ordering, and revision findings

- There are **zero byte/value-identical data rows** across all 22 columns.
- There are 77 groups where two rows share displayed second, symbol, expiry, right, and strike.
  These may be distinct fills, sweep fragments, separate parent orders, or strategy legs.
- One pair also shares second, contract, price, and volume (MSTR 2026-08-21 97.5C, 150 at 2.05)
  but differs in `Type`, `Spot`, and IV. It is not safe to collapse.
- `OI` and `MktCap` are invariant for a symbol/contract within a displayed date, but 873 contract
  groups and 855 contract groups respectively change across the two dates. This is consistent with
  daily snapshots rather than per-print live values.
- All yellow rows have row `Volume >= OI` (3,734 greater, 7 equal), every magenta row has row
  `Volume < OI`, and every white row has row `Volume <= OI`. That matches BlackBox's documented
  color intent.
- For 4,535 magenta rows, even cumulative **visible exported** volume for the contract up to that
  second does not exceed OI. BlackBox must be using activity outside the visible export subset,
  another aggregation, or proprietary ordering. Markeitech cannot reconstruct the color algorithm
  from this file.

Cross-file deduplication is therefore fundamentally uncertain without a vendor trade ID. File hash
idempotency is exact; print identity across overlapping exports is not.

### 1.9 Premium consistency

For standard 100-multiplier contracts, vendor premium is strongly consistent with
`Volume × Price × 100`:

- 12,177 rows match exactly;
- 18,914 (93.3%) are within $10;
- 95% are within $13;
- 95% relative error is at most 0.0407%; and
- the largest absolute difference is $511, while the largest relative difference is 4.55% on a
  small notional.

The likely cause is that `Price` is a rounded aggregate/sweep price while `Premium` was calculated
from more precise fills. This is inference, not documentation. OCC states that standard equity
options generally cover 100 shares and premium points represent $100, but corporate actions can
produce adjusted deliverables
([OCC equity option specifications](https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications)).
Index option premiums are also generally quoted with a $100 multiplier
([OIC equity versus index options](https://www.optionseducation.org/advancedconcepts/equity-vs-index-options)).
Because adjusted-looking roots (`BYND1`, `SA1`) occur and the file omits multiplier/deliverable,
Markeitech must retain `Premium` as the vendor-reported value and must not blindly recompute it.

## 2. Field-by-field data dictionary

| Field | Human meaning | Semantic status | Normalization rule and caveat |
|---|---|---|---|
| `CreatedDate` | Vendor date attached to the displayed flow row | **Inferred** as execution/trade date | Retain source text/date. Do not equate to exchange trade date until timezone/session is known. |
| `CreatedTime` | Vendor displayed row time to one second | **Vendor-verified** UI meaning is execution time; CSV timezone/precision **unknown** | Store local wall time plus `timezone_status`; derive UTC only under versioned mapping. |
| `Symbol` | Vendor underlying/root symbol | **Vendor-verified** | Preserve exactly; resolve separately to canonical underlying and option root. Numeric suffix may indicate adjusted/non-standard option. |
| `Type` | BlackBox `SWEEP` or `BLOCK` classification | **Vendor-verified** | Preserve as `vendor_flow_type`. Do not claim exchange order type. BlackBox describes block as one-exchange large trade and sweep as broken across exchanges. |
| `Volume` | Contracts represented by the vendor row | **Vendor-verified** | Integer, positive. May aggregate several sweep fills; it is not full session contract volume. |
| `Price` | Option execution/aggregate price per premium unit | **Vendor-verified** at UI level | Decimal, not binary float. Not an executable current price and may be rounded. |
| `Side` | `A`/`AA` ask-side vendor classification; blank for most late/cancel rows | Collective ask-side meaning **vendor-verified**; exact A=at ask and AA=above ask **inferred from official filter labels** | Store vendor code and normalized `quote_location = at_or_above_ask`; do not call proven aggressor/buyer. |
| `CallPut` | Option right | **Vendor-verified** | Canonical enum call/put. Right is not direction. |
| `Strike` | Contract strike | **Vendor-verified** | Decimal. Needs canonical contract definition and adjustment/deliverable validation. |
| `Spot` | Underlying price when flow was displayed/executed | **Vendor-verified** UI meaning; source/timestamp **unknown** | Zero becomes unavailable. Preserve precision/source text. Do not substitute a proxy under the same name. |
| `Premium` | Vendor total trade value | **Vendor-verified** | Integer dollars. Preserve as reported; do not infer cash at risk, buyer/seller, or standard multiplier. |
| `ExpirationDate` | Contract expiration date | **Vendor-verified** | Resolve with exchange product calendar; do not infer last trade/settlement from date alone. |
| `Color` | Vendor state relative to OI, or late/cancel status | **Vendor-verified** for white/magenta/yellow/orange/red; `#FF0000`→red **inferred** from literal hex | Normalize to separate `vendor_oi_state` and `vendor_report_status`; never make color a direction. |
| `ImpliedVolatility` | Vendor IV at the row time | UI meaning **vendor-verified**; decimal scale **inferred** | Treat 0 as unavailable by default. Source/model/quote input absent; never join as if chain IV. |
| `Dte` | Vendor days-to-expiry-like value | **Unknown schema**, empirical formula measured | Store source value. Independently derive calendar/trading DTE; exact 0DTE uses dates, not this field. |
| `ER` | Earnings-report-day flag | **Inferred**, supported by BlackBox filter description | Boolean vendor feature. Criteria/timezone/corporate calendar are unknown. Inapplicable to indices/ETFs. |
| `StockEtf` | BlackBox stock-versus-ETF filter class | **Vendor-verified as filter**, semantically **partial** | Never use as canonical asset class; index roots are inconsistently bucketed. |
| `Sector` | Vendor sector category | **Vendor-verified as filter**, taxonomy version **unknown** | `None` is a value. Record taxonomy/source version if later used. |
| `Uoa` | BlackBox unusual-options-activity flag | **Vendor-verified as proprietary criterion**, formula **unknown** | Preserve boolean only. Never reproduce/name a threshold not documented. |
| `Weekly` | Vendor near/current-week flag in this sample | **Unknown** | Empirically identical to `Dte == 1`; do not treat as OCC weekly-series identity. |
| `MktCap` | Vendor market-cap/filter value | **Inferred** | Daily/static vendor reference; semantics for ETFs and zero are unclear. Context only, not a live valuation input. |
| `OI` | Daily vendor open-interest snapshot for the option series | **Vendor-/market-verified concept**, exact as-of **unknown** | Store integer plus unknown as-of. Zero makes ratios unavailable. Join independently timestamped chain/OCC OI when conclusions depend on it. |

BlackBox's official material says white means OI not exceeded, magenta/purple means cumulative
multiple trades have exceeded OI, yellow means one trade has met/exceeded OI, red is a canceled
previous report, and orange is late/out of sequence
([BlackBox Options Guide](https://blackboxstocks.com/help/optionskey.pdf)). The file uses `MAGENTA`
where some documents say purple and `#FF0000` where the UI documentation says red. Preserve both
source vocabulary and normalized meaning.

## 3. What this feed can and cannot tell Markeitech

| Question | What the CSV supports | Fidelity | What remains impossible or unsafe |
|---|---|---|---|
| Did BlackBox report selected large activity? | Yes: row time, partial contract, size, price, premium, vendor type/color | Reported vendor observation | Whether every market print was captured or what exact filter admitted it |
| Was activity at/above the ask? | Vendor says A/AA are ask-side classes | Reported vendor class; market interpretation inferred | Validity/age/source of NBBO; actual initiating participant; current executable ask |
| Was it a sweep or block? | Vendor classification | Reported vendor class | Parent order, venues, component fills, true order instructions, independent reconstruction |
| Was it bullish or bearish? | A call/put and ask-side heuristic can be described | Inferred hypothesis only | Position intent, hedge, covered write, spread, opening/closing, dealer/customer side |
| Did one row exceed OI? | Yellow rows and direct `Volume/OI` comparison | Reported/derived | New opening interest; next-day OI change; full volume; both parties' open/close status |
| Did cumulative visible flow exceed OI? | Sum of exported rows can be computed | Derived but selection-biased | Reproducing vendor magenta logic or full market volume |
| Is the contract 0DTE? | Yes from source dates | Derived with calendar caveat | Exact time to last trade/settlement without product/session definition |
| Was it ITM/ATM/OTM? | For nonzero spot, approximate source-row moneyness | Derived/partial | SPX/SPXW moneyness here; adjusted-contract moneyness; trustworthy proxy/reference source |
| Was it liquid/executable? | No | Unavailable | Fresh NBBO, sizes, spread, quote stability, depth, slippage, last eligibility |
| What were IV and Greeks? | Vendor IV for some rows | Reported but model/source unknown | Delta/gamma/theta/vega; chain-relative IV/skew; all SPXW IV from this file |
| Was it multi-leg? | No ML rows are present; likely filter excluded them | Partial absence evidence | Whether a displayed block/sweep was related to stock or other option legs |
| Was it opening or closing? | No | Unavailable | Buy-to-open/close or sell-to-open/close; `Volume > OI` does not solve it |
| Was it canceled/corrected? | Red-hex and orange vendor statuses exist | Reported vendor status | Which original row was canceled/corrected; corrected price/size; complete correction chain |
| Can it drive a live alert? | Only if arrival age and export cadence are captured and inside an approved freshness policy | Currently unavailable | The supplied manual artifact arrived days after row event time and has no capture timestamp inside the file |

## 4. Options-flow concepts and the honest interpretation

### 4.1 Quote location is not proven aggressor side

BlackBox describes A/AA as ask-side “buying” activity. The conservative market interpretation is:
the reported price was classified by the vendor at or above its ask reference, so the option buyer
likely demanded liquidity. This is not proof of customer direction because the file omits the quote,
quote timestamp, quote venue/NBBO status, trade venue, locked/crossed state, condition, and parent
order. A complex order may price each leg away from the displayed simple-market quote; a quote can
move before a second-resolution timestamp; price improvement can occur; and every transaction has
both a buyer and seller.

Name the field `vendor_quote_location`, not `aggressor_side`. A later
`inferred_option_liquidity_taker_side` may be calculated only from trade and timestamp-aligned NBBO
under a versioned classifier, with coverage and ambiguity rates. In this file the absence of every
bid-side class also means no net bid-versus-ask statistic is valid.

### 4.2 Sweeps and blocks

BlackBox defines blocks as large trades executed at one exchange and sweeps as large trades broken
across exchanges; it also says sweeps may indicate urgency
([BlackBox Flow Tab](https://intercom.help/blackboxstocks/en/articles/4296095-flow-tab)). Markeitech
may report “BlackBox classified this row as SWEEP.” It must not report “a trader urgently bought X”
as observed fact. The export has no component executions, exchange list, interval, parent ID, or
condition data with which to verify reconstruction.

Do not assign a static sweep multiplier in a universal score. Preserve sweep and block activity as
separate features; any later relative predictive weight must be learned/evaluated for a named
instrument, session, horizon, and outcome.

### 4.3 Multi-leg and spread ambiguity

BlackBox documents that multi-leg rows appear with `ML/` in `TYPE` when enabled and that the default
view contains blocks and sweeps only. This file has no `ML/` rows. The likely export filter therefore
removed explicitly recognized multi-leg activity. That does **not** prove each remaining row is an
outright option bet: a leg can be reported separately, linked to stock, routed as a contingent or
complex strategy, or fail the vendor's multi-leg association. Do not infer strategy from nearby
same-second rows without a strategy/parent identifier.

### 4.4 Opening versus closing

The CSV has no open/close field. OIC explains that OI changes only after opening and closing sides
are paired and processed; both sides opening increases OI, both closing decreases it, and one open
plus one close leaves it unchanged
([OIC Open Interest](https://www.optionseducation.org/news/open-interest-why-it-matters)). Therefore:

- option purchase does not imply opening a long;
- option sale does not imply opening a short;
- row volume greater than prior OI shows activity larger than the prior outstanding count but does
  not establish how next-day OI will change; and
- a next-day OI increase is useful validation but still aggregates the full series, not one row.

“Potentially opening” is the strongest acceptable phrase for vendor yellow/magenta, and only if the
vendor color and its limitations are cited.

### 4.5 Premium

`Premium` is gross contract notional exchanged, not profit at risk, conviction, new capital, or
directional exposure. A $1 million debit and credit leg may be one spread; a deep-ITM option can have
large premium with limited incremental optionality; and the seller receives what the buyer pays.
Premium intensity is still useful for measuring selected activity, provided it remains separated by
right, vendor side, type, expiry, strike, and correction status.

### 4.6 Volume versus open interest

Row `Volume` is vendor-row contracts. `OI` is a daily series snapshot. OIC warns that volume and OI
do not themselves guarantee liquidity; a fresh two-sided market and displayed size answer the
execution question more directly
([OIC General Information](https://www.optionseducation.org/referencelibrary/faq/general-information)).

Use names such as `visible_selected_flow_contracts_to_oi`, never `new_position_ratio`. Denominator
timestamp and zero handling are mandatory. Vendor white/magenta/yellow are categorical source
features; they should not be recomputed from the selected export as if the export were complete.

### 4.7 Repeated prints

Repeated rows at a contract can be informative as an activity cluster, but they can also be sweep
fragments, separate customers, a roll/spread, negotiated blocks, duplicate vendor reports, late
reports, or corrections. A cluster is a derived entity whose inputs remain individually cited. It
must not be called “one trader,” even though BlackBox's educational shorthand describes yellow as
one trade, without a stable parent/order identity.

### 4.8 Late, canceled, and corrected reports

BlackBox says orange is late/out of sequence and red is a previously reported cancellation. The
sample has 41 orange rows and 5 red-hex rows. Cboe exchange protocols carry explicit execution and
reference identifiers for trade cancels/corrections and can correct price or size
([Cboe U.S. Options BOE specification](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-titanium-u.s.-options-boe-specification)).
The CSV does not carry those links.

Recommended policy:

- retain all orange/red source observations immutably;
- exclude orange from real-time urgency/order claims by default, but allow it to revise historical
  bounded state with `late_evidence = true`;
- emit a cancellation/correction fact without subtracting a prior row unless a deterministic unique
  match exists;
- if zero or several candidates match, set `correction_link_state = unresolved`, degrade only the
  affected contract/window, and keep unrelated flow state healthy; and
- never delete the original from audit history.

### 4.9 0DTE, DTE, and moneyness

0DTE is contract/session-specific. For this file, same displayed date is the only usable first test;
the authoritative runtime must use the option's exchange trade date, expiration, last eligible trade
time, and settlement style. SPXW can trade in GTH, RTH, and Curb while its trade-date/session mapping
must follow the Stage 9A calendar. Cboe lists SPXW GTH as 20:15–09:25 Eastern and documents SPXW as
PM-settled/cash-settled/European-style
([Cboe SPX Weeklys specifications](https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/)).

Moneyness requires a named reference:

```text
log_moneyness = ln(underlying_reference / strike)
right_signed_moneyness = +log_moneyness for calls, -log_moneyness for puts
```

Positive right-signed moneyness means intrinsic value under that reference. The output must cite
whether the reference is reported SPX, live SPY/QQQ, an ES-derived projected SPX, or unavailable.
All SPXW rows in the sample have zero spot; no moneyness should be manufactured from the file.

### 4.10 Underlying liquidity versus contract liquidity

A liquid SPY/QQQ underlying does not guarantee a tight far-OTM or near-expiry option market. High
option OI or flow volume also does not establish current fillability. Contract selection needs fresh
bid, ask, sizes, spread, quote stability, expected slippage, last eligible trade time, and contract
definition. Flow may support a thesis or highlight a contract; it may not declare that contract
tradeable.

### 4.11 Why raw bullish/bearish labels mislead

The familiar mapping—ask call bullish, bid put bullish, bid call bearish, ask put bearish—is a
heuristic about the option trade, not the holder's portfolio or underlying forecast. Calls can be
sold/closed/covered/hedged; puts can be protection against a long book; both can be spread legs.
BlackBox itself warns that alerts are not buy signals
([BlackBox Options Data Key](https://intercom.help/blackboxstocks/en/articles/4295971-options-data-key)).

Markeitech should expose at least these separate dimensions:

- option right;
- vendor quote location;
- inferred liquidity-taker side and ambiguity;
- flow type;
- gross contracts and premium;
- possible underlying-direction proxy, explicitly inferred;
- volatility-direction exposure if Greeks are joined;
- opening/closing state, usually unavailable;
- multi-leg state, absent/unknown/reported; and
- observed underlying response after the event.

## 5. V2 ingestion architecture

### 5.1 Ownership and provider replacement

```text
Manual BlackBox export now / licensed provider later
    -> OptionsFlowSourceAdapter (source-specific parsing and capability declaration)
    -> immutable SourceArtifact + SourceRowObservation
    -> OptionsFlowNormalizer (provider-neutral types; no semantic upgrading)
    -> Nautilus custom-data batch publication
    -> OptionsFlowStateActor (bounded deterministic metrics/entities)
    -> OptionsFlowEventDetector (quiet transition events)
    -> Options Intelligence / cross-instrument consumers
    -> compact agent read model

Operational lifecycle/quality/events -> OperationalPersistenceActor -> PostgreSQL
Original permitted artifact + optional normalized columnar data -> access-controlled object/file store
Raw per-row observations -> not PostgreSQL
```

Recommended narrow ownership:

- `OptionsFlowSourceAdapter`: file discovery/claim, byte hash, schema check, raw parsing, source
  capability metadata, and batch terminal outcome. A future licensed stream implements the same
  boundary.
- `OptionsFlowNormalizer`: decimals, booleans, source timestamp status, partial contract key,
  vendor classifications, lineage, and quality flags. It owns no rolling market meaning.
- `OptionsFlowStateActor`: bounded contract/underlying/surface/session projections and health.
- `OptionsFlowEventDetector`: state transitions, hysteresis, deduplication, expiry, and evidence
  rules.
- existing `Options Intelligence Owner`: joins live contract definitions, chain/NBBO/Greeks, and
  evaluates expression quality. Flow does not take over candidate discovery.
- existing `DataAcquisitionActor`: continues to own active provider demand. A manual drop is passive
  source arrival; any later API subscription/request is reconciled through acquisition/policy.

The adapter should declare capabilities, not just a source name: coverage (`filtered`), sides
(`ask_and_above_only`), corrections (`status_without_reference`), quote context (`absent`),
multi-leg (`excluded_or_unknown`), timestamp precision (`1s`), timezone (`unknown`), and arrival
mode (`manual_batch`). Consumers can then fail closed on missing capability.

Use Nautilus custom data for immutable normalized observation batches and named low-volume signal
channels for source lifecycle, readiness, health, entities, and semantic events. Do not publish one
semantic event per CSV row, create a second raw-data fan-out wrapper, or make synchronous file I/O a
Nautilus callback responsibility.

### 5.2 Immutable source artifact versus normalized observation

`SourceArtifact` records facts about the bytes: source/vendor, original filename, byte length,
SHA-256, schema fingerprint, received/captured time, declared export scope/filter profile, row
count, displayed bounds, operator/source account alias, terms version, and retention class.

`SourceRowObservation` preserves:

- artifact ID and physical row number;
- exact original field strings;
- parsed values and parse issues;
- vendor classifications without reinterpretation;
- source-local timestamp and timezone status;
- partial contract identity;
- semantic sentinel flags; and
- source-row content fingerprint.

`NormalizedOptionsFlowObservation` adds provider-neutral types and **derived** fields such as exact
same-day expiry, tentative canonical contract linkage, normalized vendor report state, and evidence
fidelity. It never overwrites source values. A later resolution/interpretation is a new revision
that cites the same immutable source row.

### 5.3 Deterministic identity, deduplication, and idempotency

Use three identities because one hash cannot honestly solve three different problems:

1. `source_artifact_id = sha256(original_bytes)`. Reimporting the identical file is an exact no-op
   with an audited duplicate outcome.
2. `source_row_id = sha256(source_artifact_id || physical_record_number || canonical_raw_fields)`.
   This is exact within one artifact and preserves truly identical repeated rows if they ever occur.
3. `print_equivalence_fingerprint = sha256(source_schema_version || source_local_timestamp_text ||
   vendor_symbol || expiry || right || normalized_strike || type || volume || normalized_price ||
   premium || side || color)`. This is a **candidate equivalence key**, never proven trade identity.

For overlapping exports, treat each file as a snapshot/multiset of vendor rows. Under a declared
same-scope profile, reconcile identical fingerprints by maximum observed multiplicity rather than
blindly summing both files, while retaining both artifact lineages. If scope/filter profiles differ,
do not deduplicate across them. A later snapshot can supersede an analytical projection but never
erase the earlier artifact. Any cross-file link has `identity_confidence = inferred` until a vendor
trade ID exists.

Do not use displayed second + contract + price + volume as a unique key: the sample already contains
a collision across different vendor types.

### 5.4 Contract identity

The file can only form a partial key:

```text
(vendor root, expiration date, call/put, decimal strike)
```

Canonical identity requires option root/OSI symbol, underlying, venue/class, multiplier, deliverable,
exercise/settlement style, currency, last eligible trade time, and adjustment status. Cboe's
consolidated options reference offering explicitly includes OSI symbol, root, expiration, strike,
right, exercise style, multiplier, deliverable, currency, OI, and underlying information
([Cboe Options Lite](https://www.cboe.com/data/market-data-services/cboe-options-lite/)); those
fields illustrate what this CSV lacks.

Never silently merge SPX with SPXW or a digit-suffixed adjusted root with the standard root. An
unresolved partial key remains usable for source-level aggregation but not contract-quality,
Greeks, settlement, or payoff claims.

### 5.5 Raw retention and format

The project charter does not select general raw market-data persistence or replay. This commercial
manual export is different from reconstructable IB ticks: the exact filter result and vendor labels
may not be reproducible later, and correction/color interpretation needs original bytes. Retention
is justified for source audit and deterministic reprocessing—not for speculative backtesting.

Subject to written terms approval:

- retain the original CSV bytes unchanged, optionally compressed losslessly as `.csv.gz`, in a
  content-addressed, non-Git, access-controlled location;
- store a small immutable JSON manifest beside it with hash, bytes, capture/export time, timezone,
  source version, filter profile, row/schema/coverage stats, importer version, and terms/retention
  class;
- optionally write a normalized Parquet derivative only after the first repeated analytical need
  proves its value. Partition by source and source trade date, use decimal types, and keep artifact/
  row IDs. This is a selected data-product store, not V2's general raw market warehouse;
- encrypt at rest where practical, restrict human/model access, and define a configurable minimum
  retention/expiry policy; and
- never put the raw export, screenshots, or vendor rows in Git, PostgreSQL JSONB, Discord, or an
  external LLM prompt by default.

If terms do not permit durable storage or machine analysis, retain only the allowed operational
manifest/approved aggregates and make raw-artifact-dependent reprocessing explicitly unavailable.

### 5.6 PostgreSQL policy

Persist operational/semantic audit through the existing sole writer:

- file arrival, accepted/rejected/duplicate/superseded/quarantined state;
- artifact hash, bytes, schema fingerprint, declared filter profile, row count, source bounds,
  storage reference, retention class, and terms-policy version;
- parse/normalization counts, sentinel/null counts, unknown enums, unresolved contracts, late/
  cancel counts, latency, and terminal reason;
- bounded batch publication lifecycle and consumer readiness;
- approved contract/underlying/cohort state checkpoints or session summaries;
- semantic event and entity lifecycle, correction uncertainty, configuration/algorithm versions;
  and
- exact evidence references used by any opportunity/agent decision.

Do not persist every source row. PostgreSQL is not the raw feed store or live bus. If an approved
semantic event needs row evidence, store artifact/row IDs and a bounded typed evidence excerpt, not
the entire vendor record set.

### 5.7 Late, out-of-order, replacement, and corrected files

- Parse in file order for provenance; calculate in event-time order with a stable tie break of
  source artifact and row number.
- Never assume arrival order equals market order. A manual artifact is stale for live action unless
  `received_at - derived_event_at` passes an explicit source freshness policy.
- Maintain an event-time watermark per source/scope/trade date. Data behind it may revise bounded
  historical state but cannot retroactively emit a “live urgency” event.
- A later overlapping export is a new artifact/revision. Compare multiset fingerprints, capture
  additions/removals/status changes, and publish a bounded revision summary.
- Orange rows remain late evidence. Red-hex rows create cancellation observations. Link only when a
  unique configured matcher succeeds; otherwise publish `correction_unresolved` and degrade the
  affected contract/window.
- Corrections must not regress current state from a newer event-time revision. Preserve both
  revisions and the supersession link.
- One malformed row, contract-resolution failure, or correction ambiguity quarantines/degrades that
  row/subject. It must not stop unrelated artifacts, underlyings, historical Stage 9B work, or the
  live Nautilus data plane.

### 5.8 Example normalized record

JSON-like example derived from the first QQQ row; IDs/hashes are illustrative:

```json
{
  "contract_name": "options_flow.observation",
  "schema_version": 1,
  "observation_id": "sha256:source-artifact+row-2+raw-fields",
  "source": {
    "provider": "blackboxstocks",
    "adapter": "manual_csv",
    "artifact_id": "sha256:bde0f66d...",
    "source_row_number": 2,
    "filter_profile_id": null,
    "coverage": "filtered_unknown",
    "arrival_mode": "manual_batch"
  },
  "timing": {
    "source_date": "2026-08-14",
    "source_time": "16:14:19",
    "source_timezone": null,
    "source_timezone_status": "unknown",
    "event_at_utc": null,
    "received_at_utc": "<captured by importer>",
    "precision": "1s",
    "session_id": null
  },
  "contract": {
    "vendor_symbol": "QQQ",
    "canonical_instrument_id": null,
    "identity_state": "partial",
    "expiration_date": "2026-08-17",
    "right": "CALL",
    "strike": "735",
    "multiplier": null,
    "deliverable": null
  },
  "reported": {
    "vendor_flow_type": "BLOCK",
    "contracts": 1571,
    "price": "0.75",
    "premium_usd": 117825,
    "vendor_side_code": "A",
    "vendor_color": "MAGENTA",
    "vendor_spot": "730.86",
    "vendor_iv": "0.08",
    "vendor_dte": 3,
    "vendor_oi": 3798,
    "vendor_uoa": false,
    "vendor_weekly": false
  },
  "derived": {
    "is_same_trade_date_expiry": false,
    "calendar_dte": 3,
    "vendor_quote_location": "at_or_above_ask",
    "vendor_report_status": "regular",
    "vendor_oi_state": "cumulative_visible_or_hidden_activity_exceeded_oi",
    "reconstructed_standard_premium_usd": 117825,
    "right_signed_log_moneyness_using_vendor_spot": -0.005647
  },
  "evidence": {
    "source_fidelity": "reported_vendor",
    "market_side_fidelity": "inferred_partial",
    "contract_identity_fidelity": "partial",
    "quote_context": "unavailable",
    "opening_closing": "unavailable",
    "multi_leg": "unknown",
    "correction_state": "not_indicated",
    "limitations": [
      "unknown export filter profile",
      "timezone absent",
      "no NBBO or exchange",
      "no vendor trade id"
    ]
  }
}
```

The moneyness field is derived from a vendor spot and is not an option-chain fact. It must be null
for SPXW rows in this sample and may be superseded by a time-aligned canonical underlying reference.

## 6. Baseline entities and rolling state

### 6.1 Entity model

| Entity | Stable identity | State/revision | Expiry/invalidation |
|---|---|---|---|
| Source artifact | source + byte SHA-256 | ingest/quality/terms profile | retention expiry; never mutate bytes |
| Flow observation | artifact + row identity | parse and canonical-resolution revisions | cancellation can invalidate interpretation, not erase source |
| Contract flow cluster | definition/config version + partial/canonical contract + cluster anchor | gross count/contracts/premium by type/side/status; evidence IDs | inactivity gap, session end, correction, identity resolution |
| Strike-expiry surface cell | underlying + trade date/session + expiry + strike + right | activity/concentration/OI state | session rollover or contract correction |
| Underlying flow session | underlying + authoritative session ID + source scope | gross call/put/type/cohort/TOD projections | session close/finalization |
| 0DTE cohort | underlying/product + exchange trade date + expiration + session phase | remaining time, activity, surface, health | last eligible trade/expiry/session invalidation |
| Cross-underlying episode | named structural group + horizon + definition/config version + anchor | aligned standardized flow/price evidence | decay, freshness loss, relationship reversal |
| Flow evidence health | source + scope + subject + capability version | fresh/degraded/stale/unavailable/unsupported | transition-only, independent per subject |

Opportunity identity remains target-exposure/episode based. A QQQ flow cluster may support a QQQ
continuation hypothesis, an S&P catch-up hypothesis, both, or neither. It does not own an
opportunity, and no permanent SPXW/SPY/QQQ preference follows from row count.

### 6.2 Bounded state views

Maintain separate views at:

- contract: root/expiry/right/strike and canonical contract when resolved;
- strike-expiry surface: call and put sides never silently netted;
- underlying: gross selected activity by source side/type/cohort;
- expiration and DTE cohort: exact 0DTE plus configurable calendar/trading-DTE bands;
- session phase/time-of-day: authoritative exchange minute since phase open, not workstation hour;
- 0DTE cohort: time remaining, underlying reference, chain/quote join health;
- cross-underlying group: SPX/SPXW/SPY/ES and QQQ/NQ initially as configured structural groups;
  and
- evidence health: source coverage, arrival age, filter profile, timestamp, contract resolution,
  quote/chain join, correction, and baseline readiness.

Cardinality is resource policy, not market truth. Configure maximum active contracts/surface cells,
evict only by documented least-recently-active rules after session/expiry constraints, emit
eviction counts, and retain enough aggregate totals that eviction cannot silently change the
denominator. Choose initial caps from a measured load test rather than this two-day sample.

## 7. Concrete baseline metrics

### 7.1 Parameter policy

These are provisional engineering defaults for evaluation, not trading folklore. Every parameter
must carry stable ID, type/unit, scope, bounds, mutability, source, version/effective time, and
rollback. Startup-static is safest initially. “Optimization-eligible” means only after Stage 9K has
a named leakage-safe target and sufficient regimes; an agent never edits the values directly.

| Parameter family | Suggested first value | Authorized design envelope | First mutability / future status |
|---|---|---|---|
| Rolling windows | 30s, 2m, 5m, 15m, session-to-date | 5s to one authoritative session; max 8 concurrent windows | startup-static; optimization-eligible per instrument/session |
| Cluster inactivity gap | 120s | 5s–15m | startup-static; optimization-eligible by source/underlying |
| Time-of-day bucket | 5 exchange minutes | 1–30m | between-session; optimization-eligible |
| Baseline history | 20 comparable completed sessions, minimum 10 | 5–120 sessions | between-session; optimization-eligible |
| Robust anomaly entry/exit | enter at robust z 3.0, exit at 2.0 | entry 1.5–8.0; exit 0.5–entry; mandatory hysteresis | startup-static; experimental, not trade threshold |
| State transition dwell | 2 consecutive evaluations | 1–10 evaluations or equivalent duration | startup-static; optimization-eligible |
| DTE bands | 0; 1–2; 3–7; 8–30; 31–90; 91+ calendar days | monotone 0–1,095 days; max 12 bands | between-session; configuration-owned |
| Join tolerance | 1s initial for quote/trade source with matching clocks; unavailable otherwise | 0–10s and must not exceed evidence freshness | source-specific; calibration required |
| Cross-market lag search | 0–300s, reported as hypothesis | 0–30m, max lag count/resource bounded | research-only until out-of-sample validation |

If fewer baseline sessions exist, publish raw gross metrics and `baseline_state = insufficient`; do
not manufacture a z-score. Robust z uses `(x - median) / (1.4826 × MAD)` with a configured fallback
when MAD is zero. Baselines must match source filter profile, session phase, time-of-day bucket,
underlying, and cohort; otherwise the comparison is invalid.

### 7.2 Metric catalog

| Metric | Decision question | Formula/inputs and windows | Fidelity/health gate | Limitation and event use |
|---|---|---|---|---|
| `selected_flow_gross` | How much vendor-selected activity is visible? | Per subject/window: row count, `ΣVolume`, `ΣPremium`, separated by right, A/AA, block/sweep, regular/late/cancel, expiry cohort | Source artifact accepted; filter profile attached; cancellations excluded from active total but retained separately | Not full market flow. Foundation for clusters and rate changes. |
| `selected_flow_rate` | Is activity arriving faster than its comparable baseline? | gross count/contracts/premium divided by elapsed active session time; normalize against same TOD/source/cohort median/MAD | Minimum comparable sessions; session alignment healthy | Manual file cannot be a live rate unless arrival is timely. May support intensity transition. |
| `contract_repeat_intensity` | Is one contract repeatedly selected? | Count distinct source rows, median interarrival, cluster duration, contracts/premium, A vs AA share within cluster gap | One-second collisions retained; source row identity valid | Does not mean one trader/order. Supports cluster entity. |
| `visible_flow_to_oi` | How large is selected row/window volume relative to daily OI? | `Σ eligible selected Volume / OI_asof`, plus row `Volume/OI`; null when OI≤0/unknown | OI as-of and contract match recorded | Not opening interest or liquidity. Event name must include `visible_selected`. |
| `vendor_oi_threshold_state` | What did the vendor classify relative to OI? | Counts/last state of white/magenta/yellow, never recomputed | Vendor color known, regular status | Proprietary/hidden population. Supports observed vendor threshold transition only. |
| `gross_right_activity` | Are calls or puts dominating the selected ask-side lens? | Parallel call and put contracts/premium/rates; optional ratio `put/(call+put)` with zero guard; no automatic sign | Filter profile confirms available sides | Descriptive, not bullish/bearish. Can update plural evidence graph. |
| `above_ask_share` | What portion has the stronger vendor quote-location code? | `AA / (A + AA)` by count/contracts/premium | A/AA mapping version and nonblank side | No NBBO; not a price-impact fact. Keep separate from sweep. |
| `strike_expiry_concentration` | Is selected activity concentrated on a surface region? | Cell premium/volume; HHI `Σ(cell_value/total)^2`; top-1/top-k share; strike-distance bands | Canonical/partial key status; total not evicted; moneyness optional | HHI is concentration, not direction/pin. Supports surface concentration transition. |
| `moneyness_at_flow` | Where was the contract relative to a named reference? | `ln(S/K)`, right-signed variant, absolute strike distance, volatility-scaled distance when valid | Nonzero fresh named reference, canonical strike/adjustment, time alignment | SPXW unavailable in sample. No stale cash SPX substitution. |
| `exact_0dte_flow_state` | What selected activity belongs to the expiring trade-date cohort? | Exact exchange trade date equals expiration; gross metrics, surface, remaining phase fraction | Calendar/product identity; last eligible trade; source event mapping | `Dte=1` forbidden as classifier. Supports 0DTE cohort state. |
| `execution_price_path` | Did reported option execution prices change across repeated rows? | Last/median/VWAP-like `ΣPrice×Volume/ΣVolume`, changes by contract/cluster | Same contract identity; correction state clean | Not mark-to-market or executable performance; underlying/IV/time all confound. |
| `underlying_at_flow_response` | Did the named underlying respond after activity? | Join underlying mid/last at event; forward log return and favorable/adverse excursion at configured horizons | Underlying feed fresh; clocks aligned; enough post-event data; no future data in live trigger | Outcome/follow-through evidence, not evidence available at initial event. |
| `flow_response_efficiency` | Was underlying response large relative to selected activity? | response divided by robust standardized activity; calculate call/put hypotheses separately | Both inputs healthy; sign proxy explicitly inferred | Never label causation. Supports confirm/diverge event after horizon. |
| `chain_quote_location` | Where did trade price occur versus actual option NBBO? | `(trade-mid)/(ask-bid)/2`, clipped only for display; quote age, spread, sizes | Timestamped NBBO, uncrossed/two-sided, source sync | This is the proper later classifier; current CSV alone unavailable. |
| `greek_equivalent_activity` | What directional/volatility sensitivity did selected size represent? | delta shares `Σcontracts×multiplier×delta`; gamma/vega/theta units reported separately; sign only under explicit side hypothesis | Canonical multiplier and timestamped Greeks; side/multi-leg confidence | Not dealer GEX or portfolio exposure. Never sum correlated legs blindly. |
| `cross_underlying_standardized_flow` | Is selected activity unusually different across configured structural peers? | Compare TOD/cohort/source-profile standardized gross metrics; alignment/difference by horizon | Same coverage/filter profile or explicit compatibility transform; freshness-aligned | SPXW/SPY/QQQ row totals are not directly comparable otherwise. Supports disagreement hypothesis. |

### 7.3 Confidence and evidence health

Do not hide these dimensions in one weighted number:

- source coverage: complete, declared-filtered, filtered-unknown, or unavailable;
- source arrival: fresh, delayed-manual, stale, or unknown;
- timestamp: timezone/precision/session alignment and clock quality;
- contract identity: canonical, partial, ambiguous, adjusted-unresolved;
- side: vendor quote location, independently inferred side, ambiguous/unavailable;
- quote context: fresh NBBO, stale, missing, crossed/one-sided;
- underlying reference: reported, derived proxy, stale, missing;
- OI: as-of known, daily-unknown, zero/unknown;
- multi-leg/open-close: reported, inferred, unknown;
- correction: clean, late, canceled-linked, canceled-unresolved, revised;
- baseline readiness: ready, insufficient sessions, incompatible filter profile; and
- publication freshness: usable for live decision, historical context only, or expired.

A conclusion may carry a separate bounded `confidence` only after deterministic gates. Confidence
must cite the dimensions and cannot upgrade an inferred side to observed. A missing option chain
degrades expression conclusions without stopping underlying-flow or unrelated market evidence.

## 8. Semantic event candidates

Events publish meaningful transitions, not every row or metric update. Per-row normalized
observations remain on the data path; only bounded state changes enter semantic channels/PostgreSQL.

| Event | Layer | Trigger and identity | Agent may infer | Agent must not infer |
|---|---|---|---|---|
| `options_flow.source.ingested` | operational observation | New artifact hash accepted with terminal quality summary | New historical/context evidence exists | Market urgency or direction |
| `options_flow.evidence.degraded` / `recovered` | observation | Health dimension crosses configured state with hysteresis | Named conclusions should narrow/re-enable | Entire runtime is unhealthy |
| `options_flow.correction.unresolved` | observation | Red/correction cannot link uniquely or removes active evidence | Affected contract/window is uncertain | Which exact trade was canceled |
| `options_flow.contract_cluster.started` | interpretation | First qualifying repeated-contract cluster after inactive state; identity binds definition/config/contract/anchor | Selected activity is concentrated/repeating | One trader, opening order, bullish/bearish intent |
| `options_flow.contract_cluster.strengthened` | interpretation | Material robust-rate/concentration band transition after dwell | Cluster gained gross significance | Predictive follow-through or tradeability |
| `options_flow.contract_cluster.ended` | interpretation | Inactivity/expiry/session/correction ends entity | Cluster no longer current | Thesis invalidated unless thesis explicitly depended on it |
| `options_flow.vendor_oi_threshold.observed` | observation | Yellow or first magenta vendor state for contract/session | Vendor's OI-relative flag occurred | New OI/opening transaction certainty |
| `options_flow.surface.concentration.changed` | interpretation | HHI/top-share crosses versioned state with hysteresis | Activity moved toward/from named strikes/expiry | Pin, support/resistance, dealer gamma |
| `options_flow.0dte_cohort.intensity.changed` | interpretation | Exact-0DTE standardized gross activity enters/exits band | 0DTE selected activity changed | Direction or preferred expression product |
| `options_flow.underlying_response.confirmed` | composite | After configured horizon, named underlying response aligns with an explicit right/side hypothesis and evidence remains healthy | The hypothesis received follow-through evidence | Flow caused the move |
| `options_flow.underlying_response.diverged` | composite | Response is materially opposite/absent under the same rules | The hypothesis weakened/contradicted | Flow was “trapped” without stronger position evidence |
| `options_flow.cross_underlying.disagreement` | composite | Compatible standardized flow/price states diverge materially for dwell period | A relationship hypothesis merits attention | Permanent lead/lag or preferred SPXW/SPY/QQQ vehicle |

Every event identity binds schema, definition, algorithm, configuration hash, source/filter profile,
subject, session, horizon, and episode anchor. Every event carries effective/observed/received/
published time, evidence IDs, fidelity, causation/correlation IDs, expiry/invalidation, and separate
severity/confidence/urgency/relevance/novelty. Late evidence can revise state with a new revision; it
cannot backdate a live notification as if received on time.

### 8.1 Example semantic event

```json
{
  "event_id": "sha256:def+config+QQQ-contract+cluster-anchor+revision",
  "event_type": "options_flow.contract_cluster.started",
  "event_family": "options_flow",
  "event_layer": "INTERPRETATION",
  "schema_version": 1,
  "producer": "OptionsFlowEventDetector",
  "producer_version": "1.0.0",
  "definition_id": "contract_repeat_cluster.v1",
  "configuration_version": "oflow-bootstrap-v1",
  "effective_at": "2026-08-13T14:34:17Z",
  "observed_at": "2026-08-13T14:34:17Z",
  "received_at": "2026-08-17T<import-time>Z",
  "published_at": "2026-08-17T<import-time>Z",
  "session": {
    "calendar_id": "us_equities",
    "trade_date": "2026-08-13",
    "phase": "RTH",
    "mapping_fidelity": "inferred_from_configured_America/New_York"
  },
  "subject": {
    "kind": "partial_option_contract",
    "underlying": "QQQ",
    "expiry": "2027-09-17",
    "right": "CALL",
    "strike": "880"
  },
  "horizon": "2m",
  "direction": "NONE",
  "severity": 0.72,
  "confidence": 0.46,
  "urgency": 0.0,
  "validity_state": "HISTORICAL_CONTEXT_ONLY",
  "expires_at": "2026-08-13T14:36:17Z",
  "evidence_group_id": "sha256:artifact+row-set+metric-snapshots",
  "evidence": [
    {"observation_id": "...", "fidelity": "reported_vendor"},
    {"metric_id": "selected_flow_gross:...", "fidelity": "derived_partial"}
  ],
  "payload": {
    "rows": 11,
    "contracts": 10043,
    "premium_usd": 32615342,
    "vendor_sides": {"A": 10043},
    "coverage": "filtered_unknown",
    "opening_closing": "unavailable",
    "multi_leg": "unknown",
    "tradeability": "unavailable",
    "reason_codes": [
      "repeat_contract_inside_configured_gap",
      "manual_file_received_after_event",
      "no_nbbo",
      "no_vendor_trade_id"
    ]
  }
}
```

The illustrative numeric score is decomposed output, not a recommended fixed formula. A production
event should publish the actual metric values/bands and versioned computation that produced each
dimension. Because this artifact arrived after the event, urgency is zero and validity is historical
context only.

## 9. Joining options flow with other evidence

### 9.1 Required joins

| Evidence | Required fields | Enables | Still does not prove |
|---|---|---|---|
| Canonical option definition | OSI/instrument ID, root, underlying, expiry, strike, right, multiplier, deliverable, venue/class, settlement/exercise, last trade | Identity, correct premium units, expiry/session, adjusted contracts | Intent |
| Option NBBO/quotes | bid/ask/sizes, exchange/OPRA timestamps, source, quote age, crossed/one-sided state | Quote-location classifier, spread, executable ask, fillability | Opening/closing or portfolio context |
| Option trades/conditions | trade ID/sequence, exchange, price/size, conditions, cancel/correct refs, complex linkage if available | Real dedup, consolidated coverage, corrections, sweep reconstruction | Customer identity or complete strategy unless supplied |
| Chain snapshot | volume/OI with as-of, IV, delta/gamma/theta/vega, neighboring strikes/expiries | Skew/term, Greek-normalized activity, chain-relative concentration | Dealer inventory/GEX without position/sign assumptions |
| Underlying at print | timestamped bid/ask/trade/index value and source | moneyness, strike distance, immediate response | Causation |
| Underlying bars/trades | aligned windows, volume where meaningful, session | follow-through/divergence, regime/location context | True order flow from bars |
| Cross instruments | ES/NQ/SPX/SPY/QQQ/VIX aligned evidence and session/basis | contextual alignment, disagreement, lead/lag hypotheses | Permanent causal relationship |
| Next-day OI | same canonical series and OCC/provider as-of | Series-level OI validation | Attribution of OI change to one flow row |

Cboe's official Option Trades product illustrates the missing trade context: exchange of execution,
NBBO at trade time, underlying stock/ETF bid-ask, condition mappings, and optional IV/Greeks
([Cboe Option Trades](https://datashop.cboe.com/option-trades)). Markeitech need not buy that
specific product, but equivalent fields are the minimum for stronger conclusions.

### 9.2 SPX/SPXW

- Preserve SPX and SPXW roots and settlement/session identities.
- The sample's SPX/SPXW spot and IV are unavailable. Join reported SPX with age during its valid
  reporting phase.
- Outside cash hours, any ES-derived projected SPX is separately named, time-aligned, basis-
  versioned, and inferred. It may guide a bounded strike window but cannot become `reported_spx`.
- The manual file has no GTH coverage, so it cannot validate GTH flow behavior or support a GTH live
  event. A future source must declare session coverage explicitly.
- SPX block dominance (282 of 288 SPXW rows are blocks; all 38 SPX rows are blocks) may reflect
  product mechanics, vendor classification, or export filter. Do not compare it mechanically with
  SPY/QQQ sweep rates.

### 9.3 SPY and QQQ

- Their nonzero vendor spot allows a partial moneyness calculation, but chain/NBBO remains required
  for execution and Greek context.
- ETF options differ from SPXW in settlement/exercise, premium scale relative to exposure, expiry
  listings, quote behavior, and underlying tradability. Normalize exposure and liquidity before
  comparing expression candidates.
- Large same-day ask-put activity can represent protection, outright downside, spread legs, or
  closing. It may become contextual evidence only after underlying response, chain, and market
  structure are considered.

### 9.4 Cross-underlying and lead/lag use

Compare SPXW, SPY, and QQQ only after standardizing within each source/product/session/TOD/cohort.
Use structural groups, not all-pairs folklore:

```text
S&P exposure: SPX/SPXW + SPY + ES
Nasdaq exposure: QQQ + NQ
volatility context: VIX with its own reporting-session limitations
```

A lead/lag statement requires freshness-aligned event time, repeated support across episodes,
out-of-sample evaluation, a bounded lag/horizon, and decay. At most, this two-day file can suggest
hypotheses. It cannot establish that QQQ flow leads SPXW, that SPY is the better vehicle, or that one
instrument permanently confirms another.

### 9.5 Conclusions impossible without richer evidence

Do not produce these outputs from the CSV alone:

- current executable or affordable contract;
- option liquidity, spread, slippage, or fill probability;
- buyer/seller certainty or customer/dealer side;
- buy-to-open, sell-to-open, buy-to-close, or sell-to-close;
- complete multi-leg/stock-option strategy;
- complete consolidated volume or market share;
- dealer gamma exposure, gamma wall, vanna/charm positioning, max pain, or pin certainty;
- risk-reversal/skew/term-structure conclusions;
- delta/vega/gamma-equivalent notional;
- SPXW moneyness from this sample;
- causal price impact;
- a bullish/bearish signal or trade recommendation; or
- live evidence from a manually downloaded file whose arrival age is outside policy.

## 10. Conservative coding sequence and stage gates

### Gate 0 — protect current Stage 9B

Finish the implemented Stage 9B provider-backed live acceptance first. This research adds no 9B
request type, provider lane, PostgreSQL schema, actor, runtime dependency, or acceptance step. The
flow sample is not historical-bar warmup and must not be routed through the Stage 9B bar contract.

### Gate 1 — authority and provenance decision

Before code that retains or analyzes repeated exports:

- confirm subscription/export rights, internal non-display use, machine processing, derivative
  analytics, retention, external model processing, and operator sharing;
- capture one canonical unfiltered/controlled export with exact UI filter settings and timezone;
- ask BlackBox support for current CSV schema, row limits, field meanings, timestamp, OI as-of,
  color/correction semantics, export completeness, and stable trade IDs/API options; and
- approve the source capability profile and retention policy.

**Exit:** Markeitect can say what may be stored/processed and exactly what one file represents.

### Gate 2 — isolated offline source contract

After 9B acceptance, implement a pure parser/profiler and immutable contract fixtures against this
exact artifact. No live actor, database write, provider connection, option conclusion, or alert.

**Acceptance tests:**

- exact 20,271 rows, 22 columns, byte hash, CRLF/ASCII behavior;
- strict decimals/booleans/dates and preservation of raw strings;
- unknown-column/enum, reordered-column, missing-column, malformed-row, BOM/encoding failure;
- sentinel-zero and literal-`None` treatment;
- measured `Dte`/`Weekly`, premium reconciliation, target counts, red/orange normalization;
- artifact and row IDs stable across runs/platforms;
- identical file is idempotent; exact duplicate rows within a synthetic file remain distinct;
- overlapping snapshot multiset reconciliation and differing-filter refusal;
- no source row written to PostgreSQL; and
- no UTC timestamp invented when timezone is absent.

**Exit:** one deterministic source artifact becomes a truthful normalized batch offline.

### Gate 3 — bounded Nautilus publication and operational audit

Add passive batch arrival and immutable custom-data publication through a bounded worker/queue.
Operational persistence records artifact/batch/quality lifecycle only. Consumers register
independently; failures are isolated; shutdown reports pending work.

**Acceptance tests:** queue saturation, parser quarantine, duplicate artifact, out-of-order rows,
late replacement, cancellation ambiguity, consumer failure, persistence degradation, restart, and
bounded shutdown while unrelated native quote/bar and Stage 9B work continue.

**Exit:** normalized observations transit V2 without raw PostgreSQL storage or startup ordering.

### Gate 4 — Stage 9F/9H analytical integration

The Stage 9F option-chain/quote proof remains the priority for truthful expression quality. Add the
flow source as contextual state only after canonical contract/quote joins exist. Baseline
contract/surface/0DTE metrics may begin in 9F if they directly validate the bounded option product;
flow/underlying response and cross-instrument hypotheses belong naturally in 9H after Stage 9G
relationship state.

**Acceptance tests:** canonical SPX/SPXW/SPY/QQQ resolution, exact 0DTE mapping, session/GTH handling,
quote/chain join success and refusal paths, SPX proxy labels, stale manual-file rejection, rolling
window/hysteresis determinism, correction revisions, bounded cardinality, and independent reference
reconciliation.

**Exit:** a flow event is quiet, evidence-linked, non-directional by default, and unable to make a
bad/unquoted contract tradeable.

### Gate 5 — agent exposure no earlier than Stage 9I/J

Expose only compact state/events and health. The read model includes source coverage/filter profile,
arrival age, missing bid-side/multi-leg/NBBO evidence, conflicting underlying response, and event
expiry. The agent can maintain several opportunities and request bounded chain/quote evidence; it
cannot query raw CSV rows, change thresholds, or declare an expression from flow alone.

**Exit:** proposals cite deterministic evidence and can surface one, several, or no opportunities.

### Observability

At minimum expose bounded lifetime and per-artifact counters:

- files seen/accepted/duplicate/quarantined/superseded/expired;
- bytes/rows parsed, rejected, normalized, published, and consumer-accepted;
- schema versions/fingerprints and unknown/missing fields;
- source coverage/filter/timezone state;
- min/max displayed and received times; arrival-age distribution;
- blank/sentinel counts, unresolved/adjusted contracts, invalid expiries;
- regular/orange/red and resolved/unresolved corrections;
- queue depth/high-water/rejection, batch latency, consumer failure;
- state subjects/evictions, baseline-ready counts, event counts/suppression/revisions;
- PostgreSQL accepted/rejected/pending/failure without raw-row counts masquerading as writes; and
- per-evidence-section health for flow, chain, option quote, underlying, and cross-instrument joins.

Diagnostic logs may sample bounded rows by source-row ID but must not leak the commercial dataset.

### Explicit non-goals

- no Stage 9B changes or live IB run;
- no full OPRA reconstruction from BlackBox rows;
- no full-chain subscription caused by a flow row;
- no raw per-row PostgreSQL table;
- no replay/backtest platform;
- no global bullish/bearish flow score;
- no static preferred expression instrument;
- no hard-coded “large premium,” sweep weight, magic cluster threshold, or causal lead/lag;
- no dealer-position/GEX/max-pain claim;
- no automated execution; and
- no external LLM access to raw licensed rows without explicit rights and data-policy approval.

## 11. Capture-now checklist

These facts cannot be reconstructed reliably after the export or market session.

### Priority 0 — capture with every file

- [ ] Original bytes, original filename, SHA-256, byte length, row count, and schema fingerprint.
- [ ] Exact export/download timestamp in UTC and local IANA timezone; workstation clock health.
- [ ] Source UI timezone and confirmation of whether `CreatedTime` is execution, report, or display
      time; source precision.
- [ ] BlackBox account/subscription alias, application/export version, terms version, and approved
      use/retention policy—without storing credentials.
- [ ] Exact tab and every filter: date range, puts/calls, A/AA/B/BB/mid, blocks/sweeps, multi-leg,
      premium, price, contracts, expiry, weekly, UOA, ER, security class, sector, watchlist,
      moneyness, ex-dividend handling, and any default left active.
- [ ] Screenshot or machine-readable filter manifest, including whether all rows or a UI-limited
      subset were downloaded and any documented minimum criteria/row cap.
- [ ] Authoritative exchange trade date/session phase mapping and any GTH/RTH/Curb scope.
- [ ] Raw orange/red rows and, if available, original/corrected trade identifiers and reason.
- [ ] Vendor schema/data dictionary and support response version.

### Priority 1 — capture at or near each print where the source can provide it

- [ ] OSI/canonical contract ID, option root, exchange/class, multiplier, deliverable, adjustment,
      settlement/exercise style, and last eligible trade time.
- [ ] OPRA/vendor trade ID, sequence, exchange of execution, condition codes, report time, original
      event time, and cancel/correct reference.
- [ ] Option NBBO and sizes with quote timestamp/source/age; simple versus complex market context.
- [ ] Underlying bid/ask/trade/index reference at print with its timestamp/source and named proxy if
      derived.
- [ ] IV and Greeks with calculation/source timestamp and the underlying/interest/dividend inputs
      where available.
- [ ] OI value, source, and exact as-of; capture next-session OI for series-level validation.
- [ ] Full/selected volume coverage statement and whether sweep volume is one aggregate or component
      prints.
- [ ] Multi-leg/stock-leg/parent strategy identifiers when available.

### Priority 2 — synchronized contextual evidence

- [ ] SPX, ES, SPY, NQ, QQQ, and VIX observations aligned under their own session/health contracts.
- [ ] Chain snapshot around relevant strikes/expiries, not only the printed contract.
- [ ] Underlying trades/quotes/bars for configured pre/post-flow response horizons.
- [ ] Corporate-action/OCC adjustment memo for digit-suffixed/non-standard roots.
- [ ] Provider/entitlement incidents, known drops, latency, and file-generation delays.

## 12. Data, privacy, licensing, and terms risk

This is a risk checklist, not a legal conclusion.

The current BlackBox website advertises downloadable and historical data, but the linked terms PDF
also limits website/content use and contains personal/non-commercial, copying/storage, and
third-party-content language subject to subscription-specific terms
([BlackBox Terms and Conditions](https://blackboxstocks.com/wp-content/uploads/2023/03/BlackBoxStocksTermsandConditions-1.pdf)).
The document linked today may not be the exact click-through agreement accepted for Markeitect's
current plan, and upstream exchange/OPRA rights may be separate.

Before production use, obtain qualified review or written vendor confirmation for:

- local storage and retention of manually downloaded full-day/historical CSVs;
- automated parsing, non-display analytical use, model training/evaluation, and generation of
  derived metrics/events;
- use inside an advisory agent, especially if an external model provider processes data;
- internal sharing across users/devices, Discord projection, screenshots, or client-facing output;
- redistribution of raw fields versus sufficiently transformed derived data;
- professional versus non-professional subscriber classification and fees;
- use after subscription termination and deletion obligations;
- provider attribution, audit, security, and usage reporting; and
- whether a supported API/data license is required instead of repeated manual export automation.

OPRA defines machine processing for investment analysis/trading and other functions as potential
non-display use and distinguishes internal from external distribution
([OPRA Description of Use](https://cdn.opraplan.com/documents/OPRA_Exhibit_A.pdf)). Whether those
terms attach through BlackBox and whether a derived-data exception applies are contractual
questions to verify, not assumptions for this report.

The CSV contains no obvious personal identifiers, account positions, orders, or credentials. It is
nevertheless commercially sensitive licensed data. Risks include source account identity in
filenames/metadata, proprietary vendor filters, accidental Git commits, verbose logs, PostgreSQL
row dumps, backups beyond retention, and raw rows sent to third-party models. Apply least privilege,
encryption/access logging where appropriate, secret-free manifests, bounded/redacted logs, explicit
retention deletion, and derived-only agent context by default.

## 13. Open questions with recommended answers

| Question for Markeitect/vendor | Recommended working decision |
|---|---|
| Was the file exported with default A/AA-only, blocks/sweeps-only filters? | Treat coverage as `filtered_unknown` now. Capture a filter manifest on the next export; do not use net flow before both sides are present. |
| What timezone do `CreatedDate/Time` use? | Preserve unknown; ask BlackBox/capture UI setting. Allow a configured Eastern interpretation only as derived lineage. |
| What exactly do `Dte` and `Weekly` mean? | Ignore them for canonical expiry logic. Derive 0DTE and DTE from exchange calendar/contract. |
| Is `OI` prior close, market open, or refreshed? | Treat as daily snapshot with unknown as-of; join authoritative OI for material conclusions. |
| Are `Premium`, `Price`, and `Volume` sweep aggregates? | Preserve all three as vendor values; do not derive component fills or VWAP without documentation. |
| Why are SPX/SPXW spot and IV zero? | Treat as unsupported/unavailable, not true zero. Use Stage 9A/9F named reference and chain sources. |
| Does orange represent the late trade itself or replacement? Does red link to a prior row? | Preserve status; do not subtract until unique source reference exists. Ask for IDs/correction schema. |
| Can BlackBox provide stable trade/contract IDs, filters, timezone, NBBO, venue/conditions, and API access? | Request a supported licensed feed/interface before considering flow a live dependency. |
| Should the broad 919-symbol universe be ingested? | Retain source rows if permitted, but activate rolling live state first for configured structural/target groups; expand by policy and resource budget, not a permanent whitelist. |
| Should manual flow be mandatory for advice? | No. It is optional contextual evidence and degrades independently. Chain/quote/underlying evidence remains sufficient for other opportunity paths. |
| Should raw artifacts use Parquet? | Original CSV is authoritative. Add normalized Parquet only after legal approval and a repeated query/reprocessing need; do not select a general market-data lake. |
| Can thresholds optimize dynamically? | Start typed/startup-static. Mark eligible analytical thresholds for later between-session or policy-controlled optimization only after Stage 9K evaluation. Evidence invariants are never tunable. |

## Recommended first implementation slice

After Stage 9B final live acceptance and licensing/provenance Gate 1, build one **offline,
provider-specific source artifact and normalization slice**:

1. strict `SourceArtifact`, `SourceRowObservation`, and `NormalizedOptionsFlowObservation` contracts;
2. a pure BlackBox manual-CSV adapter that reproduces this audit exactly;
3. decimal/raw-string preservation, partial contract identity, unknown timezone, sentinel and
   correction states, exact-date 0DTE, and evidence-fidelity fields;
4. deterministic artifact/row/equivalence identities and same-file idempotency;
5. a bounded quality summary and JSON-like fixture output only; and
6. tests for schema drift, overlap, duplicate ambiguity, red/orange handling, and the measured
   20,271-row reference results.

Do **not** add a live actor, PostgreSQL raw-row table, agent tool, directional score, chain
subscription, Discord message, or Stage 9B dependency in this slice. The next reviewed slice may
publish immutable batches through Nautilus and audit lifecycle after the contract is accepted.

## Decisions required from Markeitect

1. Confirm whether the BlackBox subscription/market-data terms permit internal machine analysis,
   original-file retention, normalized derivatives, agent use, and derived-event projection.
2. Approve original CSV retention outside Git/PostgreSQL, its access controls, and retention period;
   or require aggregate-only handling.
3. Capture/confirm the BlackBox export timezone and full filter profile on the next download.
4. Decide whether to ask BlackBox for supported API/licensed data access and the missing schema/
   identity/correction fields.
5. Approve the source as optional contextual evidence, never a mandatory live-agent dependency.
6. Approve the proposed stage placement: offline contract after 9B; bounded flow integration at
   9F/9H without displacing the option-chain/quote proof.
7. Approve the provisional configurable window/baseline envelopes for later empirical calibration,
   or nominate different first evaluation horizons.

## Risks/blockers

- **Licensing/terms blocker:** automated analysis, retention, derived use, non-display use, and model
  processing rights are not established by the sample.
- **Provenance blocker:** export filters, timezone, download timestamp, schema version, and row-
  completeness/threshold profile were not captured.
- **Live-utility blocker:** the source is a manual delayed file and therefore historical context,
  not actionable live evidence, until a licensed timely arrival mechanism exists.
- **Coverage blocker:** regular rows are ask/above-ask only, block/sweep only, apparently without
  multi-leg, and no GTH data; net flow and complete-volume claims are invalid.
- **Identity blocker:** no trade/sequence/correction reference or full canonical contract identity;
  cross-file exact dedup and correction linkage are impossible.
- **Execution blocker:** no NBBO, sizes, spread, quote age, or option chain; the feed cannot establish
  tradeability or affordability.
- **SPXW blocker:** all sample SPXW spot and IV values are zero; moneyness/volatility must come from
  separate named evidence.
- **Intent blocker:** no opening/closing, customer/dealer, portfolio, or complete strategy state;
  bullish/bearish conclusions remain hypotheses.
- **Validation blocker:** two sessions and one unknown filter profile are insufficient for baseline,
  regime, lead/lag, predictive, or optimization claims.
- **Stage risk:** implementing flow before Stage 9B acceptance or ahead of the Stage 9F chain/quote
  proof would derail the accepted sequence and give a filtered context feed too much authority.

## Traceability: files and sources consulted

### Markeitech files

- `markeitech.md` — current charter, evidence/configuration/persistence invariants.
- `docs/README.md` — documentation authority order.
- `docs/current-status.md` — current implemented runtime surface, inactive/replacement work, and
  validation debt.
- `docs/product/sir-loke-v1.md` — current first-version product, trade-expression, broker-observation,
  evidence, and advisory boundaries.
- `docs/roadmap/v2-market-events-live-agent-plan.md` — product topology, plural opportunity model,
  bounded options evidence, persistence, event, trade, and Sir Loke delivery gates.
- `docs/market-intelligence-request-catalog.md` — complete request/metric/entity/event vocabulary.
- `docs/architecture/v2-historical-dependency-execution.md` — Stage 9B transient history,
  deduplication, readiness, and PostgreSQL boundary.
- `docs/architecture/v2-session-evidence-health.md` — session truth, evidence-health semantics, and
  failure isolation.
- `docs/research/market-analysis-specialist-brief.md` — required metric/event rigor and trading-
  domain boundaries.
- `docs/research/semantic-events-ai-options-baseline.md` — informative event envelope, options-flow
  ambiguity, persistence, and agent baseline.
- `data/OptionsFlow.csv` — sole measured market-data artifact; 20,271 rows; SHA-256 above.

### External primary/official sources

- [BlackBox Options Flow Filters](https://docs.blackboxstocks.com/en/options-platform/options-flow-filters/) — default ask-side and block/sweep filters, multi-leg `ML/`, premium/security/expiry/UOA filters.
- [BlackBox orientation handout](https://blackboxstocks.com/orientation-class-handouts/) — field and
  color explanations, A/AA ask-side description.
- [BlackBox Options Guide](https://blackboxstocks.com/help/optionskey.pdf) — flow thresholds,
  colors, cancellations, late/out-of-sequence reports, download behavior.
- [BlackBox Flow Tab](https://intercom.help/blackboxstocks/en/articles/4296095-flow-tab) — minimum
  admission criteria and block/sweep description.
- [BlackBox Options Data Key](https://intercom.help/blackboxstocks/en/articles/4295971-options-data-key) — warnings, OI/volume context, and filter/download behavior.
- [BlackBox Terms and Conditions](https://blackboxstocks.com/wp-content/uploads/2023/03/BlackBoxStocksTermsandConditions-1.pdf) — use/storage/content restrictions requiring current subscription-specific verification.
- [OIC Open Interest: Why It Matters](https://www.optionseducation.org/news/open-interest-why-it-matters) — volume versus OI and opening/closing combinations.
- [OIC General Information](https://www.optionseducation.org/referencelibrary/faq/general-information) — OI timing and why volume/OI do not guarantee liquidity.
- [OCC Equity Option Specifications](https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications) — standard 100-share contract and adjusted-contract caveat.
- [OIC Equity versus Index Options](https://www.optionseducation.org/advancedconcepts/equity-vs-index-options) — index multiplier, moneyness, settlement, and exercise distinctions.
- [Cboe SPX Weeklys Specifications](https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/) — SPX/SPXW/SPY roots, settlement/exercise, expirations, and GTH.
- [Cboe Option Trades](https://datashop.cboe.com/option-trades) — exchange, NBBO-at-trade,
  underlying, condition, and optional Greek context available in a richer authoritative product.
- [Cboe Options Lite](https://www.cboe.com/data/market-data-services/cboe-options-lite/) — canonical
  reference fields and consolidated NBBO/last-sale coverage.
- [Cboe U.S. Options BOE specification](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-titanium-u.s.-options-boe-specification) — explicit trade cancel/correct identity and revisions.
- [OPRA Description of Use](https://cdn.opraplan.com/documents/OPRA_Exhibit_A.pdf) — internal,
  external, and non-display data-use categories that require contract verification.
