"""Consumer-environment tests for archont561.

Simulates the real lifecycle: skills installed as siblings under a consumer's
.agents/skills/, core run as `python <root>/archont561`, then via the
installed PATH shim with a fake HOME.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_SKILLS = REPO_ROOT / "skills"
CORE = REPO_SKILLS / "archont561"

from ..conftest import load_skill_module


@pytest.fixture()
def consumer_root(tmp_path):
    """A fake consumer install: .agents/skills/{archont561,hello} + lock."""
    root = tmp_path / ".agents" / "skills"
    for skill in ("archont561", "hello"):
        shutil.copytree(REPO_SKILLS / skill, root / skill)
    # unprefixed installs resolve via the manifest — mirrors real usage
    (root / "skills-lock.json").write_text(
        json.dumps({"skills": ["archont561", "hello"]}),
        encoding="utf-8",
    )
    return root


def run_core(root: Path, *args: str, env_extra: dict | None = None):
    import os

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(root / "archont561"), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_scan_discovers_locked_skills_and_commands(consumer_root):
    runtime = load_skill_module(consumer_root / "archont561")
    ctx = runtime.build_context(consumer_root)
    assert set(ctx.skills) == {"archont561", "hello"}
    assert "greet" in ctx.skills["hello"].commands
    mapping = runtime.command_map(ctx)
    assert mapping["greet"].skill == "hello"
    assert mapping["greet"].summary.startswith("greet — print a greeting")


def test_dispatch_greet_with_context(consumer_root):
    proc = run_core(consumer_root, "greet", "--name", "Ada")
    assert proc.returncode == 0
    assert "Hello, Ada!" in proc.stdout
    assert f"skills_root={consumer_root}" in proc.stdout


def test_list_and_doctor_builtins(consumer_root):
    listing = run_core(consumer_root, "list")
    assert listing.returncode == 0
    assert "greet" in listing.stdout

    doctor = run_core(consumer_root, "doctor")
    assert doctor.returncode == 0
    assert "skills_root:" in doctor.stdout
    assert "hello" in doctor.stdout


def test_unknown_command_fails_with_hint(consumer_root):
    proc = run_core(consumer_root, "bogus")
    assert proc.returncode == 2
    assert "unknown command" in proc.stderr
    assert "greet" in proc.stderr


def test_conflicting_commands_fail_loudly(consumer_root):
    clash = consumer_root / "archont561-other" / "commands"
    clash.mkdir(parents=True)
    (consumer_root / "archont561-other" / "SKILL.md").write_text(
        "---\nname: archont561-other\ndescription: clash fixture.\n---\n",
        encoding="utf-8",
    )
    (clash / "greet.py").write_text(
        "def command(ctx, argv):\n    return 0\n", encoding="utf-8"
    )
    # register the clashing skill in the manifest so it enters resolution
    lock = consumer_root / "skills-lock.json"
    payload = json.loads(lock.read_text(encoding="utf-8"))
    payload["skills"].append("archont561-other")
    lock.write_text(json.dumps(payload), encoding="utf-8")
    proc = run_core(consumer_root, "greet")
    assert proc.returncode == 2
    assert "ambiguous" in proc.stderr


def test_setup_installs_shim_and_rc_block(consumer_root, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    proc = run_core(consumer_root, "setup", env_extra={"HOME": str(fake_home)})
    assert proc.returncode == 0, proc.stderr

    shim = fake_home / ".archont561" / "bin" / "archont561"
    assert shim.is_file()
    assert shim.stat().st_mode & 0o100  # executable
    content = shim.read_text(encoding="utf-8")
    assert "archont561" in content

    rc = fake_home / ".bashrc"  # bash under CI $SHELL or fallback .profile
    if not rc.is_file():
        rc = fake_home / ".profile"
    rc_text = rc.read_text(encoding="utf-8")
    assert "archont561 >>>" in rc_text

    # idempotent: running again must not duplicate the block
    run_core(consumer_root, "setup", env_extra={"HOME": str(fake_home)})
    assert rc.read_text(encoding="utf-8").count("archont561 >>>") == 1

    # the shim itself dispatches
    shimmed = subprocess.run(
        ["sh", str(shim), "greet", "--name", "Shim"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert shimmed.returncode == 0
    assert "Hello, Shim!" in shimmed.stdout


def test_setup_print_is_dry_run(consumer_root, tmp_path):
    fake_home = tmp_path / "home2"
    fake_home.mkdir()
    proc = run_core(
        consumer_root, "setup", "--print", env_extra={"HOME": str(fake_home)}
    )
    assert proc.returncode == 0
    assert "would" in proc.stdout
    assert not (fake_home / ".archont561").exists()


def test_root_flag_overrides_scan_dir(consumer_root, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = run_core(consumer_root, "doctor", "--root", str(empty))
    assert proc.returncode == 0
    assert "skills:      0" in proc.stdout
