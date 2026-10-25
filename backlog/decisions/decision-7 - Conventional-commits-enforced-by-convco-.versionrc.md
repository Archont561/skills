---
id: decision-7
title: Conventional commits enforced by convco .versionrc
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Releases (version bumps, CHANGELOG) should be derivable from commit history.
convco (conda-forge) provides commit validation, version computation, and
changelog generation; its behavior is configurable through `.versionrc`.
Defaults alone were too loose (unknown types accepted).

## Decision

All commits are conventional commits, enforced at two gates:

1. lefthook `commit-msg`: `convco check --from-stdin --strip`;
2. CI: `pixi run convco check <range> --first-parent` on push/PR.

`.versionrc` (YAML, repo root) declares the type catalogue used by every
convco command — visible changelog sections for feat/fix/perf/docs/revert/
refactor, hidden sections for build/chore/ci/style/test — plus
`preMajor: true` (breaking change bumps `0.(x+1).0` while pre-1.0) and the
`#` issue prefix. Undeclared types are rejected with a suggestion
(`frob:` → "did you mean `fix`"). host/owner/repository auto-derive from the
origin remote for changelog links, so no org name is hardcoded.

## Consequences

- `convco version` / `convco changelog` produce semver + changelog sections
  directly from history (0.x until the first deliberate major).
- Commit messages double as machine input; scopes remain free-form.
- Repo-local convention docs live in the repo (README commit rules) and the
  catalogue itself is linted by all participants — hooks and CI read the
  same file.
