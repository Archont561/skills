---
id: decision-3
title: Stdlib-only runtime baseline with optional deps venv
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Skill commands execute on consumer machines whose Python environment we do
not control. Any runtime third-party import (typer, rich, pyyaml) would make
the shipped skill set fragile or force consumers into installs they did not
sign up for. At the same time, richer UX (tables, colors) is genuinely nicer
when available.

## Decision

The runtime is strictly stdlib-only: frontmatter parsing is a regex, dispatch
is argv munging, output is print(). Optional enhancements ship as
`skills/archont561/requirements.txt` (typer, rich) plus an opt-in bootstrap:
`archont561-skills setup --deps` creates an isolated venv at
`~/.archont561/venv` and installs the requirements into it — never into the
project or system environment. The installed shim prefers the venv python on
subsequent calls and silently falls back to `python3` when the venv is
absent. Optional imports are guarded (`_rich()` try/except ImportError with a
plain-output fallback), and SKILL.md declares this via the `compatibility:`
field.

## Consequences

- Every skill command keeps working identically with and without the extras;
  only the rendering changes (`list`/`doctor` tables).
- The venv lives under `~/.archont561/` — isolated, auto-detected, removable
  by deletion.
- New optional deps must be additive and import-guarded; hard dependencies
  are off the table for the runtime.
