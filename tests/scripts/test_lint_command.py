"""Tests for scripts.commands.lint, run through the plugin-loaded CLI."""

from pathlib import Path

from typer.testing import CliRunner

from scripts.cli import app
from scripts.commands import lint as lint_mod

runner = CliRunner()

VALID_SKILL_MD = """---
name: demo-skill
description: A demo skill used by tests. Use when testing.
---

# Demo Skill

## When to use this skill

For tests.

## How to use it

Run the thing.
"""

VALID_README = "# Demo Skill\n\nA demo.\n\n## Usage\n\nInstall it.\n"


def make_repo(root: Path) -> Path:
    skill = root / "skills" / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(VALID_SKILL_MD, encoding="utf-8")
    (skill / "README.md").write_text(VALID_README, encoding="utf-8")
    tests = root / "tests" / "demo_skill"
    tests.mkdir(parents=True)
    (tests / "test_demo_skill.py").write_text("def test_ok():\n    pass\n")
    (root / "LICENSE").write_text("MIT License\n")
    return root


def test_valid_repo_passes(tmp_path):
    root = make_repo(tmp_path / "repo")
    result = runner.invoke(app, ["lint", "--path", str(root)])
    assert result.exit_code == 0, result.output
    assert "all structure rules pass" in result.output


def test_missing_skill_md_sections_flagged_then_fixed(tmp_path):
    root = make_repo(tmp_path / "repo")
    skill_md = root / "skills" / "demo-skill" / "SKILL.md"
    skill_md.write_text(
        "---\nname: demo-skill\ndescription: A demo skill for tests.\n---\n\n"
        "# Demo Skill\n\nOnly a title.\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint", "--path", str(root)])
    assert result.exit_code == 1
    assert "skill-sections" in result.output

    fixed = runner.invoke(app, ["lint", "--path", str(root), "--fix"])
    assert "## When to use this skill" in skill_md.read_text(encoding="utf-8")
    rerun = runner.invoke(app, ["lint", "--path", str(root)])
    assert rerun.exit_code == 0 or "skill-sections" not in rerun.output
    assert fixed.exit_code in (0, 1)  # --fix reports remaining findings if any


def test_tests_folder_inside_skill_violates_boundary(tmp_path):
    root = make_repo(tmp_path / "repo")
    inside = root / "skills" / "demo-skill" / "tests"
    inside.mkdir()
    (inside / "test_x.py").write_text("# misplaced\n")
    result = runner.invoke(app, ["lint", "--path", str(root)])
    assert result.exit_code == 1
    assert "no-tests-in-skill" in result.output


def test_missing_readme_fix_creates_stub(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "skills" / "demo-skill" / "README.md").unlink()
    result = runner.invoke(app, ["lint", "--path", str(root), "--fix"])
    assert (root / "skills" / "demo-skill" / "README.md").is_file()
    assert result.exit_code == 0


def test_orphan_tests_dir_flagged(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "tests" / "bogus_skill").mkdir()
    result = runner.invoke(app, ["lint", "--path", str(root)])
    assert result.exit_code == 1
    assert "orphan" in result.output


def test_missing_license_is_fixable(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "LICENSE").unlink()
    result = runner.invoke(app, ["lint", "--path", str(root), "--fix"])
    assert (root / "LICENSE").is_file()
    assert result.exit_code == 0


def test_current_real_repo_is_clean():
    findings = lint_mod.collect(lint_mod.REPO_ROOT)
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], errors
