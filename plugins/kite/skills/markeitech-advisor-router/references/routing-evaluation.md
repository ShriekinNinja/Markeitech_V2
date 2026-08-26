# Advisor Council Routing Evaluation Index

The former combined design-and-results matrix was split on 2026-08-26 so expected behavior cannot
be mistaken for observed installed behavior.

- Canonical council structure and role boundaries:
  [`council-policy.toml`](council-policy.toml)
- Human-readable ownership guide:
  [`council-routing-contracts.md`](council-routing-contracts.md)
- Expected route fixtures and complete 20-role coverage:
  [`routing-cases.toml`](routing-cases.toml)
- Dated observed results and acceptance levels:
  [`routing-acceptance.md`](routing-acceptance.md)

The original cases `P1-P2`, `S1-S5`, `M1-M4`, `A1-A2`, `X1-X2`, `B1-B9`, and `G1-G2` are
preserved as typed in-Kite fixtures. `D1` proves primary Kite must not bypass a custom role by
loading its specialist skill directly. `E1-E9` cover fresh-session dormancy, explicit Kite
activation, direct named-specialist override without Kite activation, task continuity, and reset
behavior.

Use `STATIC_PASS` only for offline repository invariants. Use `DORMANCY_PASS`, `INVOCATION_PASS`,
`END_TO_END_PASS`, or `ISOLATION_PASS` only for corresponding fresh-task observations recorded
against exact source, installed plugin, policy, and Codex versions.
