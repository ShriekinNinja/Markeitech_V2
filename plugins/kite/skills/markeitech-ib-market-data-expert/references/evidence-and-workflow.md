# Evidence And Workflow

## Precedence And Freshness

Tracked Markeitech authority governs product and safety boundaries. Current official IB
documentation governs IB capability, requests, limits, and provider failures. Current exchange
schedules and dated notices govern venue sessions; IANA tzdb governs civil-time transitions.
Exact connected observations establish only their recorded account, contract, request, session,
version, and run. Local tests establish offline behavior, not provider delivery.

Deprecated docs, examples, public Q&A, third-party libraries, public skills, and memory are
discovery aids only. Preserve material conflicts and stop before a consequential recommendation.

For each time-sensitive source record title, direct URL, publisher, access date, displayed
version/update date, governed API/product, caveat, and whether it refreshed successfully.

## Measured-Evidence Envelope

Connected evidence is admissible only with applicable metadata:

- run ID and UTC observation time;
- TWS/IB Gateway, TWS API, Nautilus, and adapter versions/configuration;
- paper/live mode and non-secret username/entitlement context;
- exact `conId`, symbol, security type, exchange/primary exchange, currency, expiry, trading class,
  multiplier, and local symbol;
- request/method ID, fields or `whatToShow`, bounds/duration, bar size, RTH policy, market-data
  type, and timestamp format/timezone;
- session, exchange timezone, trade date, holiday/early-close status, and UTC interval; and
- returned count/times, empty/partial status, error codes/messages, retries, latency,
  cancellation/completion, and relevant budgets.

Missing metadata lowers the claim to inference or unknown. Never reconstruct it from current
configuration or a nearby run.

## Review Sequence

1. Frame the decision and exclusions.
2. Read tracked authority; inspect local identity/configuration.
3. Refresh official IB and exchange sources broadly, then exact pages.
4. Build contract/entitlement, request/resource, and timestamp/session censuses.
5. Classify provider outcomes using positive evidence.
6. Compare measurements only within their evidence envelope.
7. Fill the provider-truth matrix.
8. Obtain the separate Nautilus handoff if runtime use is proposed.
9. State configuration candidates, acceptance evidence, gates, and unknowns.

Prefer exact IB error codes and full sanitized messages plus request context. Do not log credentials,
account secrets, invoices, or raw licensed data.

## Acceptance Ladder

- Current primary documentation.
- Offline local contract/configuration verification.
- Pinned adapter verification by `markeitech_nautilus_advisor`.
- Markeitect-authorized, exact read-only connected check.
- Exact session/holiday/DST/closed-market boundary observation when material.
- Operational reconciliation of lifecycle, failure isolation, resources, audit, and shutdown.

Never use one rung as proof of another.
