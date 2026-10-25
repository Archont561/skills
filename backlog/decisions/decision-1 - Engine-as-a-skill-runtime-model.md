---
id: decision-1
title: Engine-as-a-skill runtime model
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Consumers install skills as plain directories under `.agents/skills/` (via
`gh skill install` or `npx skills add`). There is no package manager step on
the consumer side: no pip install, no build, no venv they own. The runtime
must therefore live inside the installed directories and run on a bare
Python 3.10+ interpreter.

## Decision

The runtime engine ships as a skill itself: `skills/archont561`. Skills are
data + code: each skill defines its commands in `commands/<name>.py` modules
implementing one contract:

```python
def command(ctx, argv: list[str]) -> int: ...
```

Core resolves the active skill set, merges all `commands/` into one flat
namespace, builds the shared `AppContext` (`skills_root`, `shell`, `skills`,
`lock_missing`), and dispatches argv to the chosen module. The module
docstring's first line is the `--help`-grade summary. Command names must be
unique across the whole set; a clash raises and aborts dispatch with a clear
error, never a coin flip.

Rejected: a centrally registered command list inside core (couples every new
skill to an engine release); a Typer/Rich dependency at runtime (consumer
machines have neither guaranteed, see decision-3).

## Consequences

- Adding a skill = adding a directory with a SKILL.md and `commands/` module;
  no other file needs to change.
- The whole registry installs as four file trees; `gh skill publish` /
  `npx skills add` compatibility comes free.
- Testing dispatches means spawning the real interpreter (see decision-6 for
  the coverage consequences).
