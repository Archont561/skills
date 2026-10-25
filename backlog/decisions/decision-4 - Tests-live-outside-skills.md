---
id: decision-4
title: Tests live outside skills
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Skill directories are shipped verbatim to installers (`gh skill install`,
`npx skills add` copy the dir as-is). A `tests/` folder inside a skill would
be downloaded onto every consumer machine and would violate the Agent Skills
spec expectation of a minimal directory payload.

## Decision

Tests live in repo-root `tests/<skill-name>/`, mirroring `skills/<skill-name>/`.
The `lint` command (`scripts/commands/lint.py`) enforces both directions:
`no-tests-in-skill` (no tests/, test/, `__tests__/`, `test_*.py`, `*.bats`
inside a skill) and `tests-outside-mirror` (every skill has its mirror; no
orphan test dirs). Because skill code runs in subprocesses under a different
root during tests, coverage maps tmp copies back with
`[tool.coverage.paths]` and modules are imported via the unique-name loader
in `tests/conftest.py` rather than `sys path.insert` + plain import.

## Consequences

- Skill dirs stay copy-clean for installers; agents never ingest test noise.
- The mirror rule makes "where does this test live" mechanically obvious.
- Cross-import between test packages is safe: `tests/` is a package suite
  with unique module names per loaded copy of runtime/installer.
