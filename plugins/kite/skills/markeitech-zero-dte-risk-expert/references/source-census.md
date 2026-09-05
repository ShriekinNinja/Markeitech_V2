# Zero DTE Candidate Risk Source Census

Last researched: 2026-08-25. This is a routing map, not frozen doctrine. Refresh the exact source,
effective version, relevant section, access timestamp, product, date, venue, broker, and conclusion
for every review.

## Tracked Markeitech Authority

- `AGENTS.md`, `markeitech.md`, `docs/current-status.md`, `docs/development-guidelines.md`, and
  `docs/README.md`: authority, product boundary, current implementation, evidence discipline, and
  permissions.
- `docs/roadmap/v2-market-events-live-agent-plan.md`: accepted Options Intelligence ownership,
  opportunity/expression separation, bounded options proof, candidate evidence, and advisory limit.
- `docs/product/sir-loke-v1.md`: first-version SPXW/QQQ scope, recommendation, trade episode,
  monitoring, governance, account-observation, and no-execution boundary.
- `docs/market-intelligence-request-catalog.md`: requested quote, Greek, IV, liquidity, expiry,
  degradation, and event evidence.
- `docs/research/gamma-exposure-and-0dte-gex-maps.md`: research-only gamma/GEX limitations; it does
  not authorize live dealer-position or contract-risk claims.

Tracked research is subordinate to the charter, accepted plans, current implementation, and exact
current market evidence.

## Product, Exercise, And Settlement Sources

| Source | Use | Required limit |
| --- | --- | --- |
| [OCC Characteristics and Risks of Standardized Options](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document) | General holder/writer, exercise, assignment, settlement, interruption, and standardized-option risk baseline | Refresh the current ODD and supplements. It is not an exact series specification, broker policy, or account decision. |
| [OCC information memos](https://infomemo.theocc.com/infomemo/search) | Contract adjustments, accelerated expirations, special settlement, and current clearing notices | Search the exact root/series and date; absence of a found memo is not proof that no adjustment exists. |
| [Cboe SPX/SPXW specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications/) | SPX/SPXW multiplier, sessions, expiration trading hours, and linked product terms | Follow current linked rules/notices and verify populated fields. Do not transfer to SPY or QQQ. |
| [Cboe ETP option specifications](https://www.cboe.com/exchange-traded-stock/etp-options-spec) | General ETP option exercise, physical settlement, deliverable, and trading-hour baseline for products such as SPY and QQQ | Confirm the exact listed series, venue, deliverable, adjustment state, and current rule; general ETP terms are not enough for a non-standard contract. |
| [Cboe settlement-style explanation](https://www.cboe.com/tradable_products/sp_500/mini_spx_options/cash_settlement) | Illustrates physical ETF delivery versus cash-settled index consequences | Education only; exact product terms and broker/account behavior require separate evidence. |
| [Cboe U.S. options hours and holidays](https://www.cboe.com/about/hours/us-options) | Current sessions, holidays, early closes, and expiration-calendar route | Dynamic and date-sensitive. It does not prove listing, quote validity, or exact last-trade rules. |

The options-market mechanics owner establishes exact product and series truth. The risk advisor
consumes that result and explains consequences.

## Broker Sources

| Source | Use | Required limit |
| --- | --- | --- |
| [Interactive Brokers delivery, exercise, and corporate-action policy](https://www.interactivebrokers.com/en/trading/delivery-exercise-actions.php) | Public expiration exercise, lapse, delivery, protective-action, and contrary-instruction policy | Refresh the effective page and relevant section. Public policy does not establish what IB will do in a particular account or scenario. |
| Exact current broker agreement, notice, or support response supplied by Markeitect | Broker-specific cutoff or treatment not covered by the public page | Treat credentials and unnecessary account data as out of scope. Preserve account-specific behavior as unknown without an approved owner. |

Do not connect to a broker or inspect an account without separate exact authorization.

## Official Event And Market-State Source Routing

Select the official source that owns the scheduled fact:

| Event class | Primary route | Limits |
| --- | --- | --- |
| FOMC meetings, statements, projections, minutes, and press conferences | [Federal Reserve FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | Refresh on the decision date; timing is fact, market response is a scenario. |
| CPI, employment, PPI, and other BLS releases | [BLS release calendar](https://www.bls.gov/schedule/) | Record release, scheduled time, timezone, update state, and access time. |
| GDP, PCE, income, and other BEA releases | [BEA release schedule](https://www.bea.gov/news/schedule) | Record the exact release and revision status; do not infer surprise or direction. |
| Treasury auctions, refunding, and financing announcements | [U.S. Treasury auction schedule](https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.pdf) and exact Treasury notice | Tentative schedules may change; refresh the exact notice and timezone. |
| Exchange halts, restrictions, sessions, and notices | Exact listing-exchange status, circular, notice, or schedule page | General calendars do not prove a particular halt or series condition. |
| ETF issuer events, distributions, or corporate actions | Exact issuer, exchange, OCC, or SEC filing | Use the source that owns the fact; preserve adjustment and deliverable uncertainty. |

Unscheduled news remains unresolved exposure, not a predicted event.

## Quote, Greek, IV, And Scenario Evidence

These values require the exact supplied evidence and owning-specialist disposition, not a public
research page:

- contract and provider/feed/venue or consolidated scope;
- entitlement/delivery mode and selector;
- bid/ask, sizes, quote conditions, event and receipt times, ordering, corrections/revisions,
  coverage, and suppressed/dropped counts;
- metric ID/version, spread formula and denominator, units, timestamp clocks, freshness and
  stability policy;
- IV/Greek provider/model, field semantics, units, reference, assumptions, timestamps, update
  trigger, revision state, and applicability; and
- scenario model/version, inputs, shocks/path, surface assumption, exercise treatment,
  precision/tolerance, independent check, and invariants.

Provider documentation is provider truth only. The IB market-data advisor owns IB delivery and
field prerequisites; the options-market mechanics owner owns listed-option semantics; the
Nautilus advisor owns adapter exposure; and the data-quality, quantitative-validation, and
evidence-fitness advisors own downstream admissibility.

## Contextual Research Excluded From Candidate Decisions

Academic or exchange-authored studies of aggregate 0DTE dealer gamma, market-maker inventory,
hedging, positioning, and market impact may inform separately approved research. They do not
establish the risk of a named live candidate and are not part of this advisor's operational source
path. Route those claims to the appropriate market-microstructure, options-flow, statistical, or
evidence-validation specialist.

## Evidence Record Required Per Review

Obtain or mark unknown:

- exact source URL/document identity, publisher, effective/publication version, relevant section,
  access timestamp, and applicability;
- exact candidate and position context;
- exchange trade date, session, holiday state, expiration, last-trade time, and timezone;
- named underlying/reference with reported/derived/proxy fidelity and timestamps;
- canonical candidate-state and policy/configuration identities;
- validated quote, spread, age, sequence, IV, Greek, and scenario evidence identities;
- official event facts and revisions; and
- public broker policy plus explicit account-specific unknowns.

Absence of current evidence is not repaired by this census. Return the smallest required
consultation, a bounded unknown, or a stopped lane.
