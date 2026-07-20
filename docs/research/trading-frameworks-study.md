# Trading Frameworks Study

Status: research note, non-authoritative  
Reviewed through: 2026-07-20

This document records ideas worth studying from Fabio Valentini, Oliver Velez,
Jim Dalton, and Linda Bradford Raschke. It does not define Markeitech signals or
change an accepted architecture decision.

## The Markeitech Boundary

These traders are accomplished educators and practitioners in their respective
styles. They are sources of vocabulary, observations, and testable hypotheses.
They are not specifications for Markeitech.

Markeitech must not copy a public strategy and assume that the visible rules are
the complete edge. Public teaching can omit discretionary judgment, instrument
familiarity, execution skill, failed experiments, costs, selection effects, or
rules the teacher does not consciously articulate.

Every borrowed idea must therefore pass through this process:

1. Name the source and distinguish a sourced statement from our inference.
2. Translate the idea into observable, point-in-time evidence.
3. Preserve instrument, session, timeframe, and data-fidelity context.
4. Test competing definitions instead of choosing thresholds by storytelling.
5. Measure frequency, MAE, MFE, invalidation latency, and target outcomes.
6. Keep the feature in shadow until out-of-sample evidence supports promotion.
7. Let Markeitech combine, reject, or materially transform the idea.

The final system is ours. External names should remain research provenance, not
permanent product semantics.

## Combined View

| Source | Strongest contribution | What Markeitech should not copy |
| --- | --- | --- |
| Jim Dalton | Auction state, evolving value, acceptance, rejection, and trade location | Retrospective or discretionary profile labels presented as precise live rules |
| Fabio Valentini | Sequential evidence: Direction, Location, then Aggression | One universal rejection setup or unsourced order-flow thresholds |
| Oliver Velez | Compact price-action patterns, moving-average geometry, and pattern invalidation | Advertised win rates, fixed sizing claims, or mandatory two-minute execution |
| Linda Raschke | Separate playbooks for trend, mean reversion, and breakout conditions; explicit risk and fast failure recognition | A catalog of named setups without regime and instrument validation |
| Markeitech | Point-in-time composition, evidence fidelity, durable lifecycle, cross-market context, outcome research, and operator narratives | Outsourcing judgment to any teacher or indicator |

A promising synthesis is:

```text
Auction state and value       Dalton-inspired research
    -> directional thesis     Markeitech context and cross-market evidence
    -> setup structure        Markeitect reference set plus price-action research
    -> actionable location    profiles, VWAP, structure, FVGs, and confluence
    -> response               price action plus order flow at explicit fidelity
    -> lifecycle narrative    approach, enter, reject, hold, target, fail, exit
```

This is a research map, not a required linear signal.

## Fabio Valentini

### What He Offers

Valentini's public framework is best understood as a sequential decision
process built on Auction Market Theory:

```text
Auction regime / Direction -> Location -> Aggression -> execution and management
```

Direction should include balance versus imbalance and evidence of controlling
pressure. Location is commonly profile-derived: value edges, POC, LVNs, VWAP,
or another meaningful auction reference. Aggression is contemporaneous buying
or selling pressure at that location, using footprint, delta/CVD, large prints,
absorption, exhaustion, or tape behavior.

The sequence is not one complete setup. At minimum, the public material implies
separate continuation and failed-auction mean-reversion playbooks:

- Imbalance continuation: displacement from value, a pullback into an
  inefficient part of the impulse, and renewed aggression in the move's
  direction.
- Failed auction: an attempted departure from balance, failure and acceptance
  back inside, then evidence supporting rotation toward fair value.

### Markeitech Relevance

`Candidate -> Armed -> Triggered` is structurally compatible with sequential
evidence, but the meanings must remain ours. Current trend scores are not a full
auction-regime classifier. General support, resistance, and FVG zones are not
automatically Fabio-style profile locations. Three completed post-arm one-minute
bars are not equivalent to footprint aggression at the location.

Research questions:

- How should balance, imbalance, and value migration be measured live?
- Which profile owns a location: prior session, current session, composite, or
  a fixed impulse leg?
- Must confirmation occur inside the zone, during the touch, or within a maximum
  time and distance after departure?
- Which observations distinguish absorption, exhaustion, failed aggression,
  and genuine follow-through?
- What event invalidates a pre-entry thesis, and what event changes management
  after entry?

### Watch And Read

- [Trading LIVE with the #1 Scalper in the WORLD](https://www.youtube.com/watch?v=tvERE-Beu2U)
- [I Traded with the World #1 Scalper](https://www.youtube.com/watch?v=cLgdXZnLL_0)
- [World's #1 Scalper: These Small Mistakes Are Keeping You Unprofitable](https://www.youtube.com/watch?v=POr0z1KEqu4)
- [Fabio Valentini masterclass overview](https://www.chartacademy.com/instructors/fabio-valentini)
- [Auction Market Strategy reconstruction](https://www.chartfanatics.com/strategies/auction-market-strategy)

The secondary reconstruction is useful for hypotheses, not authoritative
thresholds. Performance titles and competition figures do not validate each
attributed rule.

## Oliver Velez

### What He Offers

Velez provides a compact price-action language that can be measured from OHLCV:

- narrow and wide relationships between the 20- and 200-period averages;
- average slope, separation, compression, expansion, and price extension;
- available `space` between a possible entry and the next obstacle;
- power or Elephant bars relative to recent range, body, close, and volume;
- small countertrend interruption bars followed by continuation;
- three-bar pullbacks and 180-degree reversal structures;
- anticipatory entry versus confirmation by breaking a defining bar;
- invalidation at the opposite side of the pattern;
- active damage control when the expected response does not occur.

His strongest lesson for Markeitech is that a pattern without location is weak.
This matches the reference-set annotations around EMA rejection, value departure,
holding behavior, and exit after a contrary close.

### Markeitech Relevance

Do not build an `Oliver Velez strategy`. Candidate research features include:

- normalized 20/200 separation and slopes;
- distance to each average and to the next structural/profile obstacle;
- interruption-bar range percentile and pullback depth;
- expansion-bar body, wick, close-location, and volume percentiles;
- pattern identity, confirmation type, invalidation price, and session minute;
- tick response and profile location after the price pattern appears.

Two-minute bars may be tested as one deterministic view derived from one-minute
data. They are not inherently superior to 1m, 5m, or 15m bars, and bucket
alignment must be explicit.

### Watch And Read

- [Official Oliver Velez Trading channel](https://www.youtube.com/@oliverveleztrading)
- [Trading Master Class with Oliver Velez](https://www.youtube.com/watch?v=UiJTe_-fFGM)
- [Simple and Powerful Two-SMA Trading System](https://www.youtube.com/watch?v=fw7Fx1Hme9U)
- [My Favorite 2-Minute Setup](https://www.youtube.com/watch?v=Uo3jDG2IZqU)
- [Violence Into the 200](https://www.youtube.com/watch?v=0g-r7l4iljU)
- [Never Trust a Hard Sloping 200](https://www.youtube.com/watch?v=fwYh9jYXnfU)
- [Rules for Confident Trade Entries](https://www.youtube.com/watch?v=XPwFnPT9G1s)
- [Trade the Open Like a Boss: Bear 180](https://vimeo.com/141634728)

Published probability, sizing, and performance claims remain unverified until
our own point-in-time dataset reproduces them.

## Jim Dalton

### What He Offers

Dalton supplies a deeper auction-context layer beneath the abbreviated AMT
language often used online:

- markets operate as continuous two-way auctions between balance and imbalance;
- price advertises opportunity while value describes accepted business;
- higher, lower, or overlapping value shows migration or lack of migration;
- excess can indicate a completed auction and strong rejection at an extreme;
- poor or weak highs and lows describe structurally unfinished extremes;
- one-timeframing describes persistent control until a prior-period extreme is
  violated;
- profile shape, single prints, overnight inventory, and composite structure
  provide context rather than automatic entries;
- day type evolves and may remain uncertain during the session.

Dalton is especially useful because Markeitech currently calculates profile
levels but does not yet model the auction's relationship with those levels
deeply enough.

### Markeitech Relevance

Initial features should remain observational:

- balance/imbalance classification with `unknown` and revision history;
- developing and session-to-session POC/VAH/VAL migration;
- excursion, dwell, close, volume, and return-latency evidence around value;
- acceptance and rejection hypotheses with competing definitions;
- 30-minute one-timeframing state and break events;
- excess and poor-extreme quality at tick-aware tolerances;
- deterministic composite segmentation without retrospective boundary choice;
- trade-location score: edge versus middle, room to target, and opposing
  references.

Dalton context should first stratify and explain signal outcomes. It should not
become a veto until evidence shows that a specific state improves a specific
setup family.

### Watch And Read

- [Review of the Principles That Jim Dalton Trades By](https://www.youtube.com/watch?v=J4SqkwZQsw4)
- [Signature Trading Opportunities](https://www.youtube.com/watch?v=_ef1eWkfsHY)
- [The Market Profile: Trading Value versus Price](https://www.youtube.com/watch?v=LgIPFsIjyLs)
- [Scalping with the Market Profile](https://www.youtube.com/watch?v=HeWdnIt5tGk)
- [Two Distinct Day-Trading Timeframes](https://jimdaltontrading.com/january-26-2018-webinar-recording/)
- [Night Trading and the Day-Timeframe Opening](https://jimdaltontrading.com/february-13-2018-webinar-recording/)
- [Current Market Profile Primer outline](https://jimdaltontrading.com/product/market-profile-primer-april-2024/)

Dalton's `Mind Over Markets` and `Markets in Profile` are foundational books.
His current course outline explicitly notes that some older concepts have been
modified or discarded, so the books are foundations rather than immutable law.

## Linda Bradford Raschke

### Why She Belongs In This Study

Raschke adds a perspective the other three do not provide as clearly: one setup
should not be forced across every market condition. Trend, mean reversion, and
breakout behavior have different premises, triggers, risk, and management.

Her material emphasizes:

- volatility contraction followed by range expansion;
- opening-range and session behavior;
- short-term recurring price patterns rather than prediction;
- pullbacks within established momentum;
- failed breakouts and mean reversion as different playbooks;
- trade location and day-type context;
- initial risk defined before entry;
- exiting promptly when the expected response does not occur;
- simple research, consistent execution, journaling, and process discipline.

### Markeitech Relevance

Raschke supports a portfolio of small, explicit setup definitions rather than
one universal signal. Candidate hypotheses include:

- volatility contraction and subsequent expansion normalized by ATR;
- opening-range width, break, failure, retest, and time-of-day;
- trend-pullback depth, momentum persistence, and resumed expansion;
- failed-breakout return latency and acceptance back inside the range;
- pattern-specific initial invalidation and `should work now` timeout;
- separate target and management policies by trend, range, and breakout family;
- setup frequency and expectancy conditioned on instrument and volatility.

Her work also reinforces a crucial lifecycle distinction: a technically valid
entry is not a complete trade narrative. Hold, reduce, exit, and failure events
need their own evidence and should not be guessed from the entry rule.

### Watch And Read

- [Linda's official video library](https://lindaraschke.net/linda-videos/)
- [Short Term Scalping Patterns with Candlesticks](https://www.youtube.com/watch?v=kv2H152ISdM)
- [Making a Career Day Trading](https://www.youtube.com/watch?v=iOiSDHwDW3s)
- [Interview with a Market Wizard](https://www.youtube.com/results?search_query=Linda+Bradford+Raschke+Chat+With+Traders+48)
- [Trading Edges, Market Modelling, and Day Trading Techniques](https://bettersystemtrader.com/049-linda-raschke/)
- [Short-term scalping presentation](https://lindaraschke.net/wp-content/uploads/Short-Term-Scalping-Fun-with-Candlesticks.pdf)
- [Range-expansion research ebook](https://lindaraschke.net/wp-content/uploads/EBook_Updated.pdf)

Some named setups are described more completely in paid books or presentations.
Markeitech should not reconstruct missing rules from third-party summaries and
then attribute those rules to Raschke.

## Proposed Research Order

1. Enrich the Markeitect reference set without forcing teacher-specific labels.
2. Correct location interaction: approach, touch, acceptance, rejection, and
   departure must be observable rather than inferred from proximity alone.
3. Separate continuation, failed-auction mean reversion, and structural
   rejection as independent setup families.
4. Add price-action confirmation alongside explicitly labeled order-flow
   confirmation; neither should counterfeit the other.
5. Add Dalton-style auction features as shadow context and outcome strata.
6. Add Velez- and Raschke-inspired pattern features as shadow observations.
7. Compare candidate definitions against the same point-in-time outcome audit.
8. Promote only the combinations that improve usefulness outside the examples
   used to define them.

## Explicit Non-Goals

- No teacher receives veto authority over Markeitech.
- No public win rate is accepted as a calibration target.
- No setup is promoted because it looks convincing on selected screenshots.
- No candle proxy is labeled as true footprint, book, or classified-tick data.
- No retrospective profile boundary may leak into a live feature.
- No single signal family is expected to describe every tradable market event.
- No ML model may learn from teacher names as substitutes for measurable state.

The intended outcome is not a better copy of someone else's system. It is a
better vocabulary for discovering, testing, and explaining Markeitech's own.
