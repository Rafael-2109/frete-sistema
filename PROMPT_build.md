0a. Study `specs/*` with up to 500 parallel subagents to learn specifications.
0b. Study @IMPLEMENTATION_PLAN.md.
0c. Reference CLAUDE.md for field names, conventions, and validation rules.

1. Implement functionality per specifications following @IMPLEMENTATION_PLAN.md. Choose the most important item. Before making changes, search the codebase (don't assume not implemented) using subagents. Use up to 500 parallel subagents for searches/reads and only 1 subagent for build/tests. Use subagents for complex reasoning when needed.

2. After implementing, run tests for that unit of code. If functionality is missing, add it per specifications. Ultrathink.

3. When you discover issues, immediately update @IMPLEMENTATION_PLAN.md with your findings. When resolved, update and remove the item.

4. When tests pass, update @IMPLEMENTATION_PLAN.md, then `git add -A` then `git commit` with descriptive message. After commit, `git push`.

99999. Capture the why in documentation.
999999. Single sources of truth, no migrations/adapters. If unrelated tests fail, resolve them.
9999999. Create git tag on clean builds (start 0.0.0, increment patch).
99999999. Add extra logging if needed for debugging.
999999999. Keep @IMPLEMENTATION_PLAN.md current with learnings.
9999999999. Update @AGENTS.md with operational learnings (keep brief).
99999999999. Resolve or document bugs in @IMPLEMENTATION_PLAN.md.
999999999999. Implement completely. No placeholders or stubs.
9999999999999. Periodically clean completed items from @IMPLEMENTATION_PLAN.md.
99999999999999. Use Opus 4.5 subagent with 'ultrathink' for spec inconsistencies.
999999999999999. Keep @AGENTS.md operational only — progress notes go in IMPLEMENTATION_PLAN.md.
