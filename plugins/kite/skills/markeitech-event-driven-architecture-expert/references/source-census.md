# Event-Driven Architecture Source Census

Last researched: 2026-08-25. Refresh versioned and `current` sources before a consequential design
or audit. These sources inform questions and failure analysis; they do not override tracked
Markeitech authority or prove the installed NautilusTrader contract.

## Tracked Markeitech Authority And Local Evidence

Read only the documents relevant to the task, after the mandatory repository entry authorities:

- `docs/architecture/runtime-foundation.md` — native-bus, system-health, ownership, projection,
  delivery, bounded work, persistence, and failure-isolation boundaries.
- `docs/architecture/market-data-and-acquisition.md` — one subscription/request owner, native data
  path, shared demand, correlation, retry/cancellation, readiness, and transient raw evidence.
- `docs/architecture/deterministic-evidence-contracts.md` — bounded projection, revision,
  conflict, staleness, recovery, and evidence lifecycle contracts.
- `docs/roadmap/sir-loke-v1-delivery-plan.md` — accepted destination for product-channel contracts,
  independent path health, scoped reliability, recovery, and resource gates.
- Relevant implementation and tests under `src/markeitech/` and `tests/` — final evidence of
  current local behavior where documents lag.

Historical documents must not be promoted to current truth. Use `docs/current-status.md` to resolve
their status and supersession.

## Primary Standards And Official Documentation

### Akka message delivery reliability

- URL: https://doc.akka.io/libraries/akka-core/current/general/message-delivery-reliability.html
- Observed version/channel: current Akka Core documentation; page examples identified Akka 2.10.21
  on 2026-08-25.
- License/provenance: official Akka documentation; current Akka source distributions use the
  Business Source License 1.1. Consulted as attributed documentation; no text copied.
- Learned: delivery guarantees must name the precise milestone; ordinary sends are not guaranteed;
  per-sender ordering is not global order; stronger delivery needs stable IDs, acknowledgement,
  retry, and receiver duplicate handling.
- Limit: Akka behavior is comparative evidence, not a claim about NautilusTrader.

### Erlang/OTP supervision principles

- URL: https://www.erlang.org/doc/system/sup_princ.html
- Observed version: Erlang/OTP system documentation 29.0.5.
- License/provenance: official Erlang/OTP documentation; Apache License 2.0 project.
- Learned: restart strategy, intensity, and time window jointly define burst and sustained failure;
  nested supervision can multiply restart attempts; shared fate must be chosen deliberately.
- Rejected: importing OTP defaults or numeric examples as Markeitech policy.

### Reactive Streams 1.0.4

- URL: https://github.com/reactive-streams/reactive-streams-jvm
- Version: 1.0.4.
- License: MIT-0.
- Learned: asynchronous stream boundaries require non-blocking demand and subscriber-controlled
  bounds so fast producers cannot force unbounded buffering.
- Limit: it is a stream interoperability specification, not a universal requirement that every
  Markeitech pub/sub channel implement Reactive Streams.

### CNCF CloudEvents

- URLs: https://github.com/cloudevents/spec and
  https://github.com/cloudevents/spec/blob/ce@v1.0.2/cloudevents/spec.md
- Version: 1.0.2 stable; working drafts remain separate.
- License: Apache License 2.0.
- Learned: source-scoped event identity, type/version, subject, time, schema, and extension metadata
  are useful interoperability questions.
- Rejected: replacing accepted Markeitech/Nautilus envelopes with CloudEvents merely for
  uniformity. CloudEvents describes event data; it does not itself prove delivery or processing.

### Apache Kafka producer configuration

- URL: https://kafka.apache.org/42/configuration/producer-configs/
- Version/channel: Apache Kafka 4.2 producer configuration, inspected 2026-08-25. Refresh the
  versioned page before later consequential use.
- License: Apache License 2.0.
- Learned: producer idempotence is conditional on related configuration and addresses a bounded
  producer-to-log scope; retry/concurrency choices can affect ordering.
- Rejected: treating broker producer idempotence as end-to-end exactly-once business processing or
  as a reason to add Kafka.

### AWS transactional outbox guidance

- URL: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- Version/channel: current AWS Prescriptive Guidance, accessed 2026-08-25.
- License/provenance: AWS documentation terms; proprietary documentation consulted with attribution,
  no text copied.
- Learned: a database update plus event notification creates a dual-write failure window; an outbox
  may address atomic recording, but duplicate publication still requires idempotent consumption.
- Rejected: assuming Markeitech needs an outbox, broker, or raw-event store without an approved
  persistence and live-consumer requirement.

## Peer-Reviewed And Institutional Sources

### Lamport, Time, Clocks, and the Ordering of Events

- URL: https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/
- Citation: Leslie Lamport, *Communications of the ACM* 21(7), 1978, pp. 558-565.
- License/provenance: ACM copyright; abstracting with credit permitted. No paper text copied.
- Learned: causal order is a partial order; timestamps can construct an order consistent with
  causality but do not make physical time or log position a universal causal truth.

### Waldo et al., A Note on Distributed Computing

- URL: https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf
- Citation: Jim Waldo, Geoff Wyant, Ann Wollrath, and Sam Kendall, Sun Microsystems Laboratories
  technical report TR-94-29, 1994.
- License/provenance: author-hosted institutional copy; copyright retained, no text copied.
- Learned: latency, concurrency, independent failure, and partial failure prevent remote boundaries
  from being treated as ordinary local calls.

### Helland, Life beyond Distributed Transactions

- URL: https://www.cidrdb.org/cidr2007/papers/cidr07p15.pdf
- Citation: Pat Helland, CIDR 2007 position paper.
- License: Creative Commons Attribution 2.5, as stated in the paper.
- Learned: scalable systems often need explicit message identity, idempotency, and state ownership
  instead of assuming one global transaction.
- Limit: a position paper informs questions; it does not select a Markeitech persistence pattern.

## Freshness And Source Use

- Record access date, exact version/tag/commit when available, and whether a source is stable or a
  working draft.
- Prefer tracked authority and local executable contracts for current Markeitech behavior.
- Prefer official standards, project documentation, and original papers for general claims.
- Separate core transport behavior, adapter/provider delivery, configured policy, and connected
  observations.
- Do not copy source text beyond short attributed excerpts. Paraphrase and link.
- If a primary source is unavailable, label the gap and stop before a conclusion that depends on it.
