# Evidence And Source Discipline

Use this protocol for every consultation. The skill's recorded census is orientation; refresh the
relevant primary sources during the task when behavior or guidance may have changed.

## Source Priority

1. Current tracked Markeitech authority and accepted stage documents.
2. The current checkout, nearby tests, locked environment, exact interpreter build, and public
   runtime signatures.
3. Accepted runtime measurements with provenance and scope.
4. Version-matched Python language/library documentation, typing specification, PEPs, and Python
   Packaging Authority specifications.
5. Maintainer documentation for an already locked third-party dependency.
6. Peer-reviewed or institutionally credible research for measurement methods and failure models.
7. Public skill examples only for packaging inspiration, never as Python-runtime authority.

Do not use a blog, remembered behavior, search snippet, or a newer Python version to override the
current executable contract. Do not infer a third-party extension's concurrency behavior from
CPython documentation.

## Evidence Labels

Use these labels exactly for material claims:

- **Verified fact:** observed in current tracked authority, source, lockfile, interpreter, public
  signature, or a focused deterministic test. Name the artifact and version.
- **Measured evidence:** observed behavior or resource/performance data. Record workload, runtime,
  environment, sample window, units, aggregation, and important confounders.
- **Inference:** a reasoned conclusion from named facts or measurements that was not directly
  observed.
- **Hypothesis:** a falsifiable possible explanation which still needs evidence.
- **Recommendation:** the advisor's proposed action, with tradeoffs, authority gate, and acceptance
  evidence.
- **Unknown:** missing, conflicting, stale, or insufficient evidence. State the smallest safe way to
  resolve it.

Passing tests are verified only for their exercised paths. A sampled CPU value is not a causal
profile. RSS growth is not by itself a Python allocation leak. Queue capacity is not proof of
overload behavior. Type hints are not runtime enforcement. Clean shutdown once is not restart or
late-callback proof.

## Freshness And Provenance

For external sources record URL, publisher, accessed date, target Python version, displayed
revision where available, and whether it matches the local pin. For local measurements record the
commit, configuration identity, Python implementation/build, operating system, workload/session,
start/end times, sampling method, and whether native extensions or connected services participated.

Separate current-pin advice from upgrade-target advice. Never recommend an interpreter or package
upgrade merely because newer documentation offers a convenient facility.

## Measurement Guardrails

- Define the decision and metric before choosing a tool.
- Establish a baseline and a representative workload; include steady-state and lifecycle phases
  when both matter.
- Use multiple runs or a justified observation window and report distribution or variance rather
  than one attractive number.
- Separate wall time, process CPU time, event-loop delay, queue delay, task duration, RSS, Python
  allocations, native allocations, cache growth, and I/O wait.
- Record instrumentation overhead. `cProfile` is deterministic profiling, not a benchmark;
  `tracemalloc` observes traced Python allocations, not total process memory.
- Compare equivalent interpreter builds and configurations. CPython 3.13 free-threaded behavior is
  experimental and must not be assumed from the version number alone.
- Preserve raw evidence long enough for review when policy permits, but do not add persistence or
  retain licensed/provider data without approval.

## Freshness Statement

End substantive advice with the access date, local Python implementation/build and version,
locked project versions inspected, source channel, unavailable or mismatched sources, and connected
or performance behavior that remains unverified.
