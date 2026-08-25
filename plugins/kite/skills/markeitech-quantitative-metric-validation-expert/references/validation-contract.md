# Quantitative Metric Validation Contract

Freeze separate claims for definition correctness, implementation correctness, reference parity,
causal validity, evidence fidelity, numerical robustness, operational readiness and statistical
validity. Trading usefulness is outside this role.

For every metric record formula/order/ties, inputs and price basis, instrument/session/version,
units, event/availability/calculation times, window anchor/ends/minimum coverage, bounded/recursive/
path-dependent warmup, missing/late/revision rules, dtype/precision/domain/tolerance, output bounds,
health/fidelity/lineage and lifecycle.

Use hand-computed micro-fixtures, invariants/properties, metamorphic checks, an independent
differential or high-precision oracle, warmup convergence, future-only perturbation, chunk/restart
equivalence, and gap/revision cases as material. Align formula variant, inputs, aggregation,
session, sample start, seeding, dtype, missingness and version before claiming parity.

Validate aggregation algebra explicitly. Detect invalid cross-grain aggregation, including
average-of-averages without defensible weights, duplicated values introduced by joins, incompatible
denominators, and aggregation across different session, instrument, resolution, or availability-time
populations. Data quality owns the grain and cardinality facts; this role owns whether the stated
mathematics remains valid when those facts are applied.

Periods, decay, seeds, sample floors, coverage, baseline population, clipping, epsilon/tolerance,
missing-value and revision rules are typed, scoped, bounded, versioned policy candidates.
