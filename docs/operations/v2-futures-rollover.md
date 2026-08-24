# V2 Futures Contract Rollover

**Status:** Current manual operating procedure

## Purpose

Markeitech uses explicit dated futures contracts. It does not silently substitute, infer, or roll
contracts. This procedure keeps provider identity, historical dependencies, analytical lineage,
and operator expectations aligned when the configured contract changes.

The current tracked baseline uses:

- `ESU6.CME`, `NQU6.CME`, and `YMU6.CBOT`: September 2026 equity-index futures; and
- `CLV6.NYMEX`: October 2026 crude-oil futures.

Month code `U` means September; month code `V` means October. Read each configured symbol's month
code directly rather than inferring its expiry month from another instrument or from a watchlist
label.

## Ownership And Gate

Markeitect owns the rollover decision. Automatic rollover, continuous-contract substitution, and
liquidity-based runtime switching remain unimplemented and unapproved.

Begin a rollover review when exchange/provider contract lifecycle information or observed market
liquidity indicates that the configured contract may no longer be the intended evidence source.
Do not encode an unverified calendar date in this procedure. Verify the exact next contract and
its lifecycle from current exchange or provider information for that instrument.

## Review Checklist

1. Identify the intended next dated contract and verify its root, month/year, venue, currency,
   multiplier, trading hours, and provider instrument identity.
2. Confirm that the new contract is the desired evidence source. Record any basis, volume, or
   liquidity difference that affects continuity with the previous contract.
3. Stop the connected runtime before changing tracked or local provider IDs.
4. Update every configuration-owned reference to the dated contract. Do not add hidden aliases or
   code constants.
5. Run configuration and offline validation. Confirm that all analytical profiles, calendars,
   historical requirements, entity bindings, and resource policies still resolve for the new ID.
6. With Markeitect's explicit approval, run connected acceptance and verify:
   - instrument resolution and contract metadata;
   - quote and configured bar activity;
   - historical dependency timestamps, timezone boundary, and requested coverage;
   - session mapping and evidence-health behavior;
   - shared subscription ownership and clean release;
   - PostgreSQL operational lifecycle reconciliation; and
   - clean shutdown without orphaned demand.
7. Compare a small set of provider observations with an independent operator reference. Record
   any contract-basis or continuity caveat instead of normalizing it away.
8. Update `docs/current-status.md` and any tracked example IDs only after the connected evidence is
   reviewed. Commit through the normal local-review and PR process.

## Failure And Rollback

If resolution, entitlement, history, session mapping, or analytical applicability fails, keep the
failure explicit and return to the last reviewed dated contract only when that contract is still a
valid live evidence source. Do not use a continuous future, nearest-expiry guess, or alternate
venue as an invisible fallback.

A rollover is complete only when configuration, runtime evidence, operational audit, and current
documentation all name the same dated contract.
