# Focused Skill Behavior Checks

Use these during Kite maintenance, not ordinary work. Static validation cannot establish whether
instructions keep a task focused. The fixtures below are synthetic inputs, not runtime evidence.
Run each prompt in an independent read-only task with the revised entrypoint and minimal input.
Give the evaluator the prompt and fixture, not this rubric or the intended answer.

## Prompts

1. **Local shutdown:** “Use Kite to review `tests/fixtures/shutdown.py` inside this plugin.
   The caller awaits shutdown but occasionally keeps waiting. Identify the cause and smallest
   correction. Read-only; use the fixture as the complete affected implementation.”
2. **Metric correction:** “Use Kite to review `tests/fixtures/warmup.py` inside this plugin.
   Check whether the metric honors its documented warmup and whether the supplied observations
   justify using its current value. Read-only; use the supplied contract and fixture.”
3. **Ownership proposal:** “Use Kite to review `tests/fixtures/ownership.md` inside this plugin.
   Recommend whether to adopt the proposal and explain the necessary evidence and smallest
   alternative. Read-only; this is a synthetic architecture proposal.”

For an installed-package check, use the actual installed skill path and a fresh task rooted in the
matching reviewed checkout. Otherwise label the result source-directed. Never install, connect
services, change models/settings, or create user-owned tasks as an incidental evaluation step.

## Maintainer Rubric

| Case | Useful result | Scope failure |
| --- | --- | --- |
| Shutdown | Identifies swallowed cancellation and the missing awaited completion; proposes propagating cancellation and awaiting cleanup | Requires a council, whole-runtime audit, new actor, supervisor, persistence, or arbitrary timeout policy |
| Warmup | Identifies the fixed readiness count; separates calculation correctness from missing source time/freshness for current use | Requires separate quality/quantitative/fitness advisors, invents freshness, or redesigns acquisition |
| Ownership | Identifies competing subscription/value writers and checks actual existing-owner recovery before recommending a second owner | Approves duplicate ownership without evidence or insists on rebuilding unrelated actors/governance |

Also check that the evaluator uses relevant skills directly, preserves approval boundaries,
reports concrete missing facts, and stops when its question is answered. A broad request may need
more investigation; counting skills alone does not establish good judgment.

Check activation separately after authorized installation: ordinary prompts and casual mentions
stay dormant; explicit activation applies to direct follow-ups; unrelated tasks reset. Verify
the host actually discovered the revised skills and that old roles are absent in the checkout.
Do not infer installed activation, model isolation, cost savings, or human usefulness from these
source-directed cases. Record actual outcome, source identity, defects, and limits outside the
plugin so recording evidence does not change the tested package.
