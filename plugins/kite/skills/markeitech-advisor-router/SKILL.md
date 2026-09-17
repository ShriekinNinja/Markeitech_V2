---
name: markeitech-advisor-router
description: Explicitly activate Kite and select focused Markeitech skills for the current task. Use skills directly; independent review is optional. A casual mention of Kite does not activate it.
---

# Kite Focused Skills

The existing command remains compatible. Kite is a skill library used by the primary agent.
Activate only when the user selects Kite or explicitly invokes this skill. Direct follow-ups
remain active; a new or unrelated task starts in normal Codex. A directly invoked domain skill
applies only to that question. Installation and casual discussion do not activate Kite.

## Work On The Requested Outcome

1. Use the repository authority and current branch/worktree context. Inspect the affected code,
   contract, and nearby tests. Reuse evidence already established in this task unless its inputs
   changed or its freshness is material.
2. State the smallest outcome and relevant uncertainty. Handle ordinary edits directly. If domain
   guidance helps, use [the skill index](references/skill-index.md) to select the relevant entrypoint
   and read it yourself. The user need not choose skills. Do not load every skill or reference.
3. Investigate only checks that can change this result. Source quality, numerical correctness,
   domain meaning, and fitness for a named consumer are distinct checks that one agent can do.
   No separate advisor disposition, model allocation, dispatch record, or dependency graph is needed.
4. Expand the investigation only for an observed defect, conflicting authority, or missing fact
   with a concrete effect on the requested result. Explain that connection. Keep unrelated
   improvement suggestions outside the implementation scope; do not make them prerequisites.
5. Make the smallest authorized correction and run relevant checks. Finish once the outcome is
   supported. Report the result, evidence, material limits, and any actual blocker. A full audit,
   exhaustive matrix, or architecture redesign belongs only to a request that needs that breadth.

For a new framework capability or replacement, inspect the relevant Nautilus alternatives before
custom work. A fix within an accepted design needs only the exact affected framework contract.
Security and vendor-use checks apply when a trust boundary, permitted use, or concrete risk changes;
touching an existing surface alone does not reopen every adjacent decision.

## Optional Independent Review

Default to no delegation. When an independent check would materially improve confidence, name
one question and, if permitted by the user and host, use one read-only reviewer with relevant
skills and raw evidence. This skill permits that bounded review; it does not require it. Inherit
the task model/effort unless the user specifies otherwise. Do not call retired custom roles.

Give the reviewer the task, scope, relevant source paths, and allowed checks without the intended
answer. The reviewer must not edit, delegate, connect services, access credentials, or make project
decisions. Assess its findings before integrating them. A broader multi-agent review needs an
explicit user request. Reuse the same reviewer for affected follow-ups instead of starting a chain.

If review is unavailable, report the missing independent check and continue work supported by
direct evidence. Missing evidence or authorization still blocks the affected conclusion; never
substitute confidence for facts. Do not create new roles or adjust host settings to make work fit.

## Evidence And Authority

Keep provider truth, installed framework behavior, source quality, formula validity, and intended
use distinct. Preserve unknowns and upstream limitations. State missing facts directly rather
than requiring an advisor to exist. Consult current primary sources for unstable claims.

Skills do not grant approval, execution authority, service access, or legal permission. Keep the
repository's no-order-action boundary, secret handling, Markeitect-owned live acceptance, scoped
PR workflow, and approval gates. A declared read-only review is not proof of technical isolation.

Behavioral evaluation belongs to plugin maintenance, not every task. See
[behavior checks](references/behavior-checks.md) when changing this workflow.
