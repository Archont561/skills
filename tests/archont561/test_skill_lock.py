"""skills-lock.json manifest resolution: explicit registry over prefix scan."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ..conftest import load_skill_module

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "skills" / "archont561"


def _make_skill(root: Path, name: str, summary: str = ""):
    d = root / name
    (d / "commands").mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} skill\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    (d / "commands" / "ping.py").write_text(
        f'"""{summary or name + " ping"}"""\n\n\n'
        'def command(ctx, argv):\n    print("ping")\n    return 0\n',
        encoding="utf-8",
    )


def _write_lock(root: Path, payload: object):
    (root / "skills-lock.json").write_text(json.dumps(payload), encoding="utf-8")


def test_manifest_enables_unprefixed_skill_names(tmp_path):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "acme-tools", summary="acme ping")
    _write_lock(tmp_path, {"skills": ["acme-tools"]})
    ctx = rt.build_context(tmp_path)
    assert set(ctx.skills) == {"acme-tools"}
    assert "ping" in ctx.skills["acme-tools"].commands
    assert ctx.lock_missing == []


def test_manifest_mapping_form_is_accepted(tmp_path):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "acme-tools")
    _write_lock(tmp_path, {"skills": {"acme-tools": {"source": "gh:acme/tools"}}})
    ctx = rt.build_context(tmp_path)
    assert set(ctx.skills) == {"acme-tools"}


def test_manifest_takes_precedence_over_prefix_scan(tmp_path):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "archont561-legacy")
    _make_skill(tmp_path, "acme-tools")
    _write_lock(tmp_path, {"skills": ["acme-tools"]})
    ctx = rt.build_context(tmp_path)
    # the prefixed but unlisted skill is NOT active while a manifest exists
    assert set(ctx.skills) == {"acme-tools"}


def test_malformed_manifest_fails_open_to_prefix_scan(tmp_path):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "archont561-legacy")
    (tmp_path / "skills-lock.json").write_text("not json {", encoding="utf-8")
    ctx = rt.build_context(tmp_path)
    assert set(ctx.skills) == {"archont561-legacy"}


@pytest.mark.parametrize("payload", [{"skills": 42}, {"skills": [7]}, []])
def test_unexpected_manifest_shapes_fall_back(tmp_path, payload):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "archont561-legacy")
    _write_lock(tmp_path, payload)
    ctx = rt.build_context(tmp_path)
    assert set(ctx.skills) == {"archont561-legacy"}


def test_stale_lock_entries_are_reported_not_fatal(tmp_path):
    rt = load_skill_module(CORE)
    _make_skill(tmp_path, "acme-tools")
    _write_lock(tmp_path, {"skills": ["acme-tools", "ghost-skill"]})
    ctx = rt.build_context(tmp_path)
    assert set(ctx.skills) == {"acme-tools"}
    assert ctx.lock_missing == ["ghost-skill"]


def test_doctor_reports_resolver_and_stale_entries(tmp_path):
    _make_skill(tmp_path, "acme-tools")
    _write_lock(tmp_path, {"skills": ["acme-tools", "ghost-skill"]})
    proc = subprocess.run(
        [sys.executable, str(CORE), "doctor", "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "resolver:    skills-lock.json" in proc.stdout
    assert "ghost-skill" in proc.stdout
    assert "acme-tools (commands: ping)" in proc.stdout


def test_doctor_reports_prefix_scan_without_manifest(tmp_path):
    _make_skill(tmp_path, "archont561-legacy")
    proc = subprocess.run(
        [sys.executable, str(CORE), "doctor", "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "resolver:    prefix scan (archont561*)" in proc.stdout
