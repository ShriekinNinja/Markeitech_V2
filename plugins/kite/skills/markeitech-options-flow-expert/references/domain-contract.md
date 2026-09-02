# Vendor Options Flow Contract

The minimum immutable artifact identity is byte hash, filename/export ID, vendor/product/version,
download/export UTC time, source timezone, requested interval, all filters/defaults, account/user
context when terms depend on it, schema/column mapping, row count, license/terms version and
transformation version. Preserve original row identity and every parent row in aggregates.

For each row require exact option identity, execution time, price/size, exchange or scope if known,
conditions/corrections if supplied, contemporaneous bid/ask and quote time if supplied, underlying
price/time, vendor type/side/sentiment/multi-leg fields, volume/OI with as-of dates, IV/Greeks with
source/time, and explicit unknowns.

Classify price location only under a named contemporaneous quote policy; preserve inside-spread,
locked/crossed, stale and missing-quote cases. Aggregate premium only with multiplier, currency,
signed/unsigned meaning and deduplication/grouping policy. Repeated prints may be one parent order,
unrelated activity, complex legs or reporting effects; treat grouping as inference unless the
source supplies authoritative identity.

Vendor sweep/block rules, thresholds, same-side burst windows, quote age, aggregation keys,
premium bounds and confidence are typed, scoped, bounded, versioned policy or vendor-reported
semantics. Never rewrite a vendor label as exchange truth.
