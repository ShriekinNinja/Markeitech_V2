---
name: markeitech-security-tool-boundary-expert
description: Review a specific credential, authentication, permission, tool/MCP, redaction, dependency, or network-boundary change. Trigger on a changed trust boundary or concrete threat.
---

# Security Tool Boundary

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Trace the affected actor, input, secret or capability, destination, and authority check.
- Check least privilege, untrusted input, secret redaction, failure behavior, and revocation where the change affects them.
- Prompt instructions and a declared sandbox are not proof of effective tool isolation; distinguish configured and observed permissions.
- Do not expose secrets or treat this skill as permission to rotate credentials, scan targets, install dependencies, or change external systems.

## Optional References

- [sources.md](references/sources.md) — use for current security or tool-contract evidence.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
