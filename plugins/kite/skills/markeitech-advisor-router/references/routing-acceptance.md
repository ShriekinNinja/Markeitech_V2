# Advisor Council Routing Acceptance

This ledger records observed behavior. Expected routes live in
[`routing-cases.toml`](routing-cases.toml); structural policy lives in
[`council-policy.toml`](council-policy.toml). A source validator result is never promoted into an
installed-behavior claim.

## Acceptance Levels

| Level | Meaning |
|---|---|
| `STATIC_PASS` | Repository policy, role, skill, metadata, manifest, dependency, and fixture invariants pass offline. |
| `DORMANCY_PASS` | A fresh or unrelated normal Codex task did not activate Kite, its router, or its advisors. |
| `INVOCATION_PASS` | Explicit Kite activation selected the router and invoked the expected exact custom roles. |
| `END_TO_END_PASS` | Selection, selected-role order, handoffs, stop gates, conflict preservation, and synthesis match the case. |
| `ISOLATION_PASS` | The effective runtime denies unapproved write, MCP, authenticated-session, network, and external-action capabilities at the tool layer. |
| `BLOCKED` | Required evidence, coverage, authority, or safe tool surface was unavailable. |
| `FAIL` | Observed behavior contradicted the declared contract. |

Every observed row records the case, plugin and policy versions, source revision or tree digest,
installed-cache identity, Codex version, effective permission/tool surface, selected roles and
order, unnecessary roles, stop/handoff behavior, sanitized evidence location, and result.

## Current Evidence

| Date | Build | Evidence | Disposition |
|---|---|---|---|
| 2026-08-25 | `0.1.0+codex.20260825124814` | One ordinary request selected the live-agent-governance path without explicit Kite activation. Delegated execution failed because the collaboration target could not be resolved. | Legacy implicit-selection observation; this is contrary to the Phase 1 explicit-activation target and is not an invocation or end-to-end pass. |
| 2026-08-25 | `0.1.0+codex.20260825140114` | Plugin installed and enabled; repository source and installed cache matched byte-for-byte. | Packaging/source identity only. Fresh-task routing remained pending. |
| 2026-08-26 | `0.1.0+codex.20260825140114` | Architecture, governance, and security custom advisors were delegated during the Phase 1 review and returned bounded consultations. The child security context was presented with a workspace-write permission profile despite the advisor's read-only default. | Delegation observed; not a clean routing fixture and not `ISOLATION_PASS`. The runtime tool-isolation claim remains rejected. |
| 2026-08-26 | `0.1.0+codex.20260826131333` | Cache-busted plugin installed and enabled from the local `markeitech` marketplace; installed cache matched repository source byte-for-byte. Dependency-free validation passed, but a fresh task reported `invalid transport` for all 20 custom roles because each disabled PyCharm MCP override omitted its required transport. | `FAIL`. The router could not delegate to ignored roles. Static validation had encoded the same invalid transportless override and therefore did not protect startup compatibility. |
| 2026-08-26 | `0.1.0+codex.20260826132235` | Restored the exact project PyCharm HTTP transport beside `enabled = false` in every custom role. Codex 0.149.1's actual startup/prompt parser loaded the repaired configuration without malformed-role warnings. Dependency-free validation passed for 20 policy entries, 27 in-Kite routing cases, and 9 activation cases; all 19 focused validator tests passed. The cache-busted plugin was installed and its cache matched repository source byte-for-byte. | Startup configuration repair, packaging/source identity, and `STATIC_PASS`. Dormancy, explicit invocation, end-to-end, isolation, redaction, failure, and revocation acceptance remain pending for fresh tasks. |

## Fresh-Task Acceptance Requirements

Issue #39 changes source to council schema 3 with per-consultation allocation. Offline fixtures
exercise defaults, distinct allocations for one role, overrides, unavailable/unsupported pairs,
capability/context conflicts, retry bounds, and requested/effective receipts. This is source
validation only. At the initial source-only checkpoint, no schema-3 package refresh or fresh-task
effective-allocation acceptance had run; the legacy installed package differed from source in
14 files despite a matching version. Current allocation observations and remaining gates are
maintained outside the bundle in the repository
`docs/development/kite-allocation-acceptance.md` and its sanitized JSON record. Keeping run results
outside the bundle avoids changing the package merely to record its own acceptance. Always verify
current byte identity; neither a historical observation nor a matching version establishes it.

For allocation acceptance, follow [resource allocation](resource-allocation.md). Record the actual
router-to-resolver-to-exact-role calls, current host/version and context mode, complete requested
pair, and effective settings from host evidence or an explicit observability limitation. Exercise
two allocations for one unchanged advisor. An echoed model name is not effective-setting proof.

Run only after a separately approved cache-busting install or reinstall:

1. In fresh tasks, prove that ordinary conversation, substantive Markeitech work without explicit
   Kite invocation, and casual mention of Kite remain normal Codex with no Kite skill or role call.
2. Explicitly invoke Kite through the plugin and `$kite:markeitech-advisor-router`; prove that the
   router activates, then exercise no-council, single, ordered multi, unnecessary-advisor rejection,
   missing coverage, Sir Loke boundary, and direct-skill-bypass cases.
3. Prove direct follow-ups remain in Kite mode and an unrelated or fresh task resets to normal Codex.
4. Explicitly invoke one named specialist skill; prove that skill runs as a narrow override while
   Kite mode, the router, and custom advisors remain inactive.
5. Record actual skill and custom-role calls rather than inferring them from prose or final text.
6. Verify advisor MCP exposure is absent unless explicitly allowed.
7. Test harmless platform denial of a repository write under a genuinely read-only parent task;
   do not mutate production or user data.
8. Exercise missing role, source/cache mismatch, timeout, partial output, and tool-policy mismatch;
   each must fail closed without general-knowledge substitution.
9. Use only fake secret canaries and sanitized fixtures for redaction and prompt-injection tests.
10. Keep installation, revocation, and active-thread/cache behavior as separately approved external
   configuration actions.
