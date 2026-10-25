---
name: archont561
description: Runtime engine and entrypoint for all Archont561 skills. Installs the archont561 shell shim, scans sibling archont561* skills for commands, builds the shared context, and dispatches calls. Use when setting up the Archont561 skill runtime or adding a command to an Archont561 skill.
license: MIT
compatibility: Requires Python 3.10+. Optional extras (typer, rich) via `archont561 setup --deps`, installed into an isolated venv (~/.archont561/venv) — never into your project environment.
metadata:
  author: Archont561
  version: "1.0.0"
  namespace: archont561
---

# Archont561 Core

Runtime engine for the Archont561 skill set. Every Archont561 skill ships as
plain data + command modules; core provides the single CLI entrypoint
(`archont561`), the runtime scan of sibling skills, and the shared
`AppContext` those commands receive.

## When to use this skill

- First call after installing any Archont561 skill: run `setup` once so the
  `archont561` command is on PATH.
- When an Archont561 skill instructs you to run `archont561 <cmd>`.
- When adding a command: create `commands/<name>.py` inside your skill.

## How to use it

One-time setup (from the directory where the skills were installed, e.g.
`.agents/skills/`):

```bash
python .agents/skills/archont561 setup
```

This detects your shell, writes a shim to `~/.archont561/bin/archont561`
plus a PowerShell companion, and appends a marked PATH block to your shell rc
file (`~/.bashrc`, `~/.zshrc`, fish config, or `~/.profile`).

Then:

```bash
archont561 list                    # every command, from every skill
archont561 doctor                  # shell, root, discovered skills
archont561 <command> [args]        # dispatch into a skill's module
```

If the shim is not on PATH yet (fresh shell), the direct form always works:

```bash
python <skills_root>/archont561 <command> [args]
```

## How commands are discovered

Two resolution modes, manifest wins:

1. **`skills-lock.json` in the skills root** — an explicit registry, e.g.
   `{"skills": ["hello", "acme-tools"]}` (a mapping form
   `{"skills": {"acme-tools": {...}}}` works too; values are metadata).
   Listed skills are the ONLY active ones and may use ANY directory name —
   no `archont561-` prefix required. Stale entries (no dir / no SKILL.md)
   are skipped and reported by `doctor`. A missing or malformed manifest
   fails open to mode 2.
2. **Prefix scan (default)** — siblings named `archont561*` with a
   `SKILL.md`. This exists so bare installs work with zero bookkeeping;
   adding a skill needs no file edits beyond dropping the directory in.

Each skill may contribute `commands/*.py` modules with the contract:

```python
def command(
    ctx, argv: list[str]
) -> int: ...  # ctx: AppContext { skills_root, shell, skills, lock_missing }
```

Module docstring's first line becomes the help summary. Command names must be
unique across all Archont561 skills — conflicts fail loudly, never silently.

## Optional enhancements

`archont561 setup --deps` creates an isolated venv at
`~/.archont561/venv` and installs `requirements.txt` (typer, rich) there. The
shim auto-detects the venv and uses it on the next call — `list` and `doctor`
then render with rich tables. Without it, output is plain and the runtime is
stdlib-only. Declared deps: see `requirements.txt`.

## Environment notes

- The runtime is Python-stdlib-only by design: consumers' machines are not
  required to have typer/rich/any third-party package.
- Preview the exact actions setup will take: `... archont561 setup --print`.
- Override the scanned root explicitly with `--root DIR` on any command.
