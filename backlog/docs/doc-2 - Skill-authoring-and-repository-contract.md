---
id: doc-2
title: Skill authoring and repository contract
type: specification
created_date: '2026-10-25T19:22:00Z'
---

## Scope

The rules any directory under `skills/` must satisfy to be publishable and
CI-green, and the layout of the repo that hosts them. Enforced by
`scripts/commands/lint.py` (`pixi run check`, `--strict` in CI) and
pymarkdownlnt (`pixi run lint-md`); decisions 4–5 explain the split.

## Skill directory contract

```text
skills/<name>/
├── SKILL.md            # REQUIRED, agent-facing
├── README.md           # REQUIRED, human-facing
├── commands/*.py       # runtime commands (engine-facing contract: doc-1)
├── scripts/*           # standalone executables: shebang + exec bit
├── references/*        # progressive-disclosure detail (no contracts)
└── tests/ …            # FORBIDDEN — see tests/ mirror below
```

- `<name>`: lowercase words, hyphens, 1–64 chars; MUST equal the SKILL.md
  frontmatter `name`.
- SKILL.md frontmatter: valid YAML with `name` (== dir) and `description`
  (1–1024 chars); SHOULD declare `compatibility:` when env constraints exist.
- SKILL.md body sections (H2, in order): `# Title` (single H1),
  `## When to use this skill`, `## How to use it`. Body budget: ≤ 500 lines
  (warning); push detail into `references/`.
- README.md body: `# Title` + `## Usage`.
- Relative links in SKILL.md SHOULD resolve inside the skill (warning when
  broken).

## Tests mirror

`tests/<name>/` MUST exist for every `skills/<name>/`; no orphan test dirs
and no test artifacts inside a skill. Test packages import runtime/installer
copies via `tests/conftest.py: load_skill_module` (unique module names — no
sys.modules cross-contamination between repo and tmp copies).

## Boundary

Only `skills/` is linted — `.agents/skills/` installs are third-party and
never checked. `scripts/` is the repo's own Typer tooling: `cli.py`
auto-discovers `commands/*.py`; `python -m scripts` prints the CLI help.

`skills/skills-lock.json` pins the repo's own skill set (manifest mode;
decision-2), so a new skill needs one entry added there when it should be
active in repo dev runs.

## Lint rules (severity / fixable)

| Rule | Severity | --fix |
| ---- | -------- | ----- |
| `frontmatter-fields` | error | no |
| `no-tests-in-skill` | error | no |
| `readme-per-skill` | error | stub |
| `skill-sections` | error | section headers |
| `readme-sections` | error | section headers |
| `tests-outside-mirror` | error | no |
| `scripts-executable` | error | chmod |
| `body-length` | warning | no (fails under `--strict`) |
| `relative-refs-exist` | warning | no (fails under `--strict`) |
| `repo-license` | error | writes MIT LICENSE |

Markdown hygiene/MD041 (first-line H1): pymarkdownlnt with
`.pymarkdown.skill.json` / `.pymarkdown.readme.json`, front-matter aware.
