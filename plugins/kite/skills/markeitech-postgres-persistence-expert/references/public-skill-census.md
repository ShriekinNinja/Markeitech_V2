# Public Agent-Skill Census

Research snapshot: 2026-08-25. External skills were inspected only for reusable workflow and
packaging ideas. PostgreSQL facts come from primary sources and local evidence. No external prompt
text, SQL script, or executable asset was copied into this candidate.

| Source | Version or commit | License | Ideas adopted | Ideas rejected or compatibility concerns |
| --- | --- | --- | --- | --- |
| [ruicore/codex-skills `database-access-audit`](https://github.com/ruicore/codex-skills/blob/b6bed4123301820a19a3604915be8cc8b5c7757c/skills/database-access-audit/SKILL.md) | `b6bed4123301820a19a3604915be8cc8b5c7757c` (2026-08-25) | Repository Apache-2.0 | Read-only scope by default; discover project-specific persistence primitives; distinguish statements, transactions, connections and round trips; inspect constraints/indexes/rowcount; disprove candidates through an independent evidence path | Stack-neutral batch-access audit is not a PostgreSQL persistence authority; its broad application/API security scope, priority examples, and fix mode were not copied or treated as Markeitech doctrine |
| [Supabase `supabase-postgres-best-practices`](https://github.com/supabase/agent-skills/blob/8331f910845103c08d51f6ca1d86ebb7d1f745e3/skills/supabase-postgres-best-practices/SKILL.md) | repository commit `8331f910845103c08d51f6ca1d86ebb7d1f745e3`; skill release `1.6.0` | MIT | Small routing entrypoint with on-demand references; separate query, schema, concurrency, security, monitoring and advanced surfaces; prioritize integrity before tuning | Supabase/Auth/RLS/platform assumptions do not match Markeitech's local service; generic numeric performance rules and example SQL are not imported; no external dependency is added |
| [OpenAI `render-debug`](https://github.com/openai/plugins/blob/11c74d6ba24d3a6d48f54a194cd00ef3beea18f9/plugins/render/skills/render-debug/SKILL.md) | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` (2026-07-13 snapshot) | Skill frontmatter declares MIT | Symptom-to-evidence triage, logs/metrics/database state separation, progressive troubleshooting references, and verification after diagnosis | Render MCP, deployment, environment mutation, and hosted-Postgres commands are incompatible with this read-only local candidate and were rejected |
| [IldarMinaev `qubership-postgresql-troubleshooting`](https://github.com/IldarMinaev/troubleshooting-skill/blob/680d88fb47f020e349c3d584c483c2f433cfe3fe/SKILL.md) | `680d88fb47f020e349c3d584c483c2f433cfe3fe` (2026-04-08) | No repository license detected; no `LICENSE` at the inspected commit | Census value only: it demonstrates symptom-specific routing across health, performance, storage, backups, connections, logs, and monitoring | No material adopted. Kubernetes, Patroni, PgBouncer, pgBackRest, DBAAS, cluster exec, credential retrieval, and bundled SQL scripts do not match Markeitech's local Docker boundary; absent license prevents reuse |
| [Supabase `safe-sql-execution`](https://github.com/supabase/supabase/blob/0dd7cca4faeaa7b0cbb58a086c1381d908db1174/.claude/skills/safe-sql-execution/SKILL.md) | `0dd7cca4faeaa7b0cbb58a086c1381d908db1174` (2026-08-25) | Repository Apache-2.0; no content copied | Reinforced that SQL provenance, value binding, identifier handling, and explicit execution authority are separate review questions | Supabase Studio's proven-authorship types and browser/user SQL model are product-specific; no wording, types, or implementation pattern adopted |

## Applied Structure

- One plugin-local, project-scoped skill directory containing `SKILL.md`, `agents/openai.yaml`, and
  four routed references.
- One matching project-scoped read-only custom advisor definition.
- A discriminating description with explicit raw-market-data, Nautilus, runtime, infrastructure,
  security, and trading boundaries.
- No scripts or SQL assets: deterministic helpers would imply operations this read-only candidate
  must not perform.
- Router integration delegates consequential PostgreSQL mechanics to the project custom role; no
  manager, marketplace, runtime, database, or infrastructure integration is added.

## License Compatibility Conclusion

Only abstract review structure and decision criteria were used. No external expressive content,
SQL, scripts, templates, or assets were incorporated, so Apache-2.0, MIT, missing-license, and
repository-specific material do not contaminate Markeitech's proprietary candidate. Any future
adoption of external text or executable material requires a new path-level license and attribution
review.
