# Markeitect Notes

Observations captured during live trading and carried into development review.

## July 13-17, 2026

- Historical last should be up-to-now.
- Volume profile refinement: Stage 4B adds finer NQ/ES bins plus developing 2-session and 5-session composites without changing current-session location semantics. Validate usefulness during live trading.
- TickStrike/aggression indicator.
- Big trades indicator.
- Logs were not usable for humans. Stage 4B now emits an active-first warmup briefing and bounded change-aware live reports; confirm the density during trading before closing this observation.
- On July 14, Direction moved from `+2` to `-1` over roughly 45 minutes and informed a profitable discretionary puts trade. Preserve this as evidence of operator usefulness, not signal validation or a calibration target.
- Location-pattern candidate from the July 15 NQ run: model directional
  acceptance/rejection at value-area boundaries, including short continuation
  on a VAL underside retest and the mirrored long continuation on a VAH topside
  retest. Keep this distinct from the current directional support-at-VAL and
  resistance-at-VAH semantics; define confirmation and invalidation explicitly
  before enabling it.

#### July 15, 2026
- The main system ran remarkably well. the analytics as well. generally speaking the system works fantastic. it capable of helping me trading fs but its too focused on Valentini's signal imho
- Fabio Valentini's singal needs calibration and or pivot. signals were far from helpful. distracting even. ML is guess. suggestions are wellcome
- looking at the rendered chart, too many fvg's and a lot of them overlapping. we need to render a chart with the analytics and review them all.
- rendered chart was not effective for trading. discord maybe upvoted in priority.
- ask for screenshot of my context chart. today proved it's importance with soxl/cl/vix/igv/xlf/xlk/mags/iwm
- delta vs price action along with cvd is high priority now as well. ask for @ofs screenshot for ref
  - "Only 2.50% of volume was classified buy/sell." extremely bad to terrible. must be addressed. counting on it for delta and cvd.
- tracking live price and alerting when stuff happens becomes critical. for example:
  - neering, breaking, rejecting, protecting level, etc..
  - selling / buying pressure increas/decres etc.
  - breaking/following/reaching trends from multiframes
  - etc..

#### July 16, 2026
- Run it steady, trust the evidence, and stay humble. Rock & Roll