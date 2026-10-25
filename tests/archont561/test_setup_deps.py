"""Tests for setup --deps (venv bootstrap) and the optional-deps design."""

from ..conftest import load_skill_module
from .test_core_runtime import REPO_SKILLS, consumer_root, run_core  # noqa: F401


def test_requirements_file_declares_optional_deps():
    requirements = REPO_SKILLS / "archont561" / "requirements.txt"
    assert requirements.is_file()
    text = requirements.read_text(encoding="utf-8")
    assert "typer" in text
    assert "rich" in text


def test_shim_content_prefers_venv_python(consumer_root):  # noqa: F811
    installer = load_skill_module(consumer_root / "archont561", "installer")
    content = installer._shim_content(consumer_root)
    assert ".archont561/venv/bin/python" in content
    assert "archont561" in content
    # fallback stays plain python3
    assert 'exec python3 "$CORE"' in content


def test_setup_deps_print_is_dry_run(consumer_root, tmp_path):  # noqa: F811
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    proc = run_core(
        consumer_root,
        "setup",
        "--deps",
        "--print",
        env_extra={"HOME": str(fake_home)},
    )
    assert proc.returncode == 0
    assert "would venv: create" in proc.stdout
    assert "would deps: pip install" in proc.stdout
    # dry run must not create the venv
    assert not (fake_home / ".archont561" / "venv").exists()


def test_shim_without_venv_still_works(consumer_root, tmp_path):  # noqa: F811
    """Baseline: shim falls back to plain python3 when no venv exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    run_core(consumer_root, "setup", env_extra={"HOME": str(fake_home)})
    shim = fake_home / ".archont561" / "bin" / "archont561"
    import subprocess

    proc = subprocess.run(
        ["sh", str(shim), "greet", "--name", "Fallback"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Hello, Fallback!" in proc.stdout
