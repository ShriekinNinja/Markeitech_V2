# Source Census

This is a navigation and provenance map, not a cache of provider rules. Refresh the relevant page
on the day of a consequential consultation, record its displayed version or update date, and cite
the exact section used. IB pages, exchange schedules, entitlements, limits, and error behavior can
change without a Markeitech release.

## Source Precedence

1. Current IBKR Campus API documentation for IB capability and provider behavior.
2. Current exchange product specifications, calendars, and dated notices for venue truth.
3. IANA tzdb for civil-time offsets and transitions.
4. Current tracked Markeitech authority for product and safety boundaries.
5. Exact sanitized connected observations for their recorded environment and scope only.

The legacy `interactivebrokers.github.io/tws-api` site is deprecated by its own banner. Use it only
as historical corroboration when current IBKR Campus documentation does not preserve the needed
detail; label that limitation and do not silently promote it to current provider truth.

## Interactive Brokers Primary Sources

Accessed 2026-08-25. Publisher and copyright holder: Interactive Brokers LLC unless the page says
otherwise. These pages are evidence sources, not reusable licensed skill text; this skill links to
and summarizes narrow decision rules without copying documentation.

| Source | URL | Use | Freshness and compatibility concern |
|---|---|---|---|
| TWS API documentation root | https://ibkrcampus.com/docs/tws-api/ | Current entry point for socket API contracts, callbacks, settings, requests, and message codes | Follow the current navigation and changelog; do not assume examples match the installed TWS/API or Nautilus adapter version. |
| IBKR API changelog | https://ibkrcampus.com/docs/general/changelog | Detect documentation and request-contract changes, including continuous-future requirements | A changelog entry is provider documentation, not adapter acceptance. |
| Pacing behavior | https://ibkrcampus.com/docs/tws-api/doc/pacing-limitations/pacing-behavior | Current socket message-rate behavior and over-rate handling | Keep this resource family separate from historical, line, scanner, depth, and adapter-local limits. |
| Request contract details | https://ibkrcampus.com/docs/tws-api/doc/contracts-financial-instruments/contract-details/request-contract-details | Contract discovery, ambiguity, returned contract details, and exact request/response boundary | Multiple matches or successful qualification do not prove entitlement or delivery. |
| Request option chains | https://ibkrcampus.com/docs/tws-api/doc/contracts-financial-instruments/option-chains/request-option-chains | Security-definition option parameter discovery | Definition discovery is not per-contract streaming data, a full-chain subscription, or adapter support. |
| Request market rules | https://ibkrcampus.com/docs/tws-api/doc/orders/minimum-price-increment/request-market-rule | Price-increment schedules associated with returned market-rule IDs | The smallest contract `minTick` is not sufficient when price bands vary. This page lives under orders but supplies contract metadata; it does not authorize execution. |
| Live-data limitations | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/live-data-limitations | Subscription prerequisites, unavailable cases, and live-feed caveats | Refresh for the exact venue and data family; TWS display is not proof of API or adapter delivery. |
| Delayed market-data behavior | https://ibkrcampus.com/docs/tws-api/doc/market-data-delayed/market-data-type-behavior | Live, frozen, delayed, and delayed-frozen selection behavior | Requested mode and returned mode are separate evidence. Delayed support is not uniform. |
| Request top-of-book data | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/top-of-book-l-1/request-watchlist-data | `reqMktData`, generic ticks, streaming/snapshot request shape, and cancellations | Verify exact tick availability, subscription, snapshot policy, and market-data-line cost. |
| Request tick-by-tick data | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/tick-by-tick-data/request-tick-by-tick-data | Tick-by-tick request types, limits, parameters, and supported cases | Do not infer parity with watchlist ticks, historical ticks, real-time bars, or adapter callbacks. |
| Request five-second real-time bars | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/5-second-bars/request-real-time-bars | Real-time-bar request contract, pacing relationship, fields, and callback cadence | Five-second bars are a distinct request family; they do not prove tick flow. |
| Request market depth | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/market-depth-l-2/request-market-depth | L2 request shape, SMART-depth selection, row count, and cancellation | Depth entitlements, exchange support, subscription limits, and adapter exposure remain separate checks. |
| Request option Greeks | https://ibkrcampus.com/docs/tws-api/doc/market-data-live/option-greeks/request-options-greeks | Option computation callbacks and underlying/option subscription prerequisites | A returned model computation is not exchange-observed intent, and IB capability is not adapter proof. |
| Historical small-bar pacing | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-data-limitations/pacing-violations-for-small-bars-30-secs-or-less | Duplicate, burst, and rolling pacing constraints for the governed small-bar requests | Re-check applicability by bar size and current documentation; do not generalize to every request family. |
| Unavailable historical data | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-data-limitations/unavailable-historical-data | Retention and unsupported historical cases, including expired instruments | No-data classification still requires exact contract lifetime, request, session, and entitlement evidence. |
| Requesting historical bars | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-bars/requesting-historical-bars | Exact `reqHistoricalData` parameters, `useRTH`, `whatToShow`, time format, continuous-future request conditions, and update behavior | Re-open linked valid-duration, bar-size, data-type, and limitation pages for the exact request. |
| Request historical time and sales | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-time-sales/requesting-time-and-sales-data | Historical tick request parameters, tick types, bounds, and return limits | Historical ticks are not interchangeable with streaming tick-by-tick data or bars. |
| Historical `SCHEDULE` data | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-bar-what-to-show/schedule | IB schedule request type and returned session metadata | Provider schedule output must still be compared with the venue's current calendar and project phase semantics. |
| Historical operator timezone | https://ibkrcampus.com/docs/tws-api/doc/market-data-historical/historical-date-formatting/operator-time-zone | Operator-timezone return behavior and configuration context | Inspect the sibling exchange-timezone and UTC pages for the chosen mode; never infer the operator setting. |
| Error codes | https://ibkrcampus.com/docs/tws-api/doc/error-handling/error-codes | Current provider/system/request error-code catalog and messages | Interpret codes with request context and current system-message guidance; informational farm state is not automatically an outage. |
| Market scanner subscription | https://ibkrcampus.com/docs/tws-api/doc/market-scanner/market-scanner-subscription/request-market-scanner-subscription | Scanner request/filter structure and subscription lifecycle | Scanner discovery neither includes full market data nor proves entitlement for returned contracts. |
| TWS API settings schema | https://ibkrcampus.com/docs/tws-api/protobuf/api-settings-config | Read-only mode, message-rate handling, schedule exposure, returned historical-data timezone, and related TWS/IB Gateway settings | A setting's existence does not prove the operator selected it or that an adapter exposes it. |
| Third-party integration FAQ | https://ibkrcampus.com/docs/third-party-integrations/general-third-party-frequently-asked-questions | Username-scoped subscriptions, paper-data sharing, API-specific permissions, chart differences, no-data and pacing diagnostics | FAQ answers aid classification but do not replace exact account evidence or method documentation. |
| Market-data training lesson | https://ibkrcampus.com/campus/trading-lessons/python-receiving-market-data/ | IB-authored examples and clarifications for streaming, history, options, timestamps, and continuous futures | Lessons and comments are secondary to the current API reference; do not treat third-party library examples as supported contracts. |
| IBKR market-data subscriptions | https://www.interactivebrokers.com/en/pricing/research-news-marketdata.php | Current subscription catalog, professional/non-professional distinctions, and fees | Entitlement is username-, venue-, product-, and account-context specific; never infer it from this catalog. Do not purchase or change subscriptions. |

The direct pages above were refreshed on 2026-08-25. They do not display one shared semantic
version, so record the page's displayed update date when present, the current TWS/API version under
review, and relevant changelog entries in each consultation. Follow sibling request, receive,
cancellation, limitation, duration, bar-size, tick-type, timezone, and system-message pages as the
exact question requires. A broad root citation is not enough for a consequential claim.

## Venue And Time Primary Sources

| Source | URL | Publisher / license posture | Use and boundary |
|---|---|---|---|
| CME Group trading and holiday hours | https://www.cmegroup.com/trading-hours.html | CME Group copyright; link and narrow summary only | Current product-specific Globex hours, early closes, maintenance, and dated holiday changes. Schedules are explicitly subject to change. |
| NYSE hours and calendars | https://www.nyse.com/trade/hours-calendars | Intercontinental Exchange / NYSE copyright; link and narrow summary only | Current cash-market regular hours, full holidays, and early closes for the applicable NYSE market. |
| London Stock Exchange business days | https://www.londonstockexchange.com/trade/trading-access/business-days | London Stock Exchange Group copyright; link and narrow summary only | Current LSE business days, holidays, and early closes. Use only when the instrument and claim are actually governed by LSE; this does not define a universal cross-asset "London session." |
| IANA Time Zone Database | https://www.iana.org/time-zones | IANA-maintained database; public data with its published terms | Resolve `Europe/London`, `America/New_York`, exchange zones, DST gaps/folds, and historical rule changes by date. Never substitute a fixed UTC offset. |
| ISO 10383 MIC registry | https://www.iso20022.org/market-identifier-codes | ISO 20022 Registration Authority; use registry facts under published terms | Verify venue/MIC identity when it affects contract or session meaning; an IB exchange string is not automatically an ISO MIC. |

For Cboe, ICE, Eurex, Euronext, Nasdaq, or another venue, use that venue's current official product
specification, calendar, and dated notices. Do not generalize NYSE or CME hours across venues.

## Connected Evidence Sources

Connected logs, TWS/IB Gateway screens, account subscription pages, Nautilus callbacks, and
Markeitech operational events are measurements, not public documentation. Use them only when
Markeitect authorizes the exact connected activity or supplies existing evidence. Sanitize account
identifiers and never persist credentials, invoices, or licensed raw data in the skill or report.
