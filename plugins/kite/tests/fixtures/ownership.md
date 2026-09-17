# Synthetic Subscription Ownership Proposal

This fixture describes a hypothetical system, not the actual Markeitech runtime.

Accepted contract: Acquisition owns provider subscriptions, reconnects, and the canonical last
price. Watchlist declares demand and projects Acquisition's values. Dashboard consumes that
projection. A display can report stale or unavailable data but cannot calculate a replacement
canonical value. The current recovery path has not been inspected in this exercise.

Observed issue: after a provider disconnect, Dashboard shows its last received price for too long.
The fixture has no trace establishing whether the cause is subscription recovery, missing health
events, or display behavior.

Proposal: give Dashboard another provider connection. If updates stop, it subscribes directly,
reconstructs last price from its own data, and writes that value into Watchlist. Acquisition
continues its original subscription and publishes as before. No reconciliation rule is proposed.

Question: should the proposal be adopted, what evidence matters, and what is the smallest useful
alternative? No code or live provider access is authorized.
