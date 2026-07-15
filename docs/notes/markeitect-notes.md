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
