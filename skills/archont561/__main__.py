"""archont561 dispatcher.

Invoked either directly (``python <skills_root>/archont561 ...``) or via
the ``archont561`` shim that ``setup`` installs onto your PATH.

Builtins:
  setup [--root DIR] [--print]   install the PATH shim for your shell
  doctor [--root DIR]            show detected shell, root, skills, commands
  list   [--root DIR]            list all commands contributed by skills
  help                           this text

Anything else is dispatched to a command module discovered via a
``skills-lock.json`` manifest in the skills root when present, else the
sibling ``archont561*`` skills (their commands/*.py files).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sibling modules (runtime.py, installer.py) importable when running
# this directory directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import installer
import runtime


def _rich():
    """(Console, Table) when rich is installed via `setup --deps`, else (None, None)."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return None, None
    return Console(), Table


USAGE = """archont561 — entrypoint for Archont561 skills

usage:
  archont561 <command> [-- ...]   run a skill-provided command
  archont561 list                 list all available commands
  archont561 doctor               show resolved context
  archont561 setup [--print] [--deps]   install the PATH shim (+ optional deps venv)

options:
  --root DIR   skills root (default: this core skill's parent directory)
"""


def _extract_root(argv: list[str]) -> tuple[Path | None, list[str]]:
    """Pull a '--root DIR' pair out of argv."""
    if "--root" not in argv:
        return None, argv
    idx = argv.index("--root")
    try:
        return Path(argv[idx + 1]), argv[:idx] + argv[idx + 2 :]
    except IndexError as exc:
        raise SystemExit("error: --root requires a directory") from exc


def _setup(rest: list[str]) -> int:
    root_override, rest = _extract_root(rest)
    dry_run = "--print" in rest
    with_deps = "--deps" in rest
    core_dir = Path(__file__).resolve().parent
    skills_root = (root_override or core_dir.parent).resolve()
    shell = runtime.detect_shell()
    p = installer.plan(skills_root, shell, Path.home())
    print(f"shell: {shell}")
    prefix = "would " if dry_run else ""
    for action in installer.install(p, dry_run=dry_run):
        print(f"  {prefix}{action}")
    if with_deps:
        for action in installer.install_deps(p, dry_run=dry_run):
            print(f"  {prefix}{action}")
    print(installer.post_install_hint(p))
    return 0


def _list(ctx: runtime.AppContext) -> int:
    commands = runtime.command_map(ctx)
    if not commands:
        print("no skill commands found in", ctx.skills_root)
        return 1
    console, table_cls = _rich()
    if console and table_cls:
        table = table_cls(header_style="bold", title=f"root: {ctx.skills_root}")
        table.add_column("command", style="cyan")
        table.add_column("summary")
        table.add_column("skill")
        for name, info in sorted(commands.items()):
            table.add_row(name, info.summary, info.skill)
        console.print(table)
        return 0
    width = max(len(name) for name in commands)
    for name, info in sorted(commands.items()):
        print(f"  {name:<{width}}  {info.summary}  [{info.skill}]")
    return 0


def _doctor(ctx: runtime.AppContext) -> int:
    lock_used = (ctx.skills_root / runtime.LOCK_FILE).is_file()
    resolver = runtime.LOCK_FILE if lock_used else f"prefix scan ({runtime.PREFIX}*)"
    console, _ = _rich()
    if console:
        console.print(f"[bold]shell:[/bold]       {ctx.shell}")
        console.print(f"[bold]skills_root:[/bold] {ctx.skills_root}")
        console.print(f"[bold]resolver:[/bold]    {resolver}")
        console.print(f"[bold]skills:[/bold]      {len(ctx.skills)}")
        for skill in ctx.skills.values():
            names = ", ".join(sorted(skill.commands)) or "-"
            console.print(f"  - {skill.name} (commands: {names})")
        for missing in ctx.lock_missing:
            console.print(f"  [yellow]![/yellow] lock entry missing on disk: {missing}")
        return 0
    print(f"shell:       {ctx.shell}")
    print(f"skills_root: {ctx.skills_root}")
    print(f"resolver:    {resolver}")
    print(f"skills:      {len(ctx.skills)}")
    for skill in ctx.skills.values():
        names = ", ".join(sorted(skill.commands)) or "-"
        print(f"  - {skill.name} (commands: {names})")
    for missing in ctx.lock_missing:
        print(f"  ! lock entry missing on disk: {missing}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return 0

    command, rest = args[0], args[1:]

    if command == "setup":
        return _setup(rest)

    root_override, rest = _extract_root(rest)
    ctx = runtime.build_context(root_override)

    if command == "doctor":
        return _doctor(ctx)
    if command == "list":
        return _list(ctx)

    try:
        commands = runtime.command_map(ctx)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if command not in commands:
        print(f"error: unknown command {command!r}", file=sys.stderr)
        print("available:", ", ".join(sorted(commands)) or "(none)", file=sys.stderr)
        return 2

    info = commands[command]
    try:
        fn = runtime.load_command(info)
    except (ImportError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return int(fn(ctx, rest) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
