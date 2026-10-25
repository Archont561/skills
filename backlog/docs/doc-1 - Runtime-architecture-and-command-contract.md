---
id: doc-1
title: Runtime architecture and command contract
type: specification
created_date: '2026-10-25T19:22:00Z'
---

## Scope

Everything the shipped runtime (`skills/archont561/`) guarantees on a
consumer machine. Normative keywords (MUST/SHOULD/MAY) as in RFC 2119.
Rationale for each choice: see decisions 1–3.

## Layout

```text
<skills_root>/
├── skills-lock.json         # optional manifest (see §Resolution)
├── archont561/              # the engine; MUST sit directly under the root
│   ├── __main__.py          # CLI: dispatch, builtins, argv handling
│   ├── runtime.py           # scanning, context, command loading
│   ├── installer.py         # shim/venv writer for `setup`
│   └── requirements.txt     # optional extras (typer, rich)
└── <skill>/
    ├── SKILL.md             # frontmatter name == dir name
    └── commands/<name>.py   # one command per module
```

## Invocation

1. Shim: `archont561 <command> [argv]` (written by `setup` into
   `~/.archont561/bin/`, added to PATH via an idempotent rc block; a
   PowerShell companion is written alongside).
2. Direct: `python <skills_root>/archont561 <command> [argv]` — this MUST
   always work; every behavior of the shim reduces to it.
3. Exit codes: `0` success; `1` no commands found (`list` on empty set);
   `2` usage/dispatch errors (unknown command, ambiguous command name,
   unloadable command module). Usage errors print to stderr.

## Resolution

Discovery runs per invocation, order:

1. **Manifest mode.** If `<skills_root>/skills-lock.json` parses to one of
   `{"skills": [names...]}` or `{"skills": {name: meta...}}`, exactly those
   directory names are candidates. Candidates without a dir + SKILL.md are
   skipped and reported in `ctx.lock_missing` (list[str]) plus a `doctor`
   warning line; they MUST NOT fail the call.
2. **Prefix mode (fallback).** Otherwise, every sibling directory starting
   with `runtime.PREFIX` (`"archont561"`) with a SKILL.md is a skill.

A manifest that is absent, unreadable, invalid JSON, or of an unexpected
shape MUST fall back to prefix mode (fail-open). Directory names in manifest
mode are unconstrained (no prefix needed); frontmatter `name` SHOULD equal
the directory name.

Per skill, `<skill>/commands/*.py` (not starting with `_`) define commands:
command name = module stem with `_`→`-`. The first line of the module
docstring is the summary.

## AppContext

```python
@dataclass
class AppContext:
    skills_root: Path
    shell: str                       # detect_shell(): $SHELL name, else
                                     # powershell on nt, else "sh"
    skills: dict[str, SkillInfo]     # name -> {root, description, commands}
    lock_missing: list[str]          # stale manifest entries (may be empty)
```

## Dispatch contract

```python
def command(ctx: AppContext, argv: list[str]) -> int: ...
```

- Modules are imported by file path under a synthetic module name; the module
  MUST define a callable `command`. Missing/non-callable → exit 2.
- Command names MUST be unique across the active set; a conflict aborts the
  call with exit 2 naming both providers.
- Commands MUST NOT require third-party imports; optional enhancements are
  guarded (decision-3). Return value is the process exit code.

## Builtins

| Command | Behavior |
| ------- | -------- |
| `help` / none | print usage, exit 0 |
| `list` | merged command table (rich table when extras installed, plain otherwise); exit 1 when empty |
| `doctor` | shell, skills_root, active resolver, skills + commands, stale lock warnings |
| `setup [--print] [--deps]` | write shim + rc PATH block (idempotent), PowerShell companion; `--print` shows actions without writing; `--deps` creates `~/.archont561/venv` from requirements.txt and upgrades the shim to prefer it |

Every command accepts `--root DIR` to override the skills root.
