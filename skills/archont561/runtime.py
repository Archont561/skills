"""Scanning + shared context for Archont561 skills.

Zero third-party dependencies: this file runs wherever a consumer installed
the skills (no typer/rich/pyyaml on the consumer side).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

#: Skills from the Archont561 registry default to this namespace when no
#: skills-lock.json manifest is present. Matches both the bare engine
#: (`archont561`) and legacy `archont561-<name>` installs.
PREFIX = "archont561"

#: Optional manifest in the skills root that pins which sibling directories
#: are active skills. When present it replaces the PREFIX scan, so skill
#: directory names do NOT need the archont561- prefix to resolve commands.
LOCK_FILE = "skills-lock.json"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
_FIELD_RE = lambda name: re.compile(rf"^{name}:\s*(.+)$", re.MULTILINE)


@dataclass
class CommandInfo:
    """One command contributed by a skill (commands/<name>.py)."""

    name: str
    summary: str
    module_path: Path
    skill: str


@dataclass
class SkillInfo:
    name: str
    root: Path
    description: str
    commands: dict[str, CommandInfo]


@dataclass
class AppContext:
    """The shared context every skill command receives."""

    skills_root: Path
    shell: str
    skills: dict[str, SkillInfo]
    #: LOCK_FILE entries that name no installable skill dir (stale lock).
    lock_missing: list[str] = field(default_factory=list)


CommandFn = Callable[[AppContext, list[str]], int]


def detect_shell(environ: dict | None = None) -> str:
    """Best-effort shell detection: $SHELL on POSIX, PowerShell on Windows."""
    env = os.environ if environ is None else environ
    shell = env.get("SHELL", "")
    if shell:
        return Path(shell).name
    if os.name == "nt":
        return "powershell"
    return "sh"


def _read_frontmatter(text: str) -> dict[str, str]:
    """Minimal single-line YAML frontmatter reader (name/description)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    out = {}
    for key in ("name", "description"):
        field = _FIELD_RE(key).search(block)
        if field:
            out[key] = field.group(1).strip().strip('"').strip("'")
    return out


def _command_summary(path: Path) -> str:
    """First line of the module docstring doubles as the help text."""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    except (SyntaxError, OSError):
        return ""
    return (doc or "").splitlines()[0] if doc else ""


def _scan_commands(skill_dir: Path, skill_name: str) -> dict[str, CommandInfo]:
    commands_dir = skill_dir / "commands"
    found: dict[str, CommandInfo] = {}
    if not commands_dir.is_dir():
        return found
    for module in sorted(commands_dir.glob("*.py")):
        if module.name.startswith("_"):
            continue
        name = module.stem.replace("_", "-")
        found[name] = CommandInfo(
            name=name,
            summary=_command_summary(module),
            module_path=module,
            skill=skill_name,
        )
    return found


def _load_skill(skills_root: Path, name: str) -> SkillInfo | None:
    """Load one skill dir (needs SKILL.md). Returns None when not installable."""
    entry = skills_root / name
    skill_md = entry / "SKILL.md"
    if not entry.is_dir() or not skill_md.is_file():
        return None
    frontmatter = _read_frontmatter(skill_md.read_text(encoding="utf-8"))
    return SkillInfo(
        name=name,
        root=entry,
        description=frontmatter.get("description", ""),
        commands=_scan_commands(entry, name),
    )


def read_lock(skills_root: Path) -> list[str] | None:
    """Parse <skills_root>/skills-lock.json. Two accepted shapes:

      {"skills": ["name", ...]}            or   {"skills": {"name": {...}, ...}}

    Returns None (caller falls back to prefix scan) when the file is absent,
    unreadable, invalid JSON, or has an unexpected shape — fail-open by design.
    """
    lock = skills_root / LOCK_FILE
    if not lock.is_file():
        return None
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    skills = data.get("skills") if isinstance(data, dict) else None
    if isinstance(skills, dict):  # mapping form: values are per-skill metadata
        skills = list(skills)
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        return None
    return skills


def scan_skills(skills_root: Path) -> dict[str, SkillInfo]:
    """Prefix mode: find sibling Archont561 skills (dirs starting with PREFIX)."""
    skills: dict[str, SkillInfo] = {}
    if not skills_root.is_dir():
        return skills
    for entry in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        if not entry.name.startswith(PREFIX):
            continue
        info = _load_skill(skills_root, entry.name)
        if info is not None:
            skills[entry.name] = info
    return skills


def scan_locked(
    skills_root: Path, names: list[str]
) -> tuple[dict[str, SkillInfo], list[str]]:
    """Manifest mode: only the listed dirs are active skills (any naming)."""
    skills: dict[str, SkillInfo] = {}
    missing: list[str] = []
    for name in names:
        info = _load_skill(skills_root, name)
        if info is not None:
            skills[name] = info
        else:
            missing.append(name)
    return skills, missing


def build_context(skills_root: Path | None = None) -> AppContext:
    """Construct the shared context. Root defaults to this skill's parent —
    i.e. wherever the consumer installed the Archont561 skill set.

    Resolution order: a parseable skills-lock.json manifest pins the active
    skills explicitly (no prefix needed); otherwise sibling archont561-* dirs.
    """
    core_dir = Path(__file__).resolve().parent
    root = Path(skills_root).resolve() if skills_root else core_dir.parent
    lock = read_lock(root)
    if lock is None:
        skills, missing = scan_skills(root), []
    else:
        skills, missing = scan_locked(root, lock)
    return AppContext(
        skills_root=root,
        shell=detect_shell(),
        skills=skills,
        lock_missing=missing,
    )


def command_map(ctx: AppContext) -> dict[str, CommandInfo]:
    """Flat command namespace across all skills. Raises on conflicts."""
    mapping: dict[str, CommandInfo] = {}
    for skill in ctx.skills.values():
        for name, info in skill.commands.items():
            if name in mapping:
                clash = mapping[name]
                raise ValueError(
                    f"command {name!r} is ambiguous: provided by both "
                    f"{clash.skill!r} and {info.skill!r}"
                )
            mapping[name] = info
    return mapping


def load_command(info: CommandInfo) -> CommandFn:
    """Import a command module by file path and return its command function."""
    module_name = (
        f"_archont561_{info.skill.replace('-', '_')}_{info.name.replace('-', '_')}"
    )
    spec = importlib.util.spec_from_file_location(module_name, info.module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot import {info.module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, "command", None)
    if not callable(fn):
        raise TypeError(
            f"{info.module_path}: command modules must define "
            "def command(ctx, argv) -> int"
        )
    return fn
