# Interactive Brokers Market-Data Subscriptions

**Status:** Read-only planning recommendation; no subscription purchase or connected acceptance

**Last verified against public IBKR documentation:** 2026-09-02

## Purpose

This guide maps Markeitech's current and planned observation requirements to Interactive Brokers
market-data subscriptions. It separates:

- the exact current V3 ES runtime;
- the broader configured observation universe;
- the first-version SPXW and QQQ 0DTE expressions plus later SPY candidates; and
- feeds which should not be purchased until a named capability requires them.

It does not authorize a subscription purchase, change the runtime configuration, establish
provider delivery through the pinned NautilusTrader adapter, approve options intelligence, grant
execution authority, or provide legal approval. Public package names and prices are planning
evidence only. The authenticated Client Portal offering, subscriber classification, username,
account affiliate, and signed terms control the actual entitlement.

## Recommendation Summary

Subscribe in phases:

1. For the exact current tracked V3 runtime, retain only `CME Real-Time (L1)`.
2. Add direct Level 1 exchange feeds when the corresponding instruments are enabled in a connected
   profile.
3. Add `OPRA (US Options Exchanges)(L1)` only when bounded live SPXW and QQQ options
   acquisition is approved and implemented.
4. Do not buy Level 2, venue-specific depth, quote boosters, or news packages before a named
   capability and measured resource need exist.
5. Prefer the direct-feed list as the planning baseline. Use an IBKR bundle only if it appears for
   the exact account and its account-visible terms cover Markeitech's API/non-display use.

## Phase 1: Exact Current V3 ES Runtime

The tracked V3 profile currently enables one explicit instrument, `ESU6.CME`, and one acquisition
capability, `watchlist_last`. It also makes bounded historical-bar requests. See
[`config/system.v3-es-minimal.toml`](../../config/system.v3-es-minimal.toml).

| IBKR subscription | Coverage | Markeitech requirement | Published non-professional price |
| --- | --- | --- | ---: |
| `CME Real-Time (L1)` | ES; also NQ when enabled | Real-time Level 1 data, five-second bars, and entitlement for historical API bars | Approximately USD 1.55/month |

No additional exchange subscription is required merely to add NQ because ES and NQ are both CME
products. Exact dated contracts and rollover remain separately controlled by Markeitech
configuration and the futures-rollover procedure.

The following are not required by the exact current profile:

- OPRA options data;
- U.S. equity Networks A, B, or C;
- Cboe index data;
- futures or options Level 2 data;
- venue-specific order books; or
- news and research packages.

## Phase 2: Broader Configured Observation Universe

The full configuration template contains ES, NQ, YM, CL, SPY, QQQ, SPX, VIX, TSM, and several
Nasdaq-listed equities. Enabling that universe with real-time, consolidated Level 1 data requires
the following direct feeds.

| Exact IBKR subscription name | Markeitech instruments or class | Published non-professional price |
| --- | --- | ---: |
| `CME Real-Time (L1)` | ES and NQ futures | USD 1.55/month |
| `CBOT Real-Time (L1)` | YM futures | USD 1.55/month |
| `NYMEX Real-Time (L1)` | CL futures | USD 1.55/month |
| `NYSE (Network A/CTA)(L1) - Billed by Broker` | TSM and other NYSE-listed evidence instruments | USD 1.50/month |
| `NYSE American, BATS, ARCA, IEX and Regional Exchanges (Network B)(L1)` | SPY and other Tape B/ARCA instruments | USD 1.50/month |
| `NASDAQ (Network C/UTP)(L1)` | QQQ and configured Nasdaq-listed equities | USD 1.50/month |
| `CBOE Streaming Market Indexes` | SPX; likely VIX, subject to an exact-symbol Market Data Assistant check | USD 3.50/month |

The indicative total is approximately **USD 12.65/month** for a qualifying non-professional user,
before taxes, account/entity restrictions, pricing changes, and without assuming commission
waivers. Do not apply this total to a professional subscriber; professional products and prices
differ substantially.

The relevant configured instruments are declared in
[`config/system.example.toml`](../../config/system.example.toml).

### Consolidated Equity Data Requirement

IBKR includes free real-time U.S. equity and ETF data from Cboe One and IEX, but describes it as
non-consolidated. It does not establish the consolidated NBBO required for comparable Markeitech
quote-quality and liquidity evidence. Use the appropriate Network A, B, or C feed for a connected
instrument whose analysis depends on consolidated top-of-book data.

IBKR's subscription guide maps:

- SPY and other ARCA/Tape B products to Network B;
- Nasdaq-listed products to Network C;
- NYSE-listed products to Network A; and
- SPX to `CBOE Streaming Market Indexes`.

Sources:

- [IBKR popular market-data subscriptions](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/popular-market-data-subscriptions/introduction)
- [IBKR market-data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)

## Phase 3: First-Version SPXW/QQQ And Later SPY Options

SPXW and QQQ 0DTE options are Markeitech's first-version configurable expressions; SPY remains a
later candidate. No expression product is globally preferred. Options intelligence and bounded
option-chain acquisition are not currently accepted live runtime capabilities, so OPRA should not
be purchased solely because options appear in the product charter.

When live options discovery and context are approved, the smallest product-neutral entitlement
set is:

| Subscription | SPXW | SPY options | QQQ options | Purpose |
| --- | ---: | ---: | ---: | --- |
| `OPRA (US Options Exchanges)(L1)` | Required | Required | Required | Live option bid/ask, displayed sizes, last sales, volume, and option market-data requests carrying IBKR computations |
| `CBOE Streaming Market Indexes` | Required | No | No | Live SPX underlying value and the underlying dependency for SPXW Greeks and implied volatility |
| `NYSE American, BATS, ARCA, IEX and Regional Exchanges (Network B)(L1)` | No | Required | No | Consolidated SPY underlying quote and the underlying dependency for SPY option Greeks |
| `NASDAQ (Network C/UTP)(L1)` | No | No | Required | Consolidated QQQ underlying quote and the underlying dependency for QQQ option Greeks |
| `CME Real-Time (L1)` | Context-dependent | Context-dependent | Context-dependent | ES/NQ reference evidence, including a separately approved overnight SPXW reference method; not an options entitlement |

IBKR's published non-professional OPRA price is approximately **USD 1.50/month**. If all Phase 2
underlying feeds are already active, OPRA is the only additional exchange subscription in this
broader options-data plan. The indicative direct-feed total would then be approximately
**USD 14.15/month**.

IBKR states that an options subscription does not include the underlying feed and that option
Greeks require live market-data entitlement for the appropriate underlying.

Sources:

- [IBKR option-Greeks requirements](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-live/option-greeks/request-options-greeks)
- [IBKR option-Greeks fields](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-live/option-greeks/receiving-options-data)
- [IBKR option-chain request](https://www.interactivebrokers.com/docs/tws-api/doc/contracts-financial-instruments/option-chains/request-option-chains)
- [IBKR option-chain response](https://www.interactivebrokers.com/docs/tws-api/doc/contracts-financial-instruments/option-chains/receive-option-chains)

### Options Evidence Limits

- Option top-of-book is displayed liquidity, not guaranteed execution or fillability.
- IBKR implied volatility, delta, gamma, theta, and vega are model-derived computations, not
  exchange-observed outcomes.
- Option volume is activity, not buyer direction, opening/closing intent, strategy structure, or
  participant identity.
- Open interest is publication-lagged/as-of evidence, not live positioning.
- Contract-definition discovery for expirations, strikes, trading class, multiplier, and exchange
  is distinct from live option quote delivery.
- A successful security-definition response does not prove OPRA quote or Greek delivery.
- OPRA is consolidated Level 1 data; it is not complete option-market depth.
- An ES-derived SPX reference is derived evidence and must never be represented as reported cash
  SPX.

## Conditional Bundle Alternative

IBKR's general documentation describes this combination:

1. `US Securities Snapshot and Futures Value Bundle`
2. `US Equity and Options Add-On Streaming Bundle`
3. `CBOE Streaming Market Indexes`

The first bundle supplies top-of-book data for CBOT, CME, COMEX, and NYMEX futures. The add-on
supplies Networks A, B, and C plus OPRA and requires the first bundle. Cboe index streaming remains
separate for SPX and VIX.

The currently published non-professional planning prices are:

| Subscription | Published price |
| --- | ---: |
| `US Securities Snapshot and Futures Value Bundle` | USD 10.00/month base, subject to its published activity waiver and snapshot charges |
| `US Equity and Options Add-On Streaming Bundle` | USD 4.50/month, subject to its published waiver conditions |
| `CBOE Streaming Market Indexes` | USD 3.50/month |
| Indicative combined total | USD 18.00/month |

There is a material regional conflict in IBKR's public documentation. Its current pricing table
attaches disclosure 31, `Services only available for Canadian Residents`, to the two U.S. bundles,
while its general subscription guide presents the bundles without that warning. Bundle eligibility
for an Israel-based account is therefore **unknown** until the authenticated Client Portal or
Market Data Assistant confirms it for the exact account and username.

Use the direct exchange feeds as the safe planning baseline. Choose the bundle only if it appears
for the exact account and its account-visible agreements cover the intended API/non-display use.

## Feeds Not Required Yet

Do not purchase the following packages without a separately approved capability and evidence of
need.

| Subscription class | Current disposition |
| --- | --- |
| CME, CBOT, or NYMEX Level 2; `US Futures Value Bundle PLUS` | Deferred; current measurements do not consume exchange depth |
| `NASDAQ TotalView-OpenView` and its EDS API add-on | Deferred until an approved Nasdaq order-book capability exists |
| NYSE OpenBook or NYSE ArcaBook | Deferred until an approved venue-book capability exists |
| Venue-specific options depth | Deferred; the intended initial options slice needs Level 1 executable quotes, not full books |
| CFE data | Not required unless VIX futures become an explicit observation instrument |
| CME S&P Indexes | Not required for the current CME-futures plus Cboe-cash-index design |
| News or research packages | Not established as Markeitech market-data requirements |
| Quote booster packages | Do not buy pre-emptively; measure account-specific market-data-line pressure first |
| External options-flow feeds | Separate future provider, schema, licensing, and provenance decision |

Tick-by-tick observations use the instrument's ordinary Level 1 entitlement and do not require
Level 2. IBKR nevertheless limits simultaneous tick-by-tick subscriptions to 5% of a username's
total market-data lines. More exchange subscriptions do not remove that limit. Broad tick-trade
monitoring must remain bounded and focus-only unless a later measured design changes that policy.

Source: [IBKR tick-by-tick request limits](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-live/tick-by-tick-data/request-tick-by-tick-data)

## Account And API Prerequisites

Selecting the exchange feeds is not sufficient. Verify all of the following before subscription
or connected acceptance:

1. The account is an opened, funded `IBKR PRO` account. Demo accounts cannot subscribe to API
   market data.
2. The account holds the applicable minimum equity plus subscription costs. IBKR currently states
   USD 500 for ordinary individual and organizational accounts, with different published minimums
   for certain account categories.
3. U.S. futures trading permission is enabled for U.S. futures data. This permission does not
   grant Markeitech execution authority; the runtime remains data-only and read-only.
4. `Market Data API Acknowledgement` is enabled and signed in Client Portal. IBKR states that API
   requests may otherwise return market-data-not-subscribed errors.
5. Entitlements belong to the exact username used by TWS or IB Gateway.
6. The exact live username explicitly shares its subscriptions with the exact paper username used
   by Markeitech, where that facility is used.
7. The same shared entitlement is not expected to serve competing live and paper sessions
   simultaneously.
8. Every additional username is budgeted separately because market-data subscriptions are
   generally username-bound.
9. The subscriber's professional or non-professional exchange classification is confirmed. This
   classification is unrelated to IBKR Pro versus IBKR Lite.
10. Commission waivers are treated as conditional. Budget the full fee unless the exact account
    demonstrably meets the package-specific waiver.
11. The runtime records whether returned data is real-time, frozen, delayed, or delayed-frozen.
    Instrument-definition success, TWS display, historical delivery, or data received through a
    different username does not prove current real-time API entitlement.

Sources:

- [IBKR API market-data requirements](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-requirements)
- [IBKR minimum-equity requirements](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-subscription-minimum-equity-balance-requirements)
- [IBKR API acknowledgement](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/compliance-requirements-for-api-market-data/market-data-api-acknowledgement)
- [IBKR market-data sharing](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-users/market-data-sharing)
- [IBKR third-party and API FAQ](https://www.interactivebrokers.com/docs/third-party-integrations/general-third-party-frequently-asked-questions)

## Market-Data-Line And Delivery Gates

IBKR initially allocates at least 100 concurrent market-data lines per user, shared across TWS and
API requests. Option contracts can consume this allowance quickly. A bounded option-chain slice
must therefore select explicit expirations and strikes instead of starting unrestricted streaming
for an entire chain.

Before accepting a feed, verify:

- exact contract identity and venue;
- real-time rather than delayed or frozen delivery;
- requested bid, ask, last, sizes, and volume fields;
- provider and receive timestamps;
- session and closed-market interpretation;
- missing and sentinel behavior;
- first-observation evidence;
- subscription cancellation and market-data-line recovery; and
- bounded behavior when the username reaches its line or specialized tick-by-tick limit.

Sources:

- [IBKR market-data lines](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-lines/introduction)
- [IBKR delayed market-data types](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-delayed/introduction)

## Licensing And Permitted-Use Gate

IBKR distinguishes ordinary TWS display, alternative display, and non-display/API use. The
applicable account and exchange agreements may impose additional authorization for programmatic
ingestion, internal derived analytics, retention, external display, and redistribution. A normal
Level 1 subscription does not by itself prove that every Markeitech use is licensed.

Before treating this subscription plan as purchase-ready, record and verify:

- the IBKR contracting affiliate and account legal type;
- professional or non-professional subscriber status and questionnaire effective date;
- exact live and paper usernames and their sharing arrangement;
- each service, device, person, and process which will access the data;
- the product name exactly as displayed in Client Portal;
- whether the product is ordered under TWS, Alternative Display, or Non-Display/API;
- the signed GFIS, API-supplement, exchange, and order-form versions;
- permitted API receipt, internal analytics, agent/model processing, caching, retention, derived
  outputs, human display, external display, and redistribution;
- commission-waiver rules, trading-permission prerequisites, taxes, and per-username fees; and
- the date and owner of the entitlement review.

The following require documented vendor authorization or qualified legal review:

- an organization account or business/commercial use;
- API ingestion without an account-visible non-display authorization;
- retained metrics, entities, semantic events, model features, or AI inputs whose derived-data
  treatment is unclear;
- sending raw observations, quotes, charts, market-derived values, or reversible derivatives to
  Discord, an external AI provider, another person, or another service;
- multiple usernames, accounts, devices, or concurrent live/paper consumers;
- redistribution or external commercial use; or
- inability to produce the current API supplement and relevant exchange-specific terms.

An ordinary brokerage subscription is not a redistribution license. Markeitech's transient raw
observation posture is prudent, but architecture alone does not establish legal permission.

Sources:

- [IBKR professional versus non-professional classification](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/professional-vs-non-professional)
- [IBKR subscription settings and display categories](https://www.ibkrguides.com/orgportal/usersettings/marketdatasubscriptions.htm)
- [GFIS Market Data and Analytics Subscriber Agreement](https://gdcdyn.interactivebrokers.com/Universal/servlet/Registration_v2.formSampleView?formdb=3089)

This section identifies a licensing-risk gate; it is not legal advice or legal approval.

## Purchase Checklist

Use the authenticated IBKR Market Data Assistant for these exact representatives:

- one current ES futures contract;
- one current NQ futures contract;
- one current YM futures contract;
- one current CL futures contract;
- SPY;
- QQQ;
- TSM;
- SPX index;
- VIX index;
- one exact SPXW option;
- one exact SPY option; and
- one exact QQQ option.

Record for each result:

- account affiliate and residence;
- professional or non-professional status;
- exact username and paper-sharing state;
- exact subscription name returned by IBKR;
- TWS/display versus non-display/API category;
- monthly fee, tax, and waiver conditions;
- trading-permission prerequisite;
- real-time or delayed availability;
- signed agreement identity and version; and
- review date.

Only after this authenticated check should the final account-specific purchase list be approved.

## Evidence Classification And Remaining Unknowns

### Verified From Current Checkout

- The exact tracked V3 profile is ES-only and requests `watchlist_last` plus bounded historical
  bars.
- The full template contains the broader futures, equities, ETFs, and cash-index observation
  universe listed above.
- SPXW, SPY, and QQQ are a future configurable expression universe with no globally preferred
  product.
- Option-chain acquisition and live options intelligence remain future work.
- Markeitech is data-only, read-only, and advisory; it has no order-routing authority.

### Verified From Current Public IBKR Documentation

- Most API market data requires the appropriate Level 1 subscription.
- Free U.S. equity data is non-consolidated.
- U.S. options Level 1 is supplied through OPRA.
- Option Greeks require the option feed and an entitled underlying feed.
- Market-data subscriptions are username-bound and market-data-line capacity is shared across TWS
  and API requests.
- API access requires the account and acknowledgement prerequisites described above.

### Measured But Bounded Markeitech Evidence

- The tracked ES connected acceptance returned its bounded historical bar request successfully.
- That evidence does not accept all configured instruments, all exchanges, options delivery,
  account-wide entitlements, market depth, or unrestricted concurrent subscriptions.

### Unknown Until Account-Level Verification

- The account's exact professional or non-professional classification.
- The exact packages offered to the Israel-based account and contracting affiliate.
- Whether the two U.S. bundles are available despite the public regional-documentation conflict.
- The current username's subscriptions, API acknowledgement, and live-to-paper sharing state.
- Exact VIX plan coverage.
- Account-specific prices, waivers, taxes, trading permissions, and market-data-line allowance.
- Pinned NautilusTrader adapter delivery for every planned option field, chain request, or depth
  capability.
- Exact rights for non-display use, derived analytics, model or agent processing, retention,
  external projection, and redistribution.

## Change And Review Triggers

Re-run this review before purchase or acceptance when any of the following changes:

- IBKR affiliate, residence, account type, username, or subscriber classification;
- public or account-visible subscription names, prices, prerequisites, or agreements;
- TWS, IB Gateway, IB API, NautilusTrader, or the IB adapter version;
- the connected Markeitech instrument universe;
- requested feed class, including quotes, trades, bars, books, options, or Greeks;
- raw-data retention, derived-state persistence, Discord projection, or external-model use; or
- the number of concurrent instruments or option contracts.

Do not use an older price or product table as proof that the current account can lawfully receive
the same data.
