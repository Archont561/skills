---
name: hello
description: Demo command-provider skill for the Archont561 runtime. Contributes the "greet" command to archont561. Use to verify that core dispatch and the shared context work after setup.
license: MIT
metadata:
  author: Archont561
  version: "1.0.0"
  namespace: archont561
---

# Archont561 Hello

Minimal command-provider skill: demonstrates how an Archont561 skill adds a
command that the core runtime discovers and executes with the shared context.

## When to use this skill

- Verifying a fresh Archont561 runtime installation end-to-end.
- As a template when authoring a new Archont561 command-provider skill.

## How to use it

After core's one-time setup:

```bash
archont561 greet
archont561 greet --name Ada
```

The command prints a greeting plus facts from the shared `AppContext`
(`skills_root`, detected `shell`) — proof that core scanned this skill and
injected context. The implementation lives in `commands/greet.py` and follows
the contract `def command(ctx, argv: list[str]) -> int`.
