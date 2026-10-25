---
id: decision-6
title: Coverage via single pytest-cov report and path-scoped Codecov
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

We want per-area coverage visibility for `scripts/` (repo tooling) and
`skills/` (shipped runtime) on Codecov. Two complications: (1) skill code is
exercised by spawning real interpreters (`python <skills_root>/archont561`,
`sh` shims), which in-process coverage never sees; (2) tests run skills from
tmp copies for isolation, so the recorded paths are not the repo paths.

## Decision

One engine, one report: **pytest-cov** drives everything
(`pytest --cov=scripts --cov=skills --cov-report=term --cov-report=xml`), and
Codecov scopes its two `project` status checks by **path** instead of flags —
no flag-split uploads. The subprocess plumbing is configuration, not code:

- the `test` task exports `COVERAGE_PROCESS_START=pyproject.toml`, which arms
  the `a1_coverage.pth` conda-forge ships, so every spawned python measures
  itself;
- `parallel = true` makes each process write its own shard (plain `.coverage`
  writes clobber each other across sibling subprocesses — observed directly);
- pytest-cov auto-combines shards at session end;
- `[tool.coverage.paths]` remaps `*/archont561*` and `*/hello` tmp trees back
  onto `skills/` since the copies are byte-identical.

CI runs upload once with `pixi run cov-upload` (codecov-cli from PyPI,
keeping every CI step `pixi run ...`); public repos tokenless, private repos
need the `CODECOV_TOKEN` secret.

## Consequences

- ~77% total coverage including genuinely-dispatched skill code, tracked per
  area with a 2% regression threshold and a 60% patch target.
- No alternative instrumenter (no raw coverage.py orchestration in tasks);
  everything passes through pytest-cov CLI/reporting.
- The `.coverage*`/xml artifacts are git-ignored local/CI byproducts only.
