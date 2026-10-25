"""Repo-wide lint + formatter enforcing the registry's structural boundaries.

Boundary model: only ``skills/`` is publishable registry content;
``.agents/skills/`` (third-party installs) is never linted.

Run:  python -m scripts.cli lint [--fix] [--strict] [--path REPO]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s[^)]*)?\)")

TEST_DIR_NAMES = {"test", "tests", "__tests__"}
ALLOWED_NON_SKILL_TEST_DIRS = {"scripts"}  # tests/ dirs that aren't skill mirrors

# Required section contracts (H2-level, in this order). These stay here because
# pymarkdown's MD043 is positional and cannot express "any H1, then these H2s";
# general markdown hygiene + first-line-H1 are covered by `pixi run lint-md`.
SKILL_SECTIONS = ["When to use this skill", "How to use it"]
README_SECTIONS = ["Usage"]
MAX_BODY_LINES = 500  # progressive-disclosure budget


@dataclass
class Finding:
    rule: str
    severity: str  # "error" | "warning"
    message: str
    skill: str = "-"
    fixable: bool = False


# --- parsing helpers -------------------------------------------------------------


def _split_raw(text: str) -> tuple[str | None, str]:
    """Split SKILL.md text into (frontmatter_raw, body)."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    return text[3:end], text[end + 4 :].lstrip("\n")


def _frontmatter(text: str) -> dict:
    fm_raw, _ = _split_raw(text)
    if fm_raw is None:
        return {}
    try:
        data = yaml.safe_load(fm_raw.strip())
    except yaml.YAMLError as exc:
        return {"__parse_error__": str(exc).splitlines()[-1]}
    return data if isinstance(data, dict) else {}


def _headings(markdown: str) -> list[tuple[int, str]]:
    """Markdown headings as (level, title), skipping fenced code blocks."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line.strip())
        if match:
            out.append((len(match.group(1)), match.group(2)))
    return out


def _missing_sections(markdown: str, required: list[str]) -> list[str]:
    """Required H2 sections that are absent or out of order."""
    h2 = [title.lower() for level, title in _headings(markdown) if level == 2]
    missing: list[str] = []
    cursor = 0
    for wanted in required:
        needle = wanted.lower()
        if needle in h2[cursor:]:
            cursor = h2.index(needle, cursor) + 1
        else:
            missing.append(wanted)
    return missing


# --- rules -----------------------------------------------------------------------


def _skipped(path: Path) -> bool:
    return any(part == "__pycache__" or part.startswith(".") for part in path.parts)


def _test_artifacts(skill_dir: Path) -> list[Path]:
    bad = []
    for found in skill_dir.rglob("*"):
        if _skipped(found.relative_to(skill_dir)):
            continue
        if (found.is_dir() and found.name in TEST_DIR_NAMES) or (
            found.is_file()
            and (found.name.startswith("test_") or found.suffix == ".bats")
        ):
            bad.append(found)
    return bad


def _relative_link_findings(body: str, skill_dir: Path, name: str) -> list[Finding]:
    findings = []
    for link in LINK_RE.findall(body):
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (skill_dir / link.split("#")[0]).exists():
            findings.append(
                Finding(
                    "relative-refs-exist",
                    "warning",
                    f"SKILL.md links to a missing file: {link}",
                    name,
                )
            )
    return findings


def _check_skill(skill_dir: Path, tests_dir: Path) -> list[Finding]:
    name = skill_dir.name
    findings: list[Finding] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [Finding("skill-md-missing", "error", "has no SKILL.md", name)]

    text = skill_md.read_text(encoding="utf-8")
    _, body = _split_raw(text)
    frontmatter = _frontmatter(text)

    if "__parse_error__" in frontmatter:
        findings.append(
            Finding(
                "frontmatter-fields",
                "error",
                f"frontmatter is not valid YAML: {frontmatter['__parse_error__']}",
                name,
            )
        )
    else:
        fname = frontmatter.get("name")
        if not isinstance(fname, str) or not fname:
            findings.append(
                Finding(
                    "frontmatter-fields",
                    "error",
                    "frontmatter 'name' is required",
                    name,
                )
            )
        elif fname != name:
            findings.append(
                Finding(
                    "frontmatter-fields",
                    "error",
                    f"frontmatter name {fname!r} != directory {name!r}",
                    name,
                )
            )
        elif not NAME_RE.fullmatch(fname) or len(fname) > 64:
            findings.append(
                Finding(
                    "frontmatter-fields",
                    "error",
                    f"name {fname!r}: lowercase a-z 0-9 '-', max 64 chars, "
                    "no leading/trailing/double hyphens",
                    name,
                )
            )
        description = str(frontmatter.get("description") or "")
        if not 1 <= len(description) <= 1024:
            findings.append(
                Finding(
                    "frontmatter-fields",
                    "error",
                    "frontmatter 'description' must be 1-1024 chars",
                    name,
                )
            )

    for artifact in _test_artifacts(skill_dir):
        findings.append(
            Finding(
                "no-tests-in-skill",
                "error",
                f"{artifact.relative_to(skill_dir)} — tests belong to the repo "
                "tests/, never inside a skill (installers copy it verbatim)",
                name,
            )
        )

    readme = skill_dir / "README.md"
    if not readme.is_file():
        findings.append(
            Finding(
                "readme-per-skill",
                "error",
                "missing README.md (human-facing; SKILL.md is agent-facing)",
                name,
                fixable=True,
            )
        )
    else:
        readme_text = readme.read_text(encoding="utf-8")
        if not any(level == 1 for level, _ in _headings(readme_text)):
            findings.append(
                Finding(
                    "readme-sections",
                    "error",
                    "README.md needs a top-level # title",
                    name,
                    fixable=True,
                )
            )
        for section in _missing_sections(readme_text, README_SECTIONS):
            findings.append(
                Finding(
                    "readme-sections",
                    "error",
                    f"README.md missing required section: ## {section}",
                    name,
                    fixable=True,
                )
            )

    headings = _headings(body)
    if not headings or headings[0][0] != 1:
        findings.append(
            Finding(
                "skill-sections",
                "error",
                "SKILL.md body must start with a single # title",
                name,
                fixable=True,
            )
        )
    for section in _missing_sections(body, SKILL_SECTIONS):
        findings.append(
            Finding(
                "skill-sections",
                "error",
                f"SKILL.md missing required section: ## {section}",
                name,
                fixable=True,
            )
        )

    body_lines = len(body.splitlines())
    if body_lines > MAX_BODY_LINES:
        findings.append(
            Finding(
                "body-length",
                "warning",
                f"SKILL.md body is {body_lines} lines (> {MAX_BODY_LINES}); "
                "move detail into references/",
                name,
            )
        )

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for script in sorted(p for p in scripts_dir.rglob("*") if p.is_file()):
            first_line = script.read_text(encoding="utf-8", errors="replace").split(
                "\n", 1
            )[0]
            if not first_line.startswith("#!"):
                findings.append(
                    Finding(
                        "scripts-executable",
                        "error",
                        f"scripts/{script.name} has no shebang (#!...)",
                        name,
                    )
                )
            elif not script.stat().st_mode & 0o111:
                findings.append(
                    Finding(
                        "scripts-executable",
                        "error",
                        f"scripts/{script.name} is not executable",
                        name,
                        fixable=True,
                    )
                )

    findings += _relative_link_findings(body, skill_dir, name)

    mirror = tests_dir / name.replace("-", "_")
    if not mirror.is_dir():
        findings.append(
            Finding(
                "tests-outside-mirror",
                "error",
                f"no tests/{name.replace('-', '_')}/ — every skill needs its "
                "tests in the repo tests/",
                name,
            )
        )
    return findings


def collect(root: Path) -> list[Finding]:
    """Run every rule against the repo at ``root``."""
    findings: list[Finding] = []
    skills_dir = root / "skills"
    tests_dir = root / "tests"

    if not (root / "LICENSE").is_file():
        findings.append(
            Finding(
                "repo-license", "error", "repo root has no LICENSE file", fixable=True
            )
        )
    skills = (
        sorted(d for d in skills_dir.iterdir() if d.is_dir())
        if skills_dir.is_dir()
        else []
    )
    if not skills:
        findings.append(Finding("skills-dir", "error", "skills/ missing or empty"))
        return findings

    for skill_dir in skills:
        findings += _check_skill(skill_dir, tests_dir)

    if tests_dir.is_dir():
        known = {d.name.replace("-", "_") for d in skills}
        for test_dir in sorted(d for d in tests_dir.iterdir() if d.is_dir()):
            if _skipped(test_dir) or test_dir.name in {"__pycache__"}:
                continue
            if test_dir.name not in known | ALLOWED_NON_SKILL_TEST_DIRS:
                findings.append(
                    Finding(
                        "tests-outside-mirror",
                        "error",
                        f"tests/{test_dir.name}/ matches no skills/<name> "
                        "(orphan tests)",
                    )
                )
    return findings


# --- formatting (safe structural fixes only) ---------------------------------------


def _render(frontmatter_raw: str | None, body: str) -> str:
    if frontmatter_raw is None:
        return body
    return f"---\n{frontmatter_raw.strip()}\n---\n\n{body}"


def _fix_skill_sections(skill_md: Path, title: str) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    fm_raw, body = _split_raw(text)
    headings = _headings(body)
    changed = False
    if not headings or headings[0][0] != 1:
        body = f"# {title}\n\n{body}"
        changed = True
    missing = _missing_sections(body, SKILL_SECTIONS)
    if missing:
        additions = "".join(f"\n## {section}\n\nTODO\n" for section in missing)
        body = body.rstrip("\n") + "\n" + additions.lstrip("\n")
        changed = True
    if changed:
        skill_md.write_text(_render(fm_raw, body), encoding="utf-8")
    return changed


def _fix(root: Path, findings: list[Finding]) -> int:
    fixed = 0

    if any(f.rule == "repo-license" for f in findings):
        (root / "LICENSE").write_text(
            "MIT License\n\nCopyright (c) 2026 <ORG>\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining"
            " a copy of this software and associated documentation files (the"
            ' "Software"), to deal in the Software without restriction,'
            " including without limitation the rights to use, copy, modify, merge,"
            " publish, distribute, sublicense, and/or sell copies of the Software,"
            " and to permit persons to whom the Software is furnished to do so,"
            " subject to the following conditions:\n\nThe above copyright notice"
            " and this permission notice shall be included in all copies or"
            " substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED"
            ' "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,'
            " INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,"
            " FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT"
            " SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,"
            " DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT"
            " OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE"
            " SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n",
            encoding="utf-8",
        )
        fixed += 1

    for finding in findings:
        if not finding.fixable or finding.skill == "-":
            continue
        skill_dir = root / "skills" / finding.skill
        title = finding.skill.replace("-", " ").title()

        if finding.rule == "readme-per-skill":
            readme = skill_dir / "README.md"
            if not readme.is_file():
                readme.write_text(
                    f"# {title}\n\nTODO: one paragraph on what this skill does.\n\n"
                    f"## Usage\n\n```bash\n"
                    f"gh skill install <ORG>/skills {finding.skill}\n"
                    f"npx skills add <ORG>/skills --skill {finding.skill}\n```\n",
                    encoding="utf-8",
                )
                fixed += 1
        elif finding.rule == "skill-sections":
            fixed += int(_fix_skill_sections(skill_dir / "SKILL.md", title))
        elif finding.rule == "readme-sections":
            readme = skill_dir / "README.md"
            if readme.is_file():
                text = readme.read_text(encoding="utf-8")
                changed = False
                if not any(level == 1 for level, _ in _headings(text)):
                    text = f"# {title}\n\n{text}"
                    changed = True
                missing = _missing_sections(text, README_SECTIONS)
                if missing:
                    additions = "".join(f"\n## {s}\n\nTODO\n" for s in missing)
                    text = text.rstrip("\n") + "\n" + additions.lstrip("\n")
                    changed = True
                if changed:
                    readme.write_text(text, encoding="utf-8")
                    fixed += 1
        elif finding.rule == "scripts-executable":
            for script in (skill_dir / "scripts").rglob("*"):
                if script.is_file():
                    script.chmod(0o755)
            fixed += 1
    return fixed


# --- command entry point ------------------------------------------------------------


def command(
    path: Annotated[
        Path,
        typer.Option("--path", help="repo root to lint", exists=True, file_okay=False),
    ] = REPO_ROOT,
    fix: Annotated[
        bool, typer.Option("--fix", help="apply safe structural fixes first")
    ] = False,
    strict: Annotated[
        bool, typer.Option("--strict", help="warnings also fail (used in CI)")
    ] = False,
) -> None:
    """Enforce repo-wide structure rules: skill boundaries, required files
    and sections, tests placement, scripts hygiene."""
    findings = collect(path)

    if fix and findings:
        applied = _fix(path, findings)
        if applied:
            console.print(f"[cyan]applied {applied} fix(es); re-checking…[/cyan]")
            findings = collect(path)

    if not findings:
        console.print("[green]✓[/green] all structure rules pass")
        return

    table = Table(title=f"structure lint: {path.name}", header_style="bold")
    table.add_column("severity")
    table.add_column("rule", style="cyan")
    table.add_column("skill")
    table.add_column("finding")
    for item in findings:
        severity = (
            "[red]error[/red]"
            if item.severity == "error"
            else "[yellow]warning[/yellow]"
        )
        fixable = " (fixable)" if item.fixable else ""
        table.add_row(severity, item.rule, item.skill, item.message + fixable)
    console.print(table)

    hard_fail = [f for f in findings if f.severity == "error"]
    if strict:
        hard_fail = findings
    if hard_fail:
        raise typer.Exit(1)
