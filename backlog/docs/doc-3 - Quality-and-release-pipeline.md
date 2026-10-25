---
id: doc-3
title: Quality and release pipeline
type: specification
created_date: '2026-10-25T19:22:00Z'
---

## Scope

End-to-end quality gates of this repository: local tasks, git hooks, CI jobs,
coverage reporting, commit conventions, and the publish validation. Every
tool comes from the locked pixi environment (conda-forge first, PyPI via
`[pypi-dependencies]` when absent); every CI step is `pixi run ...`.

## Tasks (pixi)

| Task | What it runs |
| ---- | ------------ |
| `test` | pytest-cov over `scripts/`+`skills/`, term + `coverage.xml`; `COVERAGE_PROCESS_START` arms subprocess coverage |
| `lint` | `ruff check scripts tests skills` |
| `lint-md` | pymarkdownlnt on `skills/*/SKILL.md` + `skills/*/README.md` |
| `check` (`--strict`) | structure rules (doc-2 table); warnings fail under `--strict` in CI |
| `fmt` | `check --fix`: safe structural autofixes only |
| `scripts` | smoke: `python -m scripts` prints CLI help |
| `cov-upload` | one `codecovcli upload-process -f coverage.xml` (CI; `CODECOV_TOKEN` if private) |
| `setup` | `lefthook install` — once per clone |

## Git hooks (lefthook)

- `commit-msg`: `convco check --from-stdin --strip` — rejects
  non-conventional messages on the spot.
- `pre-commit`: ruff `--fix`+`format` with restaging on staged `*.py`;
  actionlint on staged workflows; `lint-md` on staged skill docs; `check`.
- `pre-push`: pytest on test files affected by the push.

## CI (`.github/workflows/ci.yml`)

Job `checks`: lint → lint-md → `check --strict` → actionlint → `test` →
Codecov upload → `scripts` smoke → convco range check
(`${{ github.event.before }}..HEAD` on push, `origin/main..HEAD` on PR,
`--first-parent`). Job `spec`: `gh skill publish --dry-run` as the
authoritative Agent Skills spec validation.

## Coverage policy (codecov.yml)

Two path-scoped project statuses: `scripts/` and `skills/`, each
`target: auto` + 2% regression threshold; patch target 60%; `tests/` and
`.agents/` ignored; range 70–100 with round-down. Subprocess measurement and
tmp-copy remapping: decision-6.

## Commits and releases (.versionrc)

Conventional commits only (type catalogue validated by convco; decision-7).
Visible changelog sections: feat/fix/perf/docs/revert/refactor; hidden:
build/chore/ci/style/test. `preMajor: true` until the first deliberate 1.0.
`convco version` proposes the next version; `convco changelog` renders
CHANGELOG sections — URL formats for commit/compare/issue links derive from
the origin remote, no hardcoded org.

## Publishing

No bespoke publish job: `gh skill publish --tag vX.Y.Z` (after the dry-run
gate passes) adds the agent-skills topic and cuts a GitHub release; the repo
is installable immediately and appears on skills.sh automatically once
installed via `npx skills add`. The machine-readable `.well-known` index
remains a tracked follow-up: task-1.
