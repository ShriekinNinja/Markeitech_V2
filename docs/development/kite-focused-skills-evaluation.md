# Kite Focused Skills — Issue 63 Evaluation

Date: 2026-09-17. Scope: source-directed, read-only skill evaluation in the issue #63 worktree.
The three independent evaluators received the revised source entrypoint, one realistic request,
and its synthetic input. They did not receive the maintainer rubric, intended answer, other
evaluators' findings, or permission to edit/delegate/connect services. The primary agent reviewed
their returned findings against the supplied fixtures.

These are actual observed source-directed consultations, not installed-plugin activation tests
or Markeitect's usefulness verdict. Evaluator completion and reported checks do not establish
technical isolation. No provider, runtime, market-session, trading, or comparative cost/latency
claim follows from these results.

## Observed Results

| Evaluation | Guidance used | Observed result | Disposition |
| --- | --- | --- | --- |
| `/root/kite_shutdown_evaluation` | Router/index, Python runtime, review protocol and evidence guidance | Identified swallowed cancellation and cleanup-flag polling. Also identified cancellation before first execution as a second hang. Proposed propagating cancellation and awaiting the owned task, without new timeout policy or lifecycle infrastructure. Reported bounded offline reproduction and in-memory checks of started, immediate, and repeated stop. | Meets scoped source rubric |
| `/root/kite_metric_evaluation` | Router/index, quantitative validation, data quality, evidence fitness | Identified readiness fixed at two instead of the configured period, including the period-one failure. Kept calculation correctness separate from absent timestamp/session evidence. Rejected use as a current four-observation mean while identifying the three-number arithmetic average. Reported offline examples and proposed focused boundary checks. | Meets scoped source rubric |
| `/root/kite_ownership_evaluation` | Router/index, architecture boundaries and review protocol | Rejected competing subscription/canonical writers. Preserved the accepted owner, distinguished unknown root cause from the demonstrated ownership conflict, and requested a bounded recovery/health trace. Proposed correction at the failing existing step rather than adopting a second provider path. No runtime check claimed. | Meets scoped source rubric |

All three read the relevant skills directly and returned without requiring a council, allocation
resolver, specialist disposition, role creation, or additional delegation. The ownership answer
was longer than the local-fix answers, consistent with its requested alternatives/evidence scope.
These cases show bounded feasibility; they do not establish behavior for every domain or prompt.

## Source Identity

The versioned package after evaluation is `0.1.0+codex.20260917093153`, 101 files, SHA-256
`a320637badf8e70cb86d0e8b50a125a4c395e5fb5e11a3ac8ea663336845b663`, using
`python3 -B scripts/kite-package.py identity`. The cachebuster was applied after the consultations;
the exercised instructions and fixtures below were unchanged. This record lives outside the
package so recording results does not alter its identity. The reviewed PR commit identifies the
repository instructions and package helper separately.

Paths below are relative to `plugins/kite/`:

| Evaluated input | SHA-256 |
| --- | --- |
| `skills/markeitech-advisor-router/SKILL.md` | `a404fbd52fa7d7031cc96f45e9593b343b02852d9ed536614c4e31e6f19c21f0` |
| `skills/markeitech-advisor-router/references/skill-index.md` | `afc3900021818d882c95c2f1c8271926992b4fa6a506a5f28594c38036a0df0c` |
| `skills/markeitech-python-runtime-expert/SKILL.md` | `69fd4f036c02e5a0978f46fc0aa051566fea35451bc29164b239e3d31f80a9c0` |
| `skills/markeitech-python-runtime-expert/references/review-protocol.md` | `6acadfeb08d7a45d27821331615c88593a6e93f1f8280ddc87b57e746d3892f4` |
| `skills/markeitech-python-runtime-expert/references/evidence-and-sources.md` | `65cc7eb06561d6906530d2eae88e0eb5c430f264aaaefde2dea12c0fd5f8aa55` |
| `skills/markeitech-quantitative-metric-validation-expert/SKILL.md` | `494e2f2b9ac3e93b73a9eb612bb406c51cc599701029508afb98835a28f191c5` |
| `skills/markeitech-data-quality-lineage-expert/SKILL.md` | `03d426762328fc2f87633c8a4eb6bcd42deb845fd7350d5aeaae6c52bd68c0d4` |
| `skills/markeitech-evidence-fitness-expert/SKILL.md` | `543266b51034f34abd8edd1fa81c7533e7da04b8ded509a235ce6eec26add963` |
| `skills/markeitech-architecture-boundaries-expert/SKILL.md` | `3acfabe790c371b286b9f927c19d4ab457f2f1c7af5ad803ba2be8c6be345529` |
| `skills/markeitech-architecture-boundaries-expert/references/review-protocol.md` | `0c0e9a4ebbb96fbad387d9e9515c4621ff855b09685cd9a19f789730ed7be58d` |
| `tests/fixtures/shutdown.py` | `46e83f7555cd8a61332aecf603a4bd48850c8661394545060dbcbe6b425eaf0c` |
| `tests/fixtures/warmup.py` | `56ef383bfbc38d3b5fb16c6be767b3c79806853206a4398d899f643f40bca1db` |
| `tests/fixtures/ownership.md` | `0d80b41c265969f8eb23a55aa101fd43af850dfceb51f8cafedadf0b88509ac7` |

## Deterministic Verification

- `python3 -B plugins/kite/scripts/validate_skill_library.py`: passed; 21 entrypoints, local
  links valid, no retired project advisors.
- `python3 -B -m unittest discover -s plugins/kite/tests`: 8 passed. Tests cover package
  version/identity, broken links, stale role discovery, unrelated-role preservation, and activation
  metadata. They do not test semantic instruction following.
- Bundled Plugin Creator manifest validation: passed.
- Bundled Skill Creator frontmatter validation: all 21 entrypoints passed.
- Ruff over the package Python and package helper: passed.
- The existing V2 offline CI job now also runs the library validator and eight package tests.
  Exact-head runtime regression and CI results are recorded on the PR.

## Review And Installed Check

Markeitect reviews whether this is useful for the intended workflow before approving and merging
the PR. Installation was not performed during source implementation. After an authorized candidate
install using [Kite operations](../operations/kite.md), open a fresh task in the matching checkout
and try an actual small change or the maintained fixture prompts. Confirm that the revised
entrypoint is loaded, old project roles are absent, scope stays useful, and activation resets for
unrelated work. Stop and report source/cache mismatch or unexpected scope expansion.

Explicit activation, direct-follow-up continuity, unrelated-task reset, optional-review behavior
under unavailable capacity, and broader domain behavior remain unverified on the installed host.
The three source cases are evidence for this proposed workflow, not blanket acceptance of those
conditions or of the removed council's historical claims.
