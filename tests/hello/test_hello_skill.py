"""The hello skill is discoverable in this repo's skills/ dir."""

from pathlib import Path

from ..conftest import load_skill_module

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_SKILLS = REPO_ROOT / "skills"


def test_repo_scan_finds_greet_command():
    runtime = load_skill_module(REPO_SKILLS / "archont561")
    ctx = runtime.build_context(REPO_SKILLS)
    hello = ctx.skills.get("hello")
    assert hello is not None
    assert set(hello.commands) == {"greet"}
    fn = runtime.load_command(hello.commands["greet"])
    assert callable(fn)
