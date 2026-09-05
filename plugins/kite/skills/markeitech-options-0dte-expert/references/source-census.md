# Primary Source Census

Last refreshed for candidate construction: **2026-08-25**. URLs are references, not bundled or
redistributed source content. Refresh the subset material to each future task.

## Repository Authority

| Source | Authority | Use | Limitation |
|---|---|---|---|
| `AGENTS.md` | Repository working and advisor boundary | Permissions, approval, delegation, evidence, and completion gates | Does not define exchange mechanics |
| `markeitech.md` | Product charter | Live-first, advisory/non-ordering, no global expression preference, evidence/configuration invariants | Does not prove implementation |
| `docs/current-status.md` | Current implementation ledger | Stage state, implemented boundaries, validation debt | Recheck code/tests for exact behavior |
| `docs/development-guidelines.md` | Engineering guidance | Separate thesis from expression; options need distinct chain/expiry/strike/liquidity/Greek semantics | Not external product authority |
| `docs/product/sir-loke-v1.md` | Accepted first-version product | SPXW/QQQ 0DTE scope, recommendation and trade-monitoring experience, evidence honesty, no-execution boundary | Product intent is not provider or implementation evidence |
| `docs/roadmap/sir-loke-v1-delivery-plan.md` | Accepted Sir Loke delivery plan | Gate 4 bounded SPXW/QQQ options evidence, plural opportunities, ownership, and persistence intent | Future intent is not implementation |
| `docs/architecture/sir-loke-v1-boundaries.md` | Accepted future architecture | Required request fields, side-effect classes, and anti-requests | Does not prove provider availability |
| `docs/roadmap/development-backlog.md` | Deferred evidence tracks | Vendor-flow provenance/overclaim guards and GEX identity/freshness/assumption gates | Historical research remains in Git and is not accepted product semantics |

## Product, Exercise, And Settlement

| Source | URL | What it establishes | Required caution |
|---|---|---|---|
| Cboe SPX specifications | https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications/ | Current published SPX/SPXW multiplier, exercise/settlement, regular/curb/global hours, and expiration trading distinctions | Refresh for holidays, circulars, and product changes; distinguish SPX from SPXW |
| Cboe SPX Weeklys | https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/ | SPXW PM settlement, European exercise, cash settlement, expiration schedule and comparison with SPY | Marketing/education page; exact series and exceptional dates still require contract/calendar proof |
| Cboe ETP option specifications | https://www.cboe.com/exchange-traded-stock/etp-options-spec/ | General ETP option underlying/deliverable and regular hours | Exact venue/class and adjusted deliverable can differ |
| Cboe Options rule book and filings | https://www.cboe.com/us/options/regulation/ | Governing rule and current filing roots for listing, trading, exercise, and settlement claims | Identify the exact exchange, rule, filing, approval/effective status, and product class; a proposal is not an effective rule |
| Cboe hours and expiration calendars | https://www.cboe.com/about/hours/us-options | Published sessions, holidays, and expiration-calendar roots | Reconcile the named product, venue, series, and effective year; a general hours table does not prove one contract's last trade |
| Cboe 2026 expanded-hours notice | https://cdn.cboe.com/resources/release_notes/2026/Schedule_Update_C1_Options_to_Offer_GTH_Sessions_for_Multi_List_Options_Series.html | Effective-date, session, and anticipated-symbol scope of one C1 equity-option hours expansion | Does not authorize a blanket assumption for SPY, QQQ, other venues, or future symbol changes |
| Nasdaq ISE Options 4 rules | https://listingcenter.nasdaq.com/rulebook/ise/rules/ISE%20Options%204 | Exchange rule text for short-term daily expirations including SPY/QQQ | Rules establish listing authority, not that every expected series is currently listed or delivered by IB |
| OCC June 2024 ODD page | https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document | Current ODD distribution page and standardized-options risk authority, including T+1 update | Refresh for a superseding ODD/supplement and use exact OCC rules for procedural details |
| OCC equity/ETF options primer | https://www.theocc.com/getmedia/dfc83aa2-4a89-42d0-8de7-69e5a71f71a2/OCC-Primer-Options-101-EquityOptions-F.pdf | Standard equity/ETF option American exercise, physical delivery, and usual 100-share contract | Adjusted contracts and broker procedures require exact verification |
| OCC Rules, Chapter VIII | https://www.theocc.com/getmedia/9d3854cd-b782-450f-bcf7-33169b0576ce/occ_rules.pdf | Governing exercise and assignment procedures | Broker cutoffs and account handling can be stricter; always use current rules |
| OCC By-Laws and Rules | https://www.theocc.com/company-information/documents-and-archives/by-laws-and-rules | Current governing-document root, including contract-adjustment authority and interpretive guidance | Record the retrieved document revision and exact chapter; search snippets or superseded copies are insufficient |
| OCC Information Memos | https://infomemo.theocc.com/infomemo/search-memo | Series-specific adjustment, deliverable, expiration, and settlement notices with posted/effective dates | Search the exact symbol and preserve memo number, update status, posted date, and effective date |
| FINRA 0DTE investor article | https://www.finra.org/investors/insights/zeroing-in-options-trading-strategy | Broker liquidation, physical versus cash settlement, assignment/funding, and amplified same-day risk context | Investor education, not a broker-specific policy or execution authorization |

## Market Data, Provider, And Evidence Fidelity

| Source | URL | What it establishes | Required caution |
|---|---|---|---|
| OPRA home and document library | https://www.opraplan.com/ and https://www.opraplan.com/document-library | OPRA's role disseminating consolidated listed-options last-sale and quotation information; current plan/specification/fee roots | A vendor or broker view may not expose full OPRA content; licensing and non-display terms require separate approval |
| OPRA Pillar Output Specification | https://cdn.opraplan.com/documents/OPRA_Pillar_Output_Specification.pdf | Current message categories, BBO appendages, conditions, sessions, open interest, and series fields | A feed type is not proof of provider delivery; version-date and implementation coverage must be recorded |
| OCC Series Search | https://www.theocc.com/market-data/market-data-reports/series-and-trading-data/series-search | Current OCC series/contract lookup surface | Do not infer open-interest timing from the page shell; verify the exact report definition and record its own as-of date before using OI |
| IBKR API documentation root | https://ibkrcampus.com/campus/ibkr-api-page/ | Current official API documentation and changelog root | Refresh exact TWS/API version; IB API existence is not Nautilus adapter delivery |
| IBKR market-data subscriptions | https://ibkrcampus.com/docs/general/market-data-subscriptions/introduction | Current official subscription categories and dependency cautions for underlying-dependent values such as Greeks | Account eligibility, professional status, exact live subscription, permissions, and observed delivery still require the IB advisor and current account evidence |
| IBKR market-data lines | https://ibkrcampus.com/docs/general/market-data-subscriptions/market-data-lines/introduction | Official simultaneous market-data-line resource model | Published examples do not prove the current account allowance, option request cost, pacing, or Nautilus release behavior |
| IBKR handling options chains | https://ibkrcampus.com/campus/ibkr-quant-news/handling-options-chains/ | Official example of staged option-chain discovery | Example targets Web API and does not prove current TWS/Nautilus semantics or entitlement |
| IBKR `SecDefOptParamsRequest` | https://ibkrcampus.com/docs/tws-api/protobuf/sec-def-opt-params-request | Current official request fields for one chain-definition interface | Verify the installed IB/Nautilus path separately |

## Greeks, Same-Day-Expiry Evidence, And Research

| Source | URL | What it establishes | Required caution |
|---|---|---|---|
| FINRA options basics and Greeks | https://www.finra.org/investors/insights/options-z-basics-greeks | Regulatory education on option mechanics, expirations, Greeks, leverage, and assignment | Explanatory, not a pricing model specification |
| Cboe 0DTE resources | https://www.cboe.com/tradable-products/0dte | Current product availability context and near-expiry sensitivity warning | Cboe is an exchange/operator and its statistics/interpretations must be identified as such |
| Cboe 2025 positioning report | https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact | Cboe's proprietary-data estimates of SPX 0DTE participant mix and hedging impact | Method- and sample-dependent; cannot be generalized to another product, date, or vendor feed |
| *0DTE Index Options and Market Volatility* (Jan. 25, 2025) | https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf | Academic analysis using proprietary Cboe trades and quote data to estimate market-maker gamma and volatility impact | Model-based study; dataset access and position inference are not reproduced by public vendor flow |
| BIS Quarterly Review, March 2024 | https://www.bis.org/publ/qtrpdf/r_qt2403.pdf | Institutionally credible context on short-dated leverage, payoff distribution, and competing volatility explanations | Aggregate historical study; not a live decision rule or current product statistic |
| Federal Reserve SCOOS, September 2023 | https://www.federalreserve.gov/data/scoos/files/scoos_202309.pdf | Survey evidence on dealer-reported 0DTE client activity and margin practice | Survey responses, dated and aggregate; not direct market positioning or broker policy |
| SEC order on OCC intraday risk, 2025 | https://www.sec.gov/files/rules/sro/occ/2025/34-102202.pdf | Regulatory record of OCC concerns about intraday exposure from 0DTE activity | Clearing-system context, not a contract-selection or trading rule |

## Source Use Rules

- Prefer current primary specifications, rules, circulars, and exact provider documentation over
  educational summaries.
- Record access date and the document's own effective/version/as-of date separately.
- Preserve source URL and title; do not copy source text into the skill beyond minimal attributed
  facts. Exchange names and product marks remain their owners' property.
- A source being publicly readable does not grant redistribution, non-display, derived-data,
  storage, external-model, or commercial-use rights.
- Conflicts between current official sources, local contracts, and observed delivery are material:
  stop and report them rather than choosing the convenient answer.
