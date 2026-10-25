"""Install the archont561 entrypoint: PATH shim + shell rc block.

Stdlib-only. The shim lives in ~/.archont561/bin/ and simply execs the core
skill; the shell rc file gets an idempotent marked block appending it to PATH
(that is the durable "alias").
"""

from __future__ import annotations

import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BASENAME = "archont561"
MARK_BEGIN = "# >>> archont561 >>>"
MARK_END = "# <<< archont561 <<<"

_RC_FILES = {
    "bash": ".bashrc",
    "zsh": ".zshrc",
    "fish": ".config/fish/config.fish",
}
_RC_FALLBACK = ".profile"


@dataclass
class InstallPlan:
    bin_dir: Path
    shim_path: Path
    rc_path: Path
    shell: str
    skills_root: Path


def shim_dir(home: Path) -> Path:
    return home / ".archont561" / "bin"


def venv_dir(home: Path) -> Path:
    """Isolated env for optional deps (typer/rich). Never the user's env."""
    return home / ".archont561" / "venv"


def rc_file(shell: str, home: Path) -> Path:
    return home / _RC_FILES.get(shell, _RC_FALLBACK)


def _shim_content(skills_root: Path) -> str:
    # The shim self-upgrades: if the deps venv exists (setup --deps), it is used.
    core = skills_root / "archont561"
    return (
        "#!/usr/bin/env sh\n"
        f'CORE="{core}"\n'
        'VENV_PY="$HOME/.archont561/venv/bin/python"\n'
        'if [ -x "$VENV_PY" ]; then\n'
        '  exec "$VENV_PY" "$CORE" "$@"\n'
        "fi\n"
        'exec python3 "$CORE" "$@"\n'
    )


def _shim_content_ps1(skills_root: Path) -> str:
    core = skills_root / "archont561"
    return (
        '$VenvPy = "$HOME/.archont561/venv/Scripts/python.exe"\n'
        f'$Core = "{core}"\n'
        "if (Test-Path $VenvPy) { & $VenvPy $Core @args }\n"
        "else { python $Core @args }\n"
    )


def plan(skills_root: Path, shell: str, home: Path) -> InstallPlan:
    return InstallPlan(
        bin_dir=shim_dir(home),
        shim_path=shim_dir(home) / BASENAME,
        rc_path=rc_file(shell, home),
        shell=shell,
        skills_root=skills_root.resolve(),
    )


def rc_block(p: InstallPlan) -> str:
    return f'{MARK_BEGIN}\nexport PATH="{p.bin_dir}:$PATH"\n{MARK_END}\n'


def install(p: InstallPlan, dry_run: bool = False) -> list[str]:
    """Create shim + rc block. Returns human-readable actions taken."""
    actions: list[str] = []
    actions.append(f"shim: {p.shim_path} -> python3 {p.skills_root}/archont561")
    if not dry_run:
        p.bin_dir.mkdir(parents=True, exist_ok=True)
        p.shim_path.write_text(_shim_content(p.skills_root), encoding="utf-8")
        p.shim_path.chmod(
            p.shim_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
        # PowerShell companion for Windows / cross-shell users.
        p.shim_path.with_suffix(".ps1").write_text(
            _shim_content_ps1(p.skills_root), encoding="utf-8"
        )

    existing = p.rc_path.read_text(encoding="utf-8") if p.rc_path.is_file() else ""
    if MARK_BEGIN in existing:
        actions.append(f"rc: {p.rc_path} already configured (skipped)")
    else:
        actions.append(f"rc: append PATH block to {p.rc_path}")
        if not dry_run:
            p.rc_path.parent.mkdir(parents=True, exist_ok=True)
            with p.rc_path.open("a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write(rc_block(p))
    return actions


def post_install_hint(p: InstallPlan) -> str:
    return (
        f"done. reload your shell ({p.shell}) or run:\n"
        f'  export PATH="{p.bin_dir}:$PATH"\n'
        f"then: {BASENAME} list\n"
        f"optional enhanced output: {BASENAME} setup --deps"
    )


def install_deps(p: InstallPlan, dry_run: bool = False) -> list[str]:
    """Create the isolated venv and install core's requirements.txt into it."""
    venv = venv_dir(Path.home())
    requirements = p.skills_root / "archont561" / "requirements.txt"
    actions = [
        f"venv: create {venv}",
        f"deps: pip install -r {requirements}",
    ]
    if dry_run:
        return actions
    if not requirements.is_file():
        raise SystemExit(f"error: {requirements} not found")
    venv_python = venv / "bin" / "python"
    if not venv_python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements)],
        check=True,
    )
    return actions
