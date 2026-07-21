# Markeitect Model

Status: Working research specification

Started: 2026-07-21

Owners: Markeitect and Kite

Branch: `codex/markeitect-model`

Motto: No Obstacles, Only Challenges.

## Purpose

The Markeitect Model captures how Markeitect reads an auction and forms a
discretionary options thesis. It replaces inherited Direction-first signal
logic as Markeitech's primary trading-intelligence research track. Existing
Fabio/DLA code and historical evidence remain available and versioned, but the
definition is disabled in checked-in runtime configurations.

This document records current understanding. It is intentionally more precise
than conversational shorthand, but it must not harden unfinished observations
into false market laws. Markeitect owns trading truth and the final call. Kite
owns faithful translation, deterministic measurement, engineering boundaries,
and challenges to unsupported claims.

## Trading Scope

The immediate trading focus is discretionary 0DTE index ETF/index options:

- QQQ options are the primary expression. NQ and QQQ are principal underlying
  evidence, with ES/SPX contributing broad-index context.
- SPX options are most attractive on strongly directional days where farther
  out-of-the-money contracts can still appreciate substantially.
- NQ and ES order flow are both required. One may lead while the other lags,
  disagrees, or exposes a false move.
- VIX, CL, SOXL, and a session-selected market-moving equity provide context.
  Their relationships are conditional and regime-dependent, never permanent
  sign rules.
- The desired option outcome is commonly 100% or more; Markeitect generally
  considers approximately 85% the minimum worthwhile realized return. These
  are discretionary management objectives, not proof that an underlying thesis
  was correct and not an automated execution instruction.

Markeitech remains read-only decision support. It does not place trades or
choose account exposure.

## Central Edge

The model observes consequential aggressive participation, remembers where it
occurred, measures whether price rewards or defeats that effort, and maintains
the resulting thesis through confirmation, retests, reloads, targets, recovery,
and invalidation.

The core question is not simply whether the market is bullish or bearish:

> Which side acted aggressively, what result did that effort achieve, and are
> those participants now correctly or incorrectly positioned?

A large green or red print is not inherently bullish or bearish. It reports
aggressive buying at the ask or aggressive selling at the bid. Subsequent price
response determines whether that aggression succeeded, was absorbed, failed,
or became trapped.

Direction is therefore often an output of a participant interaction rather
than a prerequisite imposed before the interaction occurs.

## Operating Priors

Market price spends much of its time balancing, rotating, and testing
liquidity. Sustained directional auctions occupy less time and can be driven by
strong catalysts whose public explanation arrives too late for an ideal entry.

This creates a useful but defeasible prior:

- aggressive activity often fails to earn sustained price progress;
- counterparties may absorb obvious aggressive orders;
- repeated failed effort can expose participants who are vulnerable to a move
  against them;
- genuine initiative must still be respected when aggression receives clear
  displacement, acceptance, and follow-through.

The model is neither permanently contrarian nor a trend follower. It defaults
to observing the result of aggression. It trades against failed initiative and
may trade with successful initiative.

"Market manipulation" is useful Markeitect shorthand for liquidity behavior
that exposes badly positioned participants. The system must not claim to know
the identity or intent of a market maker, institution, fund, hedger, liquidator,
or individual trader. It only claims observable activity and response.

## Observable Vocabulary

### Aggressive Trade

A trade classified at or through the ask is aggressive buying. A trade
classified at or through the bid is aggressive selling. Inside-spread inference
must retain its method and fidelity.

### Large Trade And Aggressive Burst

A large trade is one classified trade meeting an instrument-specific threshold.
Initial manual thresholds are:

- NQ: 40 contracts
- ES: 120 contracts

An aggressive burst is accumulated same-side activity in a short time and
price neighborhood. It may represent one split order or several participants;
it must not be mislabeled as one whale. OFS settings should be captured as
research reference. Thresholds remain configurable and later measurable by
instrument, session, volatility, trade pace, percentile, and outcome.

The Tradovate whale scanner is a useful visual reference. In inference mode it
compares cumulative bid/ask volume-at-price snapshots and permits nearby
positive deltas at the same tick to accumulate across a small snapshot window.
Its bubbles represent inferred aggressive bursts, not proven participant
identity.

### Participant Anchor

A consequential aggressive trade or burst establishes price memory containing:

- instrument, side, price or narrow price band, size, and timestamps;
- individual-print versus accumulated-burst provenance;
- nearby auction locations and current market state;
- subsequent favorable and adverse price response;
- later holds, losses, reclaims, retests, and renewed activity.

Participant anchors survive the appearance of another nearby analytical level.
The question "who acted here, and did they win?" remains relevant on later
retests.

### Delta And CVD

Delta is aggressive buy volume minus aggressive sell volume over an explicit
window. CVD is the cumulative path of that delta under an explicit reset policy.

Markeitect's eyes focus primarily on the CVD path visible in OFS. Code should
also measure evidence that is difficult for a human to track simultaneously:

- per-bar and rolling delta;
- CVD level, slope, acceleration, deceleration, and reversal;
- price change versus delta/CVD change;
- new price extremes without corresponding CVD extremes;
- new CVD extremes without corresponding price progress;
- repeated aggression and total size by price band;
- favorable and adverse excursion after aggression;
- time, trade count, volume, and volatility required to obtain price progress.

Every calculation retains source coverage, unknown volume, session/reset
identity, and fidelity.

### Effort And Result

Effort is observable aggressive participation. Result is the price progress,
holding, and acceptance obtained by that participation. Their relationship is
the model's primary evidence.

- High effort with proportional progress suggests successful initiative.
- High effort with little progress suggests absorption or inefficiency.
- Repeated effort with decreasing progress strengthens a failure hypothesis.
- Movement against the aggressive side suggests a developing trap.
- Holding beyond the participant anchor and failed reclaim strengthen trap
  confirmation.

### Interaction States

Current working states are descriptive observations, not final calibrated
thresholds:

- `PENDING`: consequential participation has appeared; outcome is unresolved.
- `FOLLOWING_THROUGH`: effort is receiving directional price progress.
- `ABSORBED`: substantial effort receives little progress at the observed area.
- `FAILING`: price begins moving against the aggressive side.
- `TRAPPED`: price has displaced and held against the aggressive side or a
  reclaim attempt has failed.
- `RECOVERED`: participants regain their anchor and receive renewed progress.

Exhaustion is distinct from absorption. It describes disappearing or depleted
aggression and does not by itself prove that a counterparty absorbed size.

### Rejection And Acceptance

A wick is evidence of traversal and response, not sufficient proof by itself.
Rejection strengthens when price departs an area and cannot immediately return.
Acceptance strengthens through time, volume, repeated trade, and successful
holding beyond an area. The exact thresholds remain research questions.

## Four Basic Participant Outcomes

| Location | Aggression | Failed outcome | Working thesis |
| --- | --- | --- | --- |
| High | Buyers | Cannot advance; price falls below them | Trapped buyers, Short |
| High | Sellers | Price absorbs and rises above them | Trapped sellers, Long continuation |
| Low | Sellers | Cannot extend; price reclaims above them | Trapped sellers, Long |
| Low | Buyers | Bounce fails; price falls below them | Trapped buyers, Short continuation |

The matrix is descriptive, not exhaustive. Large buyers at a low may win and
produce a valid rejection, as shown in the 2026-07-21 Tradovate reference. A
red bubble at the same low followed by price reclaiming above it would instead
support a trapped-seller interpretation.

## Auction Map

Aggression matters most when it occurs at a consequential auction location.
The current map includes:

- session, prior-session, named-session, and composite profiles;
- POC, developing POC, VAH, VAL, HVNs, LVNs, and low-volume paths;
- support/resistance zones across useful timeframes;
- untouched gaps, especially ES/SPX gaps;
- fair value gaps and their state;
- VWAP and selected EMAs;
- opening-range Fibonacci levels;
- gap Fibonacci levels;
- daily and higher-timeframe structure;
- prior participant anchors and unresolved traps.

Untouched gaps are especially important because the market has not yet auctioned
through them. Gap and ORB Fibonacci levels complement the ordinary auction map.

No location is automatically Long or Short. The location tells the model where
an interaction matters and where price may travel next. Participant outcome
determines the trade thesis.

### Auction Destinations

Targets arise from market structure rather than an arbitrary reward multiple.
Potential destinations include:

- the next LVN boundary or low-volume path;
- the next HVN or accepted-value area;
- POC, VAH, VAL, VWAP, gap boundary, or gap fill;
- support/resistance and Fibonacci levels;
- prior extremes and opening ranges;
- participant anchors likely to attract a retest or forced exit.

A low-volume path is an opportunity for efficient travel, not a promise. A
near destination can be reached while a farther destination remains conditional
on acceptance through the first area.

## Market State

The working market states are:

- balance or rotation;
- directional initiative or expansion;
- transition between balance and initiative;
- failed breakout or failed auction;
- catalyst/news displacement whose cause may be unknown in real time.

Trend labels, EMA structure, profile development, range behavior, and volatility
help characterize state. They do not override direct evidence that participants
are succeeding or failing.

## Cross-Market Context

### NQ And ES

NQ and ES must be observed together at trade-level fidelity for this model.
Their relationship can show:

- directional coherence;
- leader and laggard behavior;
- one index exposing the other's false move;
- two-sided aggression and poor directional efficiency;
- resolution after disagreement.

"Confused participants" is valid operator shorthand for large two-sided
aggression with weak displacement and no sustained control. The system should
describe those observations rather than asserting participant psychology.

### VIX, CL, SOXL, And Session Leader

VIX, CL, SOXL, and a session-selected market-moving equity can lead, confirm,
contradict, or remain irrelevant. Examples include VIX and CL rising while
indices weaken, or SOXL breaking before NQ. None is a permanent directional
rule. Context must retain timing, freshness, relative movement, and the market
regime in which the relationship was observed.

Context can:

- increase or decrease conviction;
- move a scenario from interesting to Armed;
- help select between alternate branches;
- justify waiting for confirmation;
- support holding or reloading;
- warn that a thesis is losing coherence.

It must not manufacture a setup without an underlying auction interaction.

## Scenario And Thesis Model

### Armed

Armed means the market has entered a consequential decision state and the
conditions that resolve it into one or more trade branches are known.

An Armed state may retain:

- a preferred thesis;
- an alternate thesis;
- participant anchors;
- relevant auction locations;
- expected confirming and contradicting observations;
- conditional targets and invalidation evidence.

Armed does not require false certainty. It may begin when a large participant
appears at a meaningful location and Markeitect starts watching whether that
participant succeeds.

### Triggered

Triggered means enough observable evidence has resolved a scenario branch to
justify a discretionary trade alert. Entry timing varies by setup and option
expression. Waiting for complete confirmation is often too late for an ideal ATM
entry, while later confirmation may still support an OTM entry, reload, retest,
continuation, hold decision, or future context.

Potential trigger evidence includes:

- repeated aggression with diminishing price result;
- movement and holding against a participant anchor;
- CVD failing to confirm aggression or reversing against it;
- opposing initiative with price and CVD follow-through;
- a failed reclaim or retest of the participant area;
- NQ/ES disagreement resolving coherently;
- VIX, CL, SOXL, or the session leader resolving a scenario branch;
- acceptance/rejection at the relevant auction location.

No single item is yet a universal requirement.

### Reload And Continuation

A reload is a new entry opportunity inside an existing thesis, not a replacement
signal. Common examples include:

- price returns to a trapped-participant area and fails to reclaim it;
- a POC or other decision area is retested and rejects again;
- NQ/ES disagreement resolves in the thesis direction;
- initial failure evidence receives later initiative follow-through;
- a broken auction destination accepts and opens the next path.

Late confirmation is retained as market memory even when no immediate entry is
desirable.

### Invalidation And Reversal

The strongest current invalidation evidence is aggression receiving genuine
follow-through in its original direction. Additional evidence can include:

- reclaim and acceptance beyond the participant anchor;
- renewed same-side aggression producing displacement;
- price and CVD returning to directional confirmation;
- cross-market context reversing or becoming decisively incoherent;
- acceptance through the location supporting the thesis;
- failure to progress before a still-uncalibrated time/observation boundary.

Invalidation of one branch may activate an explicitly retained alternate branch.
It does not automatically prove a reverse trade.

## Observed Examples

### Successful Buyer At A Low

The Tradovate NQ reference shows a large green aggressive-buy burst near a low
wick after a decline. Price initially responds upward. The buyer won the
immediate battle; the bubble is not trapped-buyer evidence. A seller burst at
that low followed by price reclaiming above it would be a trapped-seller
candidate.

### NQ Buyers Fail With Delta Non-Confirmation

The OFS recording shows NQ rising toward a local high, a large green burst near
the high, little subsequent upside, additional green aggression as price loses
ground, and CVD/delta deterioration. Price then moves materially lower. The
sequence is failed buy effort followed by adverse displacement, not merely a
green bubble to fade.

### ES POC Failure And Downside Initiative

On 2026-07-21 ES reached approximately 7520-7521 POC and a large aggressive
buyer appeared. This Armed a decision state. Price moved below the buyer; a
large aggressive seller appeared; CVD dropped with price while VIX and CL were
climbing. The short branch Triggered through buyer failure plus successful sell
initiative. The profile identified approximately 7516 as the first destination
and approximately 7500 as a conditional destination after a break.

### ES POC Retest And Reload

ES later returned toward POC while NQ showed large buying and selling with weak
directional efficiency. ES remained the clearer leader. The existing short
thesis Armed again for reload. Short resolution conditions included a new large
buyer failing, NQ losing approximately 29110, or clear ES POC rejection. The
alternate Long branch required VIX to fall, ES to break and accept above POC,
and NQ to clear approximately 29130.

The market resolved Short: NQ broke 29110 toward 29097 with a sharp CVD drop,
ES extended through 7516, additional ES buying failed to lift price, and VIX
continued higher. This was one persistent thesis with initial entry, retest,
reload, conviction escalation, and continuation, not several unrelated signals.

## Options Expression And Risk Boundary

The underlying auction produces the thesis. The option expresses it.

- Earlier, less-confirmed entries may favor different moneyness than later
  confirmed or retest entries.
- A later retest with nearby invalidation may make ATM exposure attractive.
- Strong directional days may support farther OTM SPX contracts.
- Option return, spread, liquidity, implied volatility, time decay, and strike
  selection eventually require their own evidence.

Setup confidence, contract selection, and account exposure are separate
decisions. Markeitech may describe maximum observed conviction. It must never
translate that phrase into "full port," automated sizing, or execution.

## ML And Calibration

ML is expected to help the system do more than a human can watch simultaneously,
but it follows honest observation and labeling.

Potential optimization questions include:

- what constitutes large activity by instrument, session, volatility, and
  recent trade distribution;
- which effort/result windows best distinguish follow-through from absorption;
- how long participant anchors remain useful;
- which cross-market relationships are relevant in a given regime;
- which combinations improve early entry, reload quality, destination reach,
  and invalidation speed;
- how option expression changes with confirmation latency and expected path.

ML must consume timestamp-correct features, preserve raw evidence, avoid future
leakage, and produce calibrated ranking or probability rather than retroactively
changing what was observed. Human examples guide labels, but no legend or prior
model is copied as unquestioned truth.

## Current Unknowns

These questions remain deliberately open for examples and measurement:

- exact windows and thresholds for absorption, failure, trapping, acceptance,
  recovery, and exhaustion;
- whether Armed is directional or branch-neutral in each setup family;
- how much adverse movement or time confirms that a participant is trapped;
- how individual prints and bursts should combine across nearby prices;
- CVD reset, rolling windows, and normalization by session;
- location hierarchy, freshness, width, and interaction with participant size;
- retest and reload timing;
- when cross-market disagreement is useful versus ordinary noise;
- target priority when multiple auction destinations overlap;
- option contract and management rules;
- distinction between an informative late event and an actionable late entry.

Unknown does not mean blocked. The observation layer should retain enough
evidence to answer these questions without rewriting history.

## Non-Negotiable Model Rules

1. Aggression color is not Direction.
2. Participant outcome matters more than an isolated print.
3. Follow-through can validate initiative; failure can expose a trap.
4. Locations frame interactions but do not dictate Long or Short.
5. Participant anchors and theses persist through retests.
6. A new level does not erase the existing auction story.
7. NQ and ES order flow are both first-class evidence.
8. Context relationships are conditional and time-sensitive.
9. Late evidence remains useful.
10. Raw facts, inference, and discretionary interpretation remain distinguishable.
11. No model receives execution authority.
12. Markeitect has the final call.
